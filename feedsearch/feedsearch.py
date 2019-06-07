from typing import List

from feedsearch.feedsearch_spider import FeedsearchSpider, FeedInfo
import asyncio
import json


def get_pretty_print(json_object: object):
    return json.dumps(json_object, sort_keys=True, indent=2, separators=(",", ": "))


def search(url: str, timeout: float = 20, user_agent: str = ""):

    results = asyncio.run(search_async(url, timeout, user_agent))
    return results


async def search_async(url: str, timeout: float = 20, user_agent: str = ""):

    crawler = FeedsearchSpider(max_tasks=10, timeout=timeout, user_agent=user_agent)
    await crawler.crawl(url)

    return sort_urls(crawler.items)


def sort_urls(feeds: List[FeedInfo]) -> List[FeedInfo]:
    """
    Sort list of feeds based on Url score

    :param feeds: List of FeedInfo objects
    :param original_url: Searched Url
    :return: List of FeedInfo objects
    """
    feeds = [f for f in feeds if isinstance(f, FeedInfo)]
    sorted_urls = sorted(list(set(feeds)), key=lambda x: x.score, reverse=True)
    return sorted_urls
