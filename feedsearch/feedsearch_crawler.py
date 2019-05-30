from typing import Union

from bs4 import BeautifulSoup
from yarl import URL

from crawler.crawler import Crawler
from feedsearch.feed import Feed
from crawler.request import Request
from crawler.response import Response
from feedsearch.dupefilter import NoQueryDupeFilter
from feedsearch.lib import query_contains_comments, is_feedlike_url


class FeedsearchSpider(Crawler):
    dupefilter = NoQueryDupeFilter()

    async def parse(self, request: Request, response: Response):
        url = response.url
        content_type = response.headers.get("content-type")

        if response.json:
            if "version" in response.json:
                item = Feed(str(response.url), content_type)
                item.process_data(response.json, response)
                yield item
                return
        else:
            print(f"No content type at URL: {url}")

        if not response.text:
            print(f"No text at {url}")
            return

        soup = BeautifulSoup(response.text, features="html.parser")
        data = response.text.lower()[:500]

        if not data:
            return

        if bool(data.count("<rss") + data.count("<rdf") + data.count("<feed")):
            item = Feed(str(response.url), content_type)
            item.process_data(response.text, response)
            yield item
            return

        # link_tags = soup.find_all("link")
        # if not link_tags:
        #     return
        # for link in link_tags:
        #     if link.get("type") in [
        #         "application/rss+xml",
        #         "text/xml",
        #         "application/atom+xml",
        #         "application/x.atom+xml",
        #         "application/x-atom+xml",
        #         "application/json",
        #     ]:
        #         href = link.get("href", "")
        #         yield self.follow(href, self.parse, response)
        links = soup.find_all(tag_has_attr)
        for link in links:
            if should_follow_url(link.get("href"), response):
                yield self.follow(link.get("href"), self.parse, response)


def should_follow_url(url: str, response: Response) -> bool:
    if (
        "/amp/" not in url
        and not query_contains_comments(url)
        and one_jump_from_original_domain(url, response)
        and is_feedlike_url(url)
        and not invalid_filetype(url)
    ):
        return True
    #     return False
    # if query_contains_comments(url):
    #     return False
    # if not one_jump_from_original_domain(url, response):
    #     return False
    # if is_feedlike_url(url):
    #     return True
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
