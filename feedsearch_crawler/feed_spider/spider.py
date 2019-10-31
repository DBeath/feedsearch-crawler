import base64
import pathlib
import re
from types import AsyncGeneratorType
from typing import Union, Any, List, Set, Optional

import bs4
from w3lib.url import url_query_cleaner
from yarl import URL

from feedsearch_crawler.crawler import Crawler, Item, Request, Response
from feedsearch_crawler.feed_spider.dupefilter import NoQueryDupeFilter
from feedsearch_crawler.feed_spider.favicon import Favicon
from feedsearch_crawler.feed_spider.feed_info import FeedInfo
from feedsearch_crawler.feed_spider.feed_info_parser import FeedInfoParser
from feedsearch_crawler.feed_spider.site_meta import SiteMeta
from feedsearch_crawler.feed_spider.site_meta_parser import SiteMetaParser

# Regex to check that a feed-like string is a whole word to help rule out false positives.
feedlike_regex = re.compile(
    "\\b(rss|feeds?|atom|json|xml|rdf|podcasts?)\\b", re.IGNORECASE
)

# Regex to check if the URL might contain author information.
author_regex = re.compile(
    "(authors?|journalists?|writers?|contributors?)", re.IGNORECASE
)

# Regex to check URL string for invalid file types.
file_regex = re.compile(
    ".(jpe?g|png|gif|bmp|mp4|mp3|mkv|md|css|avi|pdf|js|woff?2|svg|ttf|zip)/?$",
    re.IGNORECASE,
)

# Regex to match year and month in URLs, e.g. /2019/07/
date_regex = re.compile("/(\\d{4}/\\d{2})/")

invalid_filetypes = [
    "jpeg",
    "jpg",
    "png",
    "gif",
    "bmp",
    "mp4",
    "mp3",
    "mkv",
    "md",
    "css",
    "avi",
    "pdf",
    "js",
    "woff",
    "woff2",
    "svg",
    "ttf",
]


class FeedsearchSpider(Crawler):
    duplicate_filter_class = NoQueryDupeFilter
    htmlparser = "html.parser"
    favicon_data_uri = True
    try_urls: Union[List[str], bool] = False
    full_crawl: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.site_meta_processor = SiteMetaParser(self)
        self.feed_info_parser = FeedInfoParser(self)
        self.site_metas = set()
        self.favicons = dict()
        self.feeds_seen = dict()
        self.post_crawl_callback = self.populate_feed_site_meta
        if "try_urls" in kwargs:
            self.try_urls = kwargs["try_urls"]
        if "favicon_data_uri" in kwargs:
            self.favicon_data_uri = kwargs["favicon_data_uri"]
        if "full_crawl" in kwargs:
            self.full_crawl = kwargs["full_crawl"]

    async def parse(self, request: Request, response: Response) -> AsyncGeneratorType:
        """
        Parse a Response for feeds or site metadata.

        :param request: Request
        :param response: Response
        :return: AsyncGenerator yielding Items, Requests, or iterative AsyncGenerators
        """

        # If the Response is not OK then there's no data to parse.
        if not response.ok:
            return

        # If the Response contains JSON then attempt to parse it as a JsonFeed.
        if response.json:
            if "version" and "jsonfeed" and "feed_url" in response.json:
                yield self.feed_info_parser.parse_item(request, response, type="json")
                return

        if not isinstance(response.text, str):
            self.logger.debug("No text in %s", response)
            return

        url_origin = response.url.origin()
        request_url_origin = request.url.origin()
        # If the returned url is an origin url, or the request url is an origin url (and there may have been a redirect)
        # then parse the site meta.
        if response.url == url_origin or request.url == request_url_origin:
            yield self.site_meta_processor.parse_item(request, response)

        # Restrict the RSS check to the first 500 characters, otherwise it's almost definitely not an actual feed.
        data = response.text.lower()[:500]

        if bool(data.count("<rss") + data.count("<rdf") + data.count("<feed")):
            yield self.feed_info_parser.parse_item(request, response, type="xml")
            return

        # Don't waste time trying to parse and follow urls if the max depth is already reached.
        if response.is_max_depth_reached(self.max_depth):
            self.logger.debug("Max depth %d reached: %s", self.max_depth, response)
            return

        # Make sure the Response XML has been parsed if it exists.
        soup = await response.xml
        if not soup:
            return

        # Find all links in the Response.
        links = soup.find_all(self.tag_has_href)
        for link in links:
            # Check each href for validity and queue priority.
            new_request = await self.should_follow_link(link, response)
            if new_request:
                yield new_request

    async def parse_xml(self, response_text: str) -> Any:
        """
        Parse Response text as XML.
        Used to allow implementations to provide their own XML parser.

        :param response_text: Response text as string.
        :return: None
        """
        return bs4.BeautifulSoup(response_text, self.htmlparser)

    async def process_item(self, item: Item) -> None:
        """
        Process parsed items.

        :param item: Item object
        :return: None
        """
        if isinstance(item, FeedInfo):
            self.items.add(item)
        elif isinstance(item, SiteMeta):
            self.site_metas.add(item)
        elif isinstance(item, Favicon):
            self.add_favicon(item)

    def add_favicon(self, favicon: Favicon) -> None:
        """
        Add a favicon to the spider's favicon dictionary.

        :param favicon: Favicon object
        """
        existing: Favicon = self.favicons.get(favicon.url)
        if existing and existing.data_uri and not favicon.data_uri:
            return
        self.favicons[favicon.url] = favicon

    # noinspection PyPep8
    async def populate_feed_site_meta(self) -> None:
        """
        Populate FeedInfo site information with data from the relevant SiteMeta item
        """
        for feed in self.items:
            # Check each SiteMeta for a url host match
            site_meta = next(
                (x for x in self.site_metas if x.host in feed.url.host), None
            )
            if site_meta:
                feed.site_url = site_meta.url
                feed.site_name = site_meta.site_name

            # Populate favicon directly if available
            if feed.favicon:
                favicon = self.favicons.get(feed.favicon)
                if favicon:
                    feed.favicon_data_uri = favicon.data_uri
                    feed.favicon = favicon.resp_url if favicon.resp_url else favicon.url

            # If a favicon hasn't been found yet or there is no data_uri then try and find a suitable favicon
            if not feed.favicon or (
                self.favicon_data_uri and not feed.favicon_data_uri
            ):
                if self.favicon_data_uri:
                    favicons = list(
                        x
                        for x in list(self.favicons.values())
                        if (x.url and x.site_host in feed.url.host and x.data_uri)
                    )
                else:
                    favicons = list(
                        x
                        for x in list(self.favicons.values())
                        if (x.url and x.site_host in feed.url.host)
                    )

                if favicons:
                    favicon = min(favicons, key=lambda x: x.priority)
                    if favicon:
                        feed.favicon_data_uri = favicon.data_uri
                        feed.favicon = (
                            favicon.resp_url if favicon.resp_url else favicon.url
                        )

    async def create_data_uri(
        self, request: Request, response: Response, favicon: Favicon
    ) -> None:
        """
        Create a data uri from a favicon image.

        :param request: Request
        :param response: Response
        :param favicon: Favicon object
        :return: None
        """
        if not response.ok or not response.data or not isinstance(response.data, bytes):
            return

        def is_png(data: bytes) -> bool:
            return data[:8] in bytes.fromhex("89 50 4E 47 0D 0A 1A 0A")

        def is_ico(data: bytes) -> bool:
            return data[:4] in bytes.fromhex("00 00 01 00")

        try:
            if not is_png(response.data) and not is_ico(response.data):
                self.logger.debug(
                    "Response data is not a valid image type: %s", response
                )
                return
        except Exception as e:
            self.logger.error("Failure validation image type: %s: %s", response, e)

        try:
            encoded = base64.b64encode(response.data)
            uri = "data:image/png;base64," + encoded.decode(response.encoding)
            favicon.resp_url = response.url
            favicon.data_uri = uri
            self.add_favicon(favicon)
        except Exception as e:
            self.logger.error("Failure encoding image: %s: %s", response, e)

    def create_start_urls(self, urls: List[Union[URL, str]]) -> List[URL]:
        """
        Create the start URLs for the crawl from an initial URL. May be overridden.

        :param urls: Initial URLs
        """
        crawl_start_urls: Set[URL] = set()

        for url in urls + self.start_urls:
            if isinstance(url, str):
                if "//" not in url:
                    url = f"//{url}"
                url = URL(url)

            if url.scheme.lower() not in ["http", "https"]:
                url = url.with_scheme("http")

            crawl_start_urls.add(url)

        if self.try_urls:
            origins = set(url.origin() for url in crawl_start_urls)

            # Common paths for feeds.
            suffixes = {
                "index.xml",
                "atom.xml",
                "feeds",
                "feeds/default",
                "feed",
                "feed/default",
                "feeds/posts/default",
                "?feed=rss",
                "?feed=atom",
                "?feed=rss2",
                "?feed=rdf",
                "rss",
                "atom",
                "rdf",
                "index.rss",
                "index.rdf",
                "index.atom",
                "data/rss",
                "rss.xml",
                "index.json",
                "about",
                "about/feeds",
                "rss-feeds",
            }

            for origin in origins:
                if isinstance(self.try_urls, list):
                    crawl_start_urls.update(
                        origin.join(URL(suffix)) for suffix in self.try_urls
                    )
                else:
                    crawl_start_urls.update(
                        origin.join(URL(suffix)) for suffix in suffixes
                    )

        return list(crawl_start_urls)

    async def should_follow_link(
        self, link: bs4.Tag, response: Response
    ) -> Optional[Request]:
        """
        Check that the link should be followed if it may contain feed information.

        :param link: Link tag
        :param response: Response
        :return: boolean
        """
        href: str = link.get("href")
        link_type: str = link.get("type")

        url: URL = self.parse_href_to_url(href)
        if not url:
            return

        is_one_jump: bool = self.is_one_jump_from_original_domain(url, response)

        priority: int = Request.priority

        has_author_info: bool = self.has_author_info(href)
        is_feedlike_href: bool = self.is_feedlike_href(href)
        is_feedlike_querystring: bool = self.is_feedlike_querystring(url)
        is_low_priority: bool = self.is_low_priority(href)

        is_feedlike_url = is_feedlike_querystring or is_feedlike_href

        # A low priority url should be fetched last.
        if is_low_priority:
            priority = Request.priority + 2
        # Potential author info has a medium priority.
        if has_author_info:
            priority = 4
        # A feedlike url has high priority.
        if is_feedlike_url:
            priority = 3

        # If the link may have a valid feed type then follow it regardless of the url text.
        if (
            link_type
            and any(
                map(link_type.lower().count, ["application/json", "rss", "atom", "rdf"])
            )
            and "json+oembed" not in link_type
            and is_one_jump
        ):
            # A link with a possible feed type has the highest priority after callbacks.
            return await self.follow(
                url, self.parse, response, priority=2, allow_domain=True
            )
        # Validate the actual URL string.
        else:
            follow = (
                is_one_jump
                and not self.has_invalid_contents(href)
                and self.is_valid_filetype(href)
                and not self.has_invalid_querystring(url)
            )
            # If full_crawl then follow all valid URLs regardless of the feedlike quality of the URL.
            # Otherwise only follow URLs if they look like they might contain feed information.
            if follow and (self.full_crawl or is_feedlike_url):

                # Remove the querystring unless it may point to a feed.
                if not is_feedlike_querystring:
                    url = url.with_query(None)

                return await self.follow(
                    url, self.parse, response, priority=priority, allow_domain=True
                )

    @staticmethod
    def tag_has_href(tag: bs4.Tag) -> bool:
        """
        Find all tags that contain links.

        :param tag: XML tag
        :return: boolean
        """
        return tag.has_attr("href")

    @staticmethod
    def is_one_jump_from_original_domain(url: URL, response: Response) -> bool:
        """
        Check that the current URL is only one response away from the originally queried domain.

        We want to be able to follow potential feed links that point to a different domain than
        the originally queried domain, but not to follow any deeper than that.

        Sub-domains of the original domain are ok.

        i.e: the following are ok
            "test.com" -> "feedhost.com"
            "test.com/feeds" -> "example.com/feed.xml"
            "test.com" -> "feeds.test.com"

        not ok:
            "test.com" -> "feedhost.com" (we stop here) -> "feedhost.com/feeds"

        :param url: URL object or string
        :param response: Response object
        :return: boolean
        """

        if not url.is_absolute():
            url = url.join(response.url)

        # This is the first Response in the chain
        if len(response.history) == 1:
            return True

        # URL is same domain
        if url.host == response.history[0].host:
            return True

        # URL is sub-domain
        if response.history[0].host in url.host:
            return True

        # URL domain and current Response domain are different from original domain
        if (
            response.history[-1].host != response.history[0].host
            and url.host != response.history[0].host
        ):
            return False

        return True

    @staticmethod
    def is_valid_filetype(url: str) -> bool:
        """
        Check if url string has an invalid filetype extension.

        :param url: URL string
        :return: boolean
        """
        # if file_regex.search(url.strip()):
        #     return False
        # return True
        suffix = pathlib.Path(url_query_cleaner(url)).suffix.strip(".").lower()
        if suffix in invalid_filetypes:
            return False
        return True

    @staticmethod
    def has_invalid_querystring(url: URL) -> bool:
        """
        Check if URL querystring contains invalid keys.

        :param url: URL object
        :return: boolean
        """
        return any(
            key in url.query for key in ["comment", "comments", "post", "view", "theme"]
        )

    @staticmethod
    def is_feedlike_href(url_string: str) -> bool:
        """
        Check if url looks like it may point to something resembling a feed.

        :param url_string: URL string
        :return: boolean
        """
        # Check url string without query parameters
        if feedlike_regex.search(url_query_cleaner(url_string)):
            return True
        return False

    @staticmethod
    def is_feedlike_querystring(url: URL) -> bool:
        """
        Check if the url querystring looks like it may point to a feed.

        :param url: URL object
        :return: boolean
        """
        for key in url.query:
            if feedlike_regex.search(key):
                return True
        return False

    @staticmethod
    def has_invalid_contents(string: str) -> bool:
        """
        Ignore any string containing the following strings.

        :param string: String to check
        :return: boolean
        """
        return any(
            map(
                string.lower().count,
                [
                    "wp-includes",
                    "wp-content",
                    "wp-json",
                    "xmlrpc",
                    "wp-admin",
                    # Theoretically there could be a feed at an AMP url, but not worth checking.
                    "/amp/",
                    "mailto:",
                    "//font.",
                ],
            )
        )

    @staticmethod
    def has_author_info(url_string: str) -> bool:
        """
        Check if the url may contain author information.

        :param url_string: URL string
        :return: boolean
        """
        if author_regex.search(url_query_cleaner(url_string)):
            return True
        return False

    @staticmethod
    def is_low_priority(url_string) -> bool:
        """
        Check if the url contains any strings that indicate the url should be low priority.

        :param url_string: URL string
        :return: boolean
        """
        if any(
            map(
                url_string.lower().count,
                [
                    # Archives and article pages are less likely to contain feeds.
                    "/archive/",
                    "/page/",
                    # Forums are not likely to contain interesting feeds.
                    "forum",
                    # Can't guarantee that someone won't put a feed at a CDN url, so we can't outright ignore it.
                    "//cdn.",
                    "video",
                ],
            )
        ):
            return True

        # Search for dates in url, this generally indicates an article page.
        if date_regex.search(url_string):
            return True
        return False
