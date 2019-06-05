from typing import Union, Any

from bs4 import BeautifulSoup
from yarl import URL

from crawler.crawler import Crawler
from crawler.item import Item
from feedsearch.feed_info import FeedInfo
from crawler.request import Request
from crawler.response import Response
from feedsearch.dupefilter import NoQueryDupeFilter
from feedsearch.lib import query_contains_comments, is_feedlike_url
from feedsearch.site_meta_parser import SiteMetaParser
from feedsearch.site_meta import SiteMeta
from feedsearch.feed_info_parser import FeedInfoParser


class FeedsearchSpider(Crawler):
    dupefilter = NoQueryDupeFilter()
    htmlparser = "html.parser"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.site_meta_processor = SiteMetaParser(self)
        self.feed_info_parser = FeedInfoParser(self)
        self.site_metas = set()
        self.post_crawl_callback = self.populate_feed_site_meta

    async def parse(self, request: Request, response: Response):
        if not response.ok:
            return

        url = response.url

        url_origin = url.origin()
        if url == url_origin:
            yield await self.site_meta_processor.parse_item(request, response)

        if response.json:
            if "version" in response.json:
                yield await self.feed_info_parser.parse_item(
                    request, response, type="json"
                )
                return

        if not response.text:
            self.logger.debug("No text in %s", response)
            return

        soup = response.parsed_xml
        data = response.text.lower()[:500]

        if not data:
            return

        if bool(data.count("<rss") + data.count("<rdf") + data.count("<feed")):
            yield await self.feed_info_parser.parse_item(request, response, type="xml")
            return

        links = soup.find_all(tag_has_attr)
        for link in links:
            if should_follow_url(link.get("href"), response):
                yield self.follow(link.get("href"), self.parse, response)

    async def parse_xml(self, response_text: str) -> Any:
        return BeautifulSoup(response_text, self.htmlparser)

    async def process_item(self, item: Item) -> None:
        if isinstance(item, FeedInfo):
            self.items.add(item)
        elif isinstance(item, SiteMeta):
            self.site_metas.add(item)

    async def populate_feed_site_meta(self):
        for feed in self.items:
            for meta in self.site_metas:
                if meta.url.host in feed.url.host:
                    feed.site_url = meta.url
                    if not feed.favicon:
                        feed.favicon = meta.icon_url
                    feed.site_name = meta.site_name


def should_follow_url(url: str, response: Response) -> bool:
    if (
        "/amp/" not in url
        and not query_contains_comments(url)
        and one_jump_from_original_domain(url, response)
        and is_feedlike_url(url)
        and not invalid_filetype(url)
    ):
        return True

    return False


def tag_has_attr(tag):
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

    if len(response.history) > 1:
        if (
            response.history[-2].host == response.history[0].host
            and url.host == response.history[-1].host
        ):
            return True
    return False


def invalid_filetype(url: Union[str, URL]):
    if isinstance(url, URL):
        url = str(url)
    url_ending = url.split(".")[-1]
    if url_ending in ["png", "md", "css", "jpg", "jpeg"]:
        return True
    return False
