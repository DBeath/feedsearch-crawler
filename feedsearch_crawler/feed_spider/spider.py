import base64
import re
from types import AsyncGeneratorType
from typing import Union, Any, List

from bs4 import BeautifulSoup
from yarl import URL

from feedsearch_crawler.crawler import Crawler, Item, Request, Response

from feedsearch_crawler.feed_spider.dupefilter import NoQueryDupeFilter
from feedsearch_crawler.feed_spider.feed_info import FeedInfo
from feedsearch_crawler.feed_spider.feed_info_parser import FeedInfoParser
from feedsearch_crawler.feed_spider.site_meta import SiteMeta
from feedsearch_crawler.feed_spider.site_meta_parser import SiteMetaParser


class FeedsearchSpider(Crawler):
    duplicate_filter_class = NoQueryDupeFilter
    htmlparser = "html.parser"
    favicon_data_uri = True
    try_urls: Union[List[str], bool] = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.site_meta_processor = SiteMetaParser(self)
        self.feed_info_parser = FeedInfoParser(self)
        self.site_metas = set()
        self.favicons = dict()
        self.post_crawl_callback = self.populate_feed_site_meta
        if "try_urls" in kwargs:
            self.try_urls = kwargs["try_urls"]
        if "favicon_data_uri" in kwargs:
            self.favicon_data_uri = kwargs["favicon_data_uri"]

    async def parse(self, request: Request, response: Response) -> AsyncGeneratorType:
        if not response.ok:
            return

        url = response.url

        if response.json:
            if "version" and "jsonfeed" and "feed_url" in response.json:
                yield self.feed_info_parser.parse_item(request, response, type="json")
                return

        if not isinstance(response.text, str):
            self.logger.debug("No text in %s", response)
            return

        data = response.text.lower()[:500]

        url_origin = url.origin()
        request_url_origin = request.url.origin()
        # If the returned url is an origin url, or the request url is an origin url (and there may have been a redirect)
        # then parse the site meta.
        if url == url_origin or request.url == request_url_origin:
            yield self.site_meta_processor.parse_item(request, response)

        if bool(data.count("<rss") + data.count("<rdf") + data.count("<feed")):
            yield self.feed_info_parser.parse_item(request, response, type="xml")
            return

        soup = await response.xml
        if not soup:
            return

        links = soup.find_all(tag_has_attr)
        for link in links:
            href = link.get("href", "")
            if href:
                if (
                    "alternate" in link.get("rel", "")
                    and should_follow_alternate(link, response)
                ) or should_follow_url(href, response):
                    yield self.follow(href, self.parse, response)

    async def parse_xml(self, response_text: str) -> Any:
        return BeautifulSoup(response_text, self.htmlparser)

    async def process_item(self, item: Item) -> None:
        if isinstance(item, FeedInfo):
            self.items.add(item)
        elif isinstance(item, SiteMeta):
            self.site_metas.add(item)

    async def populate_feed_site_meta(self):
        """
        Populate FeedInfo site information with data from the relevant SiteMeta item
        """
        for feed in self.items:
            # Check each SiteMeta for a url host match
            for meta in self.site_metas:
                # If the meta url host begins with www, then we remove it because the feed may be on
                # a different subdomain
                host = meta.url.host
                if host.startswith("www."):
                    host = host[len("www.") :]

                # If the meta url host is in the feed url host then we can assume that the feed belongs to that site
                if host in feed.url.host:
                    feed.site_url = meta.url
                    feed.site_name = meta.site_name
                    if not feed.favicon:
                        feed.favicon = meta.icon_url

            # Populate favicon data uri if available
            if feed.favicon:
                feed.favicon_data_uri = self.favicons.get(feed.favicon, "")

    async def fetch_data_uri(self, url: URL):
        req = self.follow(url, self.create_data_uri)
        await self._process_request(req)

    async def create_data_uri(self, request: Request, response: Response):
        if not response.ok or not isinstance(response.data, bytes):
            return

        try:
            encoded = base64.b64encode(response.data)
            uri = "data:image/png;base64," + encoded.decode(response.encoding)
            self.favicons[request.url] = uri
        except Exception as e:
            self.logger.warning("Failure encoding image: %s", e)

    def create_start_urls(self, url: Union[str, URL]) -> List[URL]:
        if isinstance(url, str):
            if "//" not in url:
                url = f"//{url}"
            url = URL(url)

        if url.scheme not in ["http", "https"]:
            url = url.with_scheme("http")

        origin = url.origin()

        urls = [url, origin]

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

        if self.try_urls:
            if isinstance(self.try_urls, list):
                urls.extend(origin.join(URL(suffix)) for suffix in self.try_urls)
            else:
                urls.extend(origin.join(URL(suffix)) for suffix in suffixes)

        return urls


def should_follow_alternate(link, response: Response) -> bool:
    href = link.get("href")
    return is_valid_alternate(link.get("type", "")) and one_jump_from_original_domain(
        href, response
    )


def is_valid_alternate(string: str) -> bool:
    if any(map(string.lower().count, ["json+oembed"])):
        return False
    if any(map(string.lower().count, ["application/json", "rss", "atom", "rdf"])):
        return True


def should_follow_url(url: str, response: Response) -> bool:
    if (
        "/amp/" not in url
        and is_feedlike_string(url)
        and not invalid_filetype(url)
        and not ignore(url)
        and not query_contains_comments(url)
        and one_jump_from_original_domain(url, response)
    ):
        return True

    return False


def tag_has_attr(tag) -> bool:
    return tag.has_attr("href")


def one_jump_from_original_domain(url: Union[str, URL], response: Response) -> bool:
    if isinstance(url, str):
        url = URL(url)

    if not url.is_absolute():
        url = url.join(response.url)

    if url.host == response.history[0].host:
        return True

    # Url is subdomain
    if response.history[0].host in url.host:
        return True

    if len(response.history) == 1:
        return True

    if (
        response.history[-1].host != response.history[0].host
        and url.host != response.history[0].host
    ):
        return False

    return True


# URL string should not contain invalid file types.
file_regex = re.compile(".(jpe?g|png|gif|bmp|mp4|mp3|mkv|md|css|avi)/?$", re.IGNORECASE)


def invalid_filetype(url: str) -> bool:
    if file_regex.search(url.strip()):
        return True
    return False


def query_contains_comments(url: Union[str, URL]) -> bool:
    if isinstance(url, URL):
        query = url.query
    else:
        query = URL(url).query

    return any(key in query for key in ["comment", "comments", "post"])


# Feed-like string should be whole word to help rule out false positives.
feedlike_regex = re.compile("\\b(rss|feed|atom|json|xml|rdf|feeds)\\b", re.IGNORECASE)


def is_feedlike_string(string: str) -> bool:
    if feedlike_regex.search(string):
        return True
    return False


def ignore(string: str) -> bool:
    return any(
        map(string.lower().count, ["wp-includes", "wp-content", "wp-json", "xmlrpc"])
    )
