import heapq
import logging
import re
from asyncio import Event, Queue
from enum import Enum
from typing import Any, Dict, List, Union

from yarl import URL

from feedsearch_crawler.crawler.queueable import Queueable

logger = logging.getLogger(__name__)


class ContentLengthError(Exception):
    """Content Length is too long."""

    def __init__(self, max_content_length: int, *args: object) -> None:
        self.max_content_length = max_content_length
        super().__init__(*args)


class ContentReadError(Exception):
    """Response Content was not read."""


class CrawlerPriorityQueue(Queue):
    """A subclass of Queue; retrieves entries in priority order (lowest first).

    Entries are typically tuples of the form: (priority number, data).

    This class is used instead of the standard library PriorityQueue because it implements a clear() method.
    """

    _unfinished_tasks: int
    _finished: Event

    def _init(self, maxsize: int) -> None:
        self._queue: list[Queueable] = []
        self._maxsize: int = maxsize

    def _put(self, item: Queueable, heappush: Any = heapq.heappush) -> None:
        heappush(self._queue, item)

    def _get(self, heappop: Any = heapq.heappop) -> Queueable:
        return heappop(self._queue)

    def clear(self) -> None:
        """
        Clear the Queue of any unfinished tasks.
        """
        self._queue.clear()
        self._unfinished_tasks = 0
        self._finished.set()


class Stats(Enum):
    # Number of Requests added to the queue.
    REQUESTS_QUEUED = "requests_queued"
    # Number of HTTP Requests that were successful (HTTP Status code 200-299).
    REQUESTS_SUCCESSFUL = "requests_successful"
    # Number of HTTP Requests that were unsuccessful (HTTP Status code not in 200s).
    REQUESTS_FAILED = "requests_failed"
    # Total size in bytes of all HTTP Responses.
    CONTENT_LENGTH_TOTAL = "content_length_total"
    # Harmonic mean of total HTTP Response content length in bytes.
    CONTENT_LENGTH_AVG = "content_length_avg"
    # Highest HTTP Response content length in bytes.
    CONTENT_LENGTH_MAX = "content_length_max"
    # Lowest HTTP Response content length in bytes.
    CONTENT_LENGTH_MIN = "content_length_min"
    # Median HTTP Response content length in bytes.
    CONTENT_LENGTH_MEDIAN = "content_length_med"
    # Number of Items processed.
    ITEMS_PROCESSED = "items_processed"
    # Number of URls seen and added to duplicate filter.
    URLS_SEEN = "urls_seen"
    # Harmonic mean of Request duration in Milliseconds.
    REQUESTS_DURATION_AVG = "requests_duration_avg"
    # Highest Request duration in Milliseconds.
    REQUESTS_DURATION_MAX = "requests_duration_max"
    # Lowest Request duration in Milliseconds.
    REQUESTS_DURATION_MIN = "requests_duration_min"
    # Total Request duration in Milliseconds.
    REQUESTS_DURATION_TOTAL = "requests_duration_total"
    # Median Request duration in Milliseconds.
    REQUESTS_DURATION_MEDIAN = "requests_duration_med"
    # Harmonic mean of HTTP request latency in Milliseconds.
    REQUESTS_LATENCY_AVG = "requests_latency_avg"
    # Highest HTTP Request latency in Milliseconds.
    REQUESTS_LATENCY_MAX = "requests_latency_max"
    # Lowest HTTP Request latency in Milliseconds.
    REQUESTS_LATENCY_MIN = "requests_latency_min"
    # Median HTTP Request latency in Milliseconds.
    REQUESTS_LATENCY_MEDIAN = "requests_latency_med"
    # Total HTTP Request latency in Milliseconds.
    REQUESTS_LATENCY_TOTAL = "requests_latency_total"
    # Total duration of crawl in Milliseconds.
    TOTAL_DURATION = "total_duration"
    # Response status codes.
    STATUS_CODES = "status_codes"
    # Highest queue wait time in Milliseconds.
    QUEUE_WAIT_MAX = "queue_wait_max"
    # Lowest queue wait time in Milliseconds.
    QUEUE_WAIT_MIN = "queue_wait_min"
    # Harmonic mean of queue wait time in Milliseconds.
    QUEUE_WAIT_AVG = "queue_wait_avg"
    # Median queue wait time in Milliseconds.
    QUEUE_WAIT_MEDIAN = "queue_wait_med"
    # Highest queue size.
    QUEUE_SIZE_MAX = "queue_size_max"
    # Harmonic mean of queue size.
    QUEUE_SIZE_AVG = "queue_size_avg"
    # Median queue size.
    QUEUE_SIZE_MEDIAN = "queue_size_med"
    # Total objects put on queue.
    QUEUED_TOTAL = "queued_total"
    # Total number of retried Requests
    REQUESTS_RETRIED = "requests_retried"

    def __repr__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return str(self.value)

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Stats):
            return False
        return self.value < other.value


def coerce_url(
    url: Union[URL, str], https: bool = False, default_scheme: str = "http"
) -> URL:
    """
    Coerce URL to valid format

    :param url: URL
    :param https: Force https if no scheme in url
    :param default_scheme: Default scheme if not forcing https
    :return: str
    """
    if isinstance(url, str):
        url = URL(url.strip())

    scheme = "https" if https else default_scheme

    if not url.is_absolute():
        url_string = str(url)
        split = url_string.split("/", 1)
        url = URL.build(scheme=scheme, host=split[0])
        if len(split) > 1:
            url = url.with_path(split[1])

    if (url.scheme == "http" and https) or not url.scheme:
        url = url.with_scheme(scheme)

    return url


def to_bytes(text: str, encoding: str = "utf-8", errors: str = "strict") -> bytes:
    """Return the binary representation of `text`. If `text`
    is already a bytes object, return it as-is."""
    if not text:
        return b""
    if isinstance(text, bytes):
        return text
    return text.encode(encoding, errors)


def to_string(item: Any, encoding: str = "utf-8", errors: str = "strict") -> str:
    """
    Return the string representation of 'item'.
    """
    if item is None:
        return ""
    if isinstance(item, bytes):
        return item.decode(encoding, errors)
    return str(item)


def case_insensitive_key(key: str, dictionary: Dict[str, Any]) -> bool:
    """
    Check if a case-insensitive key is in a dictionary.
    """
    k = key.lower()
    for key in dictionary.keys():
        if key.lower() == k:
            return True
    return False


def headers_to_dict(headers: Any) -> Dict[str, str]:
    """
    Convert various header classes to a simple dictionary

    :param headers: Dict subclass of HTTP headers
    :return: Dict of HTTP headers
    """
    new_headers: Dict[str, str] = {}
    try:
        new_headers.update({k.lower(): v for (k, v) in headers.items()})
    except Exception as e:
        logger.warning("Exception parsing headers to dict: %s", e)
        pass
    return new_headers


def ignore_aiohttp_ssl_error(loop: Any, aiohttpversion: str = "3.5.4") -> None:
    """Ignore aiohttp #3535 issue with SSL data after close
     There appears to be an issue on Python 3.7 and aiohttp SSL that throws a
    ssl.SSLError fatal error (ssl.SSLError: [SSL: KRB5_S_INIT] application data
    after close notify (_ssl.c:2609)) after we are already done with the
    connection. See GitHub issue aio-libs/aiohttp#3535
     Given a loop, this sets up a exception handler that ignores this specific
    exception, but passes everything else on to the previous exception handler
    this one replaces.
     If the current aiohttp version is not exactly equal to aiohttpversion
    nothing is done, assuming that the next version will have this bug fixed.
    This can be disabled by setting this parameter to None
    """
    import asyncio
    import ssl

    import aiohttp

    try:
        # noinspection PyUnresolvedReferences
        import uvloop

        protocol_class = uvloop.loop.SSLProtocol  # type: ignore
    except ImportError:
        protocol_class = asyncio.sslproto.SSLProtocol  # type: ignore
        pass

    if aiohttpversion and aiohttp.__version__ != aiohttpversion:
        return

    orig_handler = loop.get_exception_handler()

    # noinspection PyUnresolvedReferences
    def ignore_ssl_error(this_loop: Any, context: Any) -> None:
        errors = ["SSL error", "Fatal error"]
        if any(x in context.get("message") for x in errors):
            # validate we have the right exception, transport and protocol
            exception = context.get("exception")
            protocol = context.get("protocol")
            if (
                isinstance(exception, ssl.SSLError)
                and exception.reason == "KRB5_S_INIT"
                and isinstance(protocol, protocol_class)
            ):
                if this_loop.get_debug():
                    asyncio.log.logger.debug("Ignoring aiohttp SSL KRB5_S_INIT error")  # type: ignore
                return
        if orig_handler is not None:
            orig_handler(this_loop, context)
        else:
            this_loop.default_exception_handler(context)

    loop.set_exception_handler(ignore_ssl_error)


def parse_href_to_url(href: str) -> Union[URL, None]:
    """
    Parse an href string to a URL object.

    :param href: An href string that may be a valid url.
    :return: URL or None.
    """
    if not href:
        return None

    try:
        return URL(href)
    except (UnicodeError, ValueError) as e:
        logger.warning("Failed to encode href: %s : %s", href, e)
        return None


def remove_www(host: str) -> str:
    """
    Remove www. subdomain from URL host strings.

    :param host: URL host without scheme or path. e.g. www.test.com
    :return: URL host string.
    """
    if host.startswith("www."):
        return host[4:]
    return host


def is_same_domain(root_domain: Union[str, None], url_domain: Union[str, None]) -> bool:
    """
    Check if the url domain is the same or a subdomain of the root domain.

    :param root_domain: Original root domain of this crawl
    :param url_domain: Domain of the url to filter
    :return: boolean
    """
    if not root_domain or not url_domain:
        return False
    return remove_www(root_domain) in url_domain


def parse_robots_txt(robots_txt: str, user_agent: str) -> List[str]:
    """
    Parses a robots.txt file and returns a list of disallowed paths.

    Args:
      robots_txt: The robots.txt file, as a string.

    Returns:
      A list of the the paths that are not allowed to be crawled.
    """
    # Create a regex pattern to match the "Disallow" lines in the robots.txt file
    disallow_pattern = re.compile(r"^Disallow:\.*(.*)$", re.MULTILINE)

    # Create a list to store the disallowed paths
    disallowed_paths: List[str] = []

    # Split the robots.txt file into lines
    lines = robots_txt.split("\n")

    # Flag to indicate whether we're currently in the section of the file that applies to our user-agent
    in_our_section = False

    # Loop through each line of the robots.txt file
    for line in lines:
        # If this line is the start of a section for a user-agent, check if it's our user-agent
        if line.startswith("User-agent:"):
            # Check if this user-agent section applies to our user-agent
            in_our_section = line.strip().endswith(user_agent) or line.strip().endswith(
                "*"
            )
        # If this line is a "Disallow" line and we're currently in our user-agent section,
        # add the disallowed path to our list
        elif in_our_section:
            disallowed = disallow_pattern.match(line)
            if disallowed:
                disallowed_paths.append(disallowed.group(1))

    # Return the list of disallowed paths
    return disallowed_paths


def parse_sitemap(sitemap_xml: str) -> List[str]:
    """Parses a sitemap XML file and returns URLs of potential RSS/Atom/JSON feeds.

    Enhanced to filter for feed-like URLs using multiple patterns:
    - URLs ending with .rss, .xml, .atom
    - URLs containing /rss, /feed, /atom in the path
    - URLs with feed-related segments like rss., feed., atom.

    Args:
      sitemap_xml: The sitemap XML file, as a string.

    Returns:
      A list of URLs that are likely to be feeds.
    """

    # Create a regex pattern to match the "loc" elements in the sitemap
    loc_pattern = re.compile(r"<loc>(.*?)</loc>")

    # Create a list to store the URLs of the feeds
    feed_urls: List[str] = []

    # Feed-like URL patterns to match
    feed_patterns = [
        "/rss",
        "/feed",
        "/atom",
        ".rss",
        ".xml",
        ".atom",
        "rss.",
        "feed.",
        "atom.",
        "/feeds/",
        "-feed",
        "_feed",
    ]

    # Use the regex pattern to find all the "loc" elements in the sitemap
    for loc_element in loc_pattern.finditer(sitemap_xml):
        # Get the URL from the "loc" element
        url = loc_element.group(1)
        url_lower = url.lower()

        # Check if URL matches any feed pattern
        if any(pattern in url_lower for pattern in feed_patterns):
            feed_urls.append(url)

    # Return the list of feed URLs
    return feed_urls
