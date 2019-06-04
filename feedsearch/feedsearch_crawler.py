from typing import Union, Any

from bs4 import BeautifulSoup
from yarl import URL

from crawler.crawler import Crawler
from crawler.item import Item
from feedsearch.feed import Feed
from crawler.request import Request
from crawler.response import Response
from feedsearch.dupefilter import NoQueryDupeFilter
from feedsearch.lib import query_contains_comments, is_feedlike_url
from feedsearch.site_meta_processor import SiteMetaProcessor
from feedsearch.site_meta import SiteMeta


class FeedsearchSpider(Crawler):
    dupefilter = NoQueryDupeFilter()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.site_meta_processor = SiteMetaProcessor(self)
        self.site_metas = set()
        self.post_crawl_callback = self.populate_feed_site_meta

    async def parse(self, request: Request, response: Response):
        if not response.ok:
            return

        url = response.url
        content_type = response.headers.get("content-type")

        if response.json:
            if "version" in response.json:
                item = Feed(response.url, content_type)
                item.process_data(response.json, response)
                yield item
                return

        if not response.text:
            self.logger.debug("No text in %s", response)
            return

        soup = response.parsed_xml
        data = response.text.lower()[:500]

        url_origin = url.origin()
        if url == url_origin:
            yield await self.site_meta_processor.process(url, request, response)

        if not data:
            return

        if bool(data.count("<rss") + data.count("<rdf") + data.count("<feed")):
            item = Feed(response.url, content_type)
            item.process_data(response.text, response)
            yield item
            return

        links = soup.find_all(tag_has_attr)
        for link in links:
            if should_follow_url(link.get("href"), response):
                yield self.follow(link.get("href"), self.parse, response)

    async def parse_xml(self, response_text: str) -> Any:
        return BeautifulSoup(response_text, features="html.parser")

    async def process_item(self, item: Item) -> None:
        if isinstance(item, Feed):
            self.items.add(item)
        elif isinstance(item, SiteMeta):
            self.site_metas.add(item)

    def populate_feed_site_meta(self):
        for feed in self.items:
            for meta in self.site_metas:
                if meta.url == feed.url.origin():
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
