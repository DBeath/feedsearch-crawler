import asyncio
import json
import logging
from typing import List

from feedsearch.feedsearch_spider import FeedsearchSpider, FeedInfo

logging.getLogger("feedsearch.crawler").addHandler(logging.NullHandler())

name = "Feedsearch Crawler"


def get_pretty_print(json_object: object):
    return json.dumps(json_object, sort_keys=True, indent=2, separators=(",", ": "))


def search(
    url: str,
    timeout: float = 20,
    user_agent: str = "",
    concurrency: int = 10,
    try_urls: bool = False,
):

    results = asyncio.run(search_async(url, timeout, user_agent, concurrency, try_urls))
    return results


async def search_async(
    url: str,
    timeout: float = 20,
    user_agent: str = "",
    concurrency: int = 10,
    try_urls: bool = False,
):

    crawler = FeedsearchSpider(
        concurrency=concurrency,
        timeout=timeout,
        user_agent=user_agent,
        try_urls=try_urls,
    )
    await crawler.crawl(url)

    return sort_urls(crawler.items)


def sort_urls(feeds: List[FeedInfo]) -> List[FeedInfo]:
    """
    Sort list of feeds based on Url score

    :param feeds: List of FeedInfo objects
    :return: List of FeedInfo objects
    """
    feeds = [f for f in feeds if isinstance(f, FeedInfo)]
    sorted_urls = sorted(list(set(feeds)), key=lambda x: x.score, reverse=True)
    return sorted_urls
