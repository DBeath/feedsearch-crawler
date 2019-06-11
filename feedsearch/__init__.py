import asyncio
import logging
from typing import List

from feedsearch.feedsearch_spider import FeedsearchSpider, FeedInfo

logging.getLogger("feedsearch.crawler").addHandler(logging.NullHandler())

name = "Feedsearch Crawler"


def search(url: str, try_urls: bool = False, *args, **kwargs) -> List[FeedInfo]:
    """
    Search for feeds at a URL.

    :param url: URL to search
    :param try_urls: Tries different paths that may contain feeds.
    :return: List of FeedInfo objects
    """
    results = asyncio.run(search_async(url, try_urls=try_urls, *args, **kwargs))
    return results


async def search_async(
    url: str, try_urls: bool = False, *args, **kwargs
) -> List[FeedInfo]:
    """
    Search asynchronously for feeds at a URL.

    :param url: URL to search
    :param try_urls: Tries different paths that may contain feeds.
    :return: List of FeedInfo objects
    """
    crawler = FeedsearchSpider(try_urls=try_urls, *args, **kwargs)
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
