import asyncio
import logging
from xml.etree import ElementTree
from typing import List, Union

from feedsearch_crawler.feed_spider import FeedsearchSpider, FeedInfo

logging.getLogger("feedsearch_crawler").addHandler(logging.NullHandler())

name = "Feedsearch Crawler"


def search(
    url: str, try_urls: Union[List[str], bool] = False, *args, **kwargs
) -> List[FeedInfo]:
    """
    Search for feeds at a URL.

    :param url: URL to search
    :param try_urls: Tries different paths that may contain feeds.
    :return: List of FeedInfo objects
    """
    results = asyncio.run(search_async(url, try_urls=try_urls, *args, **kwargs))
    return results


async def search_async(
    url: str, try_urls: Union[List[str], bool] = False, *args, **kwargs
) -> List[FeedInfo]:
    """
    Search asynchronously for feeds at a URL.

    :param url: URL to search
    :param try_urls: Tries different paths that may contain feeds.
    :return: List of FeedInfo objects
    """
    crawler = FeedsearchSpider(try_urls=try_urls, *args, **kwargs)
    await crawler.crawl(url)

    return sort_urls(list(crawler.items))


def sort_urls(feeds: List[FeedInfo]) -> List[FeedInfo]:
    """
    Sort list of feeds based on Url score

    :param feeds: List of FeedInfo objects
    :return: List of FeedInfo objects sorted by score
    """
    feeds = [f for f in feeds if isinstance(f, FeedInfo)]
    sorted_urls = sorted(list(set(feeds)), key=lambda x: x.score, reverse=True)
    return sorted_urls


def output_opml(feeds: List[FeedInfo]) -> bytes:
    """
    Return feeds as a subscriptionlist OPML file.
    http://dev.opml.org/spec2.html#subscriptionLists

    :param feeds: List of FeedInfo objects
    :return: OPML file as XML bytestring
    """
    root = ElementTree.Element("opml", version="2.0")
    head = ElementTree.SubElement(root, "head")
    title = ElementTree.SubElement(head, "title")
    title.text = "Feeds"
    body = ElementTree.SubElement(root, "body")

    for feed in feeds:
        if not feed.url:
            continue

        fe = ElementTree.SubElement(body, "outline", type="rss", xmlUrl=str(feed.url))

        if feed.title:
            fe.set("text", feed.title)
            fe.set("title", feed.title)
        if feed.site_url:
            fe.set("htmlUrl", str(feed.site_url))
        if feed.description:
            fe.set("description", feed.description)
        if feed.version:
            fe.set("version", feed.version)

    return ElementTree.tostring(root, encoding="utf8", method="xml")
