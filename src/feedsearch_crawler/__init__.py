import asyncio
import logging
from typing import List, Union
from xml.etree import ElementTree

from yarl import URL

from feedsearch_crawler.exceptions import ErrorType, SearchError
from feedsearch_crawler.feed_spider import FeedsearchSpider, FeedInfo
from feedsearch_crawler.result import SearchResult

logging.getLogger(__name__).addHandler(logging.NullHandler())

name = "Feedsearch Crawler"


def search(
    url: Union[URL, str, List[Union[URL, str]]],
    try_urls: Union[List[str], bool] = False,
    *args,
    **kwargs,
) -> List[FeedInfo]:
    """
    Search for feeds at the given URL(s).

    This function returns a list of discovered feeds. If the root URL fails
    to load (DNS error, 404, SSL error, etc.), an empty list is returned.

    For detailed error information and statistics, use search_with_info().

    Args:
        url: URL or list of URLs to search
        try_urls: Tries different paths that may contain feeds
        **kwargs: Additional arguments passed to FeedsearchSpider

    Returns:
        List[FeedInfo]: List of discovered feeds, sorted by score (highest first).
            Returns empty list if no feeds found or if root URL fails.

    Examples:
        >>> feeds = search("https://example.com")
        >>> for feed in feeds:
        ...     print(feed.url)

        >>> if not feeds:
        ...     print("No feeds found (or URL failed)")

    Note:
        This function always returns List[FeedInfo] for backward compatibility.
        The return type is guaranteed not to change in v1.x releases.

    See Also:
        search_with_info(): Returns SearchResult with error information
    """
    result = asyncio.run(search_async(url, try_urls=try_urls, *args, **kwargs))
    return result


async def search_async(
    url: Union[URL, str, List[Union[URL, str]]],
    try_urls: Union[List[str], bool] = False,
    *args,
    **kwargs,
) -> List[FeedInfo]:
    """
    Asynchronously search for feeds at the given URL(s).

    This function returns a list of discovered feeds. If the root URL fails
    to load (DNS error, 404, SSL error, etc.), an empty list is returned.

    For detailed error information and statistics, use search_async_with_info().

    Args:
        url: URL or list of URLs to search
        try_urls: Tries different paths that may contain feeds
        **kwargs: Additional arguments passed to FeedsearchSpider

    Returns:
        List[FeedInfo]: List of discovered feeds, sorted by score (highest first).
            Returns empty list if no feeds found or if root URL fails.

    Examples:
        >>> feeds = await search_async("https://example.com")
        >>> for feed in feeds:
        ...     print(feed.url)

    Note:
        This function always returns List[FeedInfo] for backward compatibility.
        The return type is guaranteed not to change in v1.x releases.

    See Also:
        search_async_with_info(): Returns SearchResult with error information
    """
    crawler = FeedsearchSpider(try_urls=try_urls, *args, **kwargs)
    await crawler.crawl(url)

    feeds = sort_urls(list(crawler.items))
    return feeds


def search_with_info(
    url: Union[URL, str, List[Union[URL, str]]],
    try_urls: Union[List[str], bool] = False,
    include_stats: bool = False,
    *args,
    **kwargs,
) -> SearchResult:
    """
    Search for feeds with detailed error and statistics information.

    Unlike search(), this function returns a SearchResult object that includes:
    - List of discovered feeds
    - Error information if the root URL failed
    - Optional crawl statistics

    Args:
        url: URL or list of URLs to search
        try_urls: Tries different paths that may contain feeds
        include_stats: Include crawl statistics in result
        **kwargs: Additional arguments passed to FeedsearchSpider

    Returns:
        SearchResult containing:
            - feeds: List of discovered feeds (may be empty)
            - root_error: SearchError if root URL failed, None otherwise
            - stats: Crawl statistics dict if include_stats=True, None otherwise

    Examples:
        >>> result = search_with_info("https://example.com")
        >>> if result.root_error:
        ...     print(f"Error: {result.root_error.message}")
        ...     print(f"Type: {result.root_error.error_type}")
        >>> else:
        ...     print(f"Found {len(result.feeds)} feeds")
        ...     for feed in result.feeds:
        ...         print(feed.url)

        >>> # With statistics
        >>> result = search_with_info("https://example.com", include_stats=True)
        >>> if result.stats:
        ...     print(f"Requests: {result.stats.get('requests')}")
        ...     print(f"Responses: {result.stats.get('responses')}")

    Note:
        SearchResult is iterable, so you can iterate over feeds directly:
        >>> result = search_with_info("https://example.com")
        >>> for feed in result:  # Iterates over result.feeds
        ...     print(feed.url)

    See Also:
        search(): Simple API that returns List[FeedInfo]
        SearchError: Error information dataclass
        ErrorType: Enum of possible error types
    """
    result = asyncio.run(
        search_async_with_info(
            url, try_urls=try_urls, include_stats=include_stats, *args, **kwargs
        )
    )
    return result


async def search_async_with_info(
    url: Union[URL, str, List[Union[URL, str]]],
    try_urls: Union[List[str], bool] = False,
    include_stats: bool = False,
    *args,
    **kwargs,
) -> SearchResult:
    """
    Asynchronously search for feeds with detailed error and statistics information.

    Unlike search_async(), this function returns a SearchResult object that includes:
    - List of discovered feeds
    - Error information if the root URL failed
    - Optional crawl statistics

    Args:
        url: URL or list of URLs to search
        try_urls: Tries different paths that may contain feeds
        include_stats: Include crawl statistics in result
        **kwargs: Additional arguments passed to FeedsearchSpider

    Returns:
        SearchResult containing:
            - feeds: List of discovered feeds (may be empty)
            - root_error: SearchError if root URL failed, None otherwise
            - stats: Crawl statistics dict if include_stats=True, None otherwise

    Examples:
        >>> result = await search_async_with_info("https://example.com")
        >>> if result.root_error:
        ...     print(f"Error: {result.root_error.message}")
        >>> else:
        ...     for feed in result.feeds:
        ...         print(feed.url)

    See Also:
        search_async(): Simple API that returns List[FeedInfo]
    """
    crawler = FeedsearchSpider(try_urls=try_urls, *args, **kwargs)
    await crawler.crawl(url)

    feeds = sort_urls(list(crawler.items))
    root_error = crawler.get_root_error()
    stats = crawler.get_stats() if include_stats else None

    return SearchResult(feeds=feeds, root_error=root_error, stats=stats)


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


# Export public API
__all__ = [
    "search",
    "search_async",
    "search_with_info",
    "search_async_with_info",
    "sort_urls",
    "output_opml",
    "FeedInfo",
    "FeedsearchSpider",
    "SearchResult",
    "SearchError",
    "ErrorType",
]
