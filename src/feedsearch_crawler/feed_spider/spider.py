import base64
import logging
from typing import Any, AsyncGenerator, List, Optional, Set, Union

import bs4
from yarl import URL

from feedsearch_crawler.crawler import Crawler, Item, Request, Response
from feedsearch_crawler.crawler.lib import parse_href_to_url
from feedsearch_crawler.exceptions import ErrorType, SearchError
from feedsearch_crawler.feed_spider.dupefilter import NoQueryDupeFilter
from feedsearch_crawler.feed_spider.favicon import Favicon
from feedsearch_crawler.feed_spider.feed_info import FeedInfo
from feedsearch_crawler.feed_spider.feed_info_parser import FeedInfoParser
from feedsearch_crawler.feed_spider.lib import ParseTypes
from feedsearch_crawler.feed_spider.link_filter import LinkFilter
from feedsearch_crawler.feed_spider.regexes import rss_regex
from feedsearch_crawler.feed_spider.site_meta import SiteMeta
from feedsearch_crawler.feed_spider.site_meta_parser import SiteMetaParser

logger = logging.getLogger(__name__)


class FeedsearchSpider(Crawler):
    duplicate_filter_class = NoQueryDupeFilter
    htmlparser = "html.parser"
    favicon_data_uri = True
    try_urls: Union[List[str], bool] = False
    full_crawl: bool = False
    crawl_hosts: bool = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.site_meta_processor = SiteMetaParser(self)
        self.feed_info_parser = FeedInfoParser(self)
        self.site_metas = set()
        self.favicons = dict()
        self.feeds_seen = dict()
        self.post_crawl_callback = self.populate_feed_site_meta
        self._root_urls: Set[str] = set()
        self._root_url_error: Optional[SearchError] = None
        if "try_urls" in kwargs:
            self.try_urls = kwargs["try_urls"]
        if "favicon_data_uri" in kwargs:
            self.favicon_data_uri = kwargs["favicon_data_uri"]
        if "full_crawl" in kwargs:
            self.full_crawl = kwargs["full_crawl"]
        if "crawl_hosts" in kwargs:
            self.crawl_hosts = kwargs["crawl_hosts"]

    async def crawl(self, urls: Union[URL, str, List[Union[URL, str]]] = []) -> None:
        """
        Start the web crawler and track root URLs.

        :param urls: URL or list of URLs to crawl
        """
        # Normalize URLs to list
        if not urls:
            url_list = []
        elif isinstance(urls, (URL, str)):
            url_list = [urls]
        else:
            url_list = urls

        # Convert to URL objects and track as root URLs
        initial_urls = self.create_start_urls(url_list)
        self._track_root_urls(initial_urls)

        # Call parent crawl method
        await super().crawl(urls)

    async def parse_response(
        self, request: Request, response: Response
    ) -> AsyncGenerator[Any, Any]:
        """
        Parse a Response for feeds or site metadata.

        :param request: Request
        :param response: Response
        :return: AsyncGenerator yielding Items, Requests, or iterative AsyncGenerators
        """

        # If the Response is not OK then there's no data to parse.
        if not response.ok:
            # Check if this is a root URL and record error
            is_root_url = str(request.url) in self._root_urls
            if is_root_url and not self._root_url_error:
                # First root URL error - record it
                self._root_url_error = self._create_error_from_response(
                    request, response
                )
            return

        # If the Response contains JSON then attempt to parse it as a JsonFeed.
        if response.json:
            if "version" and "jsonfeed" and "feed_url" in response.json:
                yield self.feed_info_parser.parse_item(
                    request, response, parse_type=ParseTypes.JSON
                )
                return

        if not isinstance(response.text, str):
            logger.debug("No text in %s", response)
            return

        yield self.parse_site_meta(request, response)

        # Restrict the RSS check to the first 1000 characters, otherwise it's almost definitely not an actual feed.
        if rss_regex.search(response.text, endpos=1000):
            yield self.feed_info_parser.parse_item(
                request, response, parse_type=ParseTypes.XML
            )
            return

        # Don't waste time trying to parse and follow urls if the max depth is already reached.
        if response.is_max_depth_reached(self.max_depth):
            logger.debug("Max depth %d reached: %s", self.max_depth, response)
            return

        # Parse HTML content using BeautifulSoup
        soup = await self.parse_response_content(response.text)
        if not soup:
            return

        # Don't crawl links from pages that are not from the original domain
        if not response.is_original_domain():
            return

        link_filter = LinkFilter(
            request=request, response=response, full_crawl=self.full_crawl
        )

        # Find all links in the Response.
        links = soup.find_all(self.tag_has_href)
        for link in links:
            # Check each href for validity and queue priority.
            values = link_filter.should_follow_link(link)
            if values:
                url, priority = values
                yield self.follow(
                    url,
                    self.parse_response,
                    response,
                    priority=priority,
                    allow_domain=True,
                )

    async def parse_site_meta(
        self, request: Request, response: Response
    ) -> AsyncGenerator[Any, Any]:
        """
        Parses site metadata if the returned URL is a site origin URL.

        If the returned url is an origin url, or the request url is an origin url (and there may have been a redirect)
        then parse the site meta.

        :param request: Request
        :param response: Response
        :return: AsyncGenerator yielding SiteMeta items
        """
        url_origin = response.url.origin()
        request_url_origin = request.url.origin()

        if response.url == url_origin or request.url == request_url_origin:
            yield self.site_meta_processor.parse_item(request, response)

    async def parse_response_content(self, response_text: str) -> Any:
        """
        Parse Response content as HTML/XML.
        Used to allow implementations to provide their own HTML parser.

        This method uses html.parser intentionally because it needs to parse
        both HTML pages (to extract links) and handle XML gracefully.
        Actual RSS/Atom/XML feeds are parsed by FeedInfoParser using feedparser.

        :param response_text: Response text as string.
        :return: BeautifulSoup object
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
                (x for x in self.site_metas if x.host in URL(feed.url).host), None
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
                feed_host = feed.url.host
                favicons = list(
                    x
                    for x in self.favicons.values()
                    if x.matches_host(feed_host, self.favicon_data_uri)
                )

                if favicons:
                    favicon = min(favicons, key=lambda x: x.priority)

                    feed.favicon_data_uri = favicon.data_uri
                    feed.favicon = favicon.resp_url if favicon.resp_url else favicon.url

    # noinspection PyUnusedLocal
    async def parse_favicon_data_uri(
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
                logger.debug("Response data is not a valid image type: %s", response)
                return
        except Exception as e:
            logger.exception("Failure validation image type: %s: %s", response, e)

        try:
            encoded = base64.b64encode(response.data)
            uri = "data:image/png;base64," + encoded.decode(response.encoding)
            favicon.resp_url = response.url
            favicon.data_uri = uri
            self.add_favicon(favicon)
        except Exception as e:
            logger.exception("Failure encoding image: %s: %s", response, e)

    def create_start_urls(self, urls: List[Union[URL, str]]) -> List[URL]:
        """
        Create the start URLs for the crawl from an initial URL. May be overridden.

        :param urls: Initial URLs
        """
        crawl_start_urls: Set[URL] = set()

        for url in urls + self.start_urls:
            try:
                if isinstance(url, str):
                    if "//" not in url:
                        url = f"//{url}"
                    url = parse_href_to_url(url)
                    if not url:
                        continue

                if url.scheme.lower() not in ["http", "https"]:
                    url = url.with_scheme("http")

                crawl_start_urls.add(url)
            except ValueError as e:
                logger.warning("Invalid start URL '%s': %s", url, e)

        origins = set(url.origin() for url in crawl_start_urls)

        if self.try_urls:
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
                    for suffix in self.try_urls:
                        try:
                            crawl_start_urls.add(origin.join(URL(suffix)))
                        except (ValueError, TypeError) as e:
                            logger.warning("Invalid URL suffix '%s': %s", suffix, e)
                else:
                    for suffix in suffixes:
                        try:
                            crawl_start_urls.add(origin.join(URL(suffix)))
                        except (ValueError, TypeError) as e:
                            logger.warning("Invalid URL suffix '%s': %s", suffix, e)

        # Crawl the origin urls of the start urls for Site metadata.
        if self.crawl_hosts:
            crawl_start_urls.update(origins)

        return list(crawl_start_urls)

    @staticmethod
    def tag_has_href(tag: bs4.Tag) -> bool:
        """
        Find all tags that contain links.

        :param tag: XML tag
        :return: boolean
        """
        return tag.has_attr("href")

    def _track_root_urls(self, start_urls: List[URL]) -> None:
        """
        Track which URLs are root/start URLs provided by the user.

        :param start_urls: List of root URLs to track
        """
        self._root_urls = {str(url) for url in start_urls}

    def _create_error_from_response(
        self, request: Request, response: Response
    ) -> SearchError:
        """
        Create SearchError from failed response.

        :param request: The failed request
        :param response: The error response
        :return: SearchError with error details
        """
        # Use error type from downloader if available, otherwise categorize by status code
        if response.error_type:
            error_type = response.error_type
            # Map error types to user-friendly messages
            if error_type == ErrorType.DNS_FAILURE:
                message = "Domain name resolution failed (DNS error)"
            elif error_type == ErrorType.SSL_ERROR:
                message = "SSL/TLS certificate verification failed"
            elif error_type == ErrorType.CONNECTION_ERROR:
                message = "Connection to server failed"
            elif error_type == ErrorType.TIMEOUT:
                message = "Request timed out"
            else:
                message = f"Request failed with status {response.status_code}"
        else:
            # Categorize by status code when error_type not provided
            if response.status_code == 408:
                error_type = ErrorType.TIMEOUT
                message = "Request timed out"
            elif response.status_code >= 500:
                error_type = ErrorType.HTTP_ERROR
                message = f"Server error: HTTP {response.status_code}"
            elif response.status_code == 404:
                error_type = ErrorType.HTTP_ERROR
                message = "Page not found (404)"
            elif response.status_code >= 400:
                error_type = ErrorType.HTTP_ERROR
                message = f"Client error: HTTP {response.status_code}"
            else:
                error_type = ErrorType.OTHER
                message = f"Request failed with status {response.status_code}"

        return SearchError(
            url=str(request.url),
            error_type=error_type,
            message=message,
            status_code=response.status_code
            if response.status_code not in [500, 408]
            else None,
        )

    def get_root_error(self) -> Optional[SearchError]:
        """
        Get error from root URL if it failed.

        :return: SearchError if root URL failed, None otherwise
        """
        return self._root_url_error
