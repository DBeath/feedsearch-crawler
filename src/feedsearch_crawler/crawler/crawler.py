import asyncio
import copy
import inspect
import logging
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from fnmatch import fnmatch
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Coroutine,
    Dict,
    Final,
    List,
    Optional,
    Set,
    Union,
)

import aiohttp
from aiohttp import ClientTimeout, TraceConfig
from yarl import URL

from feedsearch_crawler.crawler.downloader import Downloader
from feedsearch_crawler.crawler.duplicatefilter import DuplicateFilter
from feedsearch_crawler.crawler.item import Item
from feedsearch_crawler.crawler.lib import (
    CrawlerPriorityQueue,
    Stats,
    coerce_url,
    ignore_aiohttp_ssl_error,
    parse_href_to_url,
)
from feedsearch_crawler.crawler.middleware.content_type import ContentTypeMiddleware
from feedsearch_crawler.crawler.middleware.cookie import CookieMiddleware
from feedsearch_crawler.crawler.middleware.monitoring import MonitoringMiddleware
from feedsearch_crawler.crawler.middleware.retry import RetryMiddleware
from feedsearch_crawler.crawler.middleware.robots import RobotsMiddleware
from feedsearch_crawler.crawler.middleware.throttle import ThrottleMiddleware
from feedsearch_crawler.crawler.queueable import CallbackResult, Queueable
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
from feedsearch_crawler.crawler.statistics import (
    ErrorCategory,
    StatisticsLevel,
    StatsCollector,
)
from feedsearch_crawler.crawler.trace import add_trace_config

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    uvloop = None
    pass


logger = logging.getLogger(__name__)

DEFAULT_TOTAL_TIMEOUT: Final[float] = 30.0
DEFAULT_REQUEST_TIMEOUT: Final[float] = 5.0
DEFAULT_MAX_CONTENT_LENGTH: Final[int] = 1024 * 1024 * 10


class Crawler(ABC):
    # Class Name of the Duplicate Filter.
    # May be overridden to use different Duplicate Filter.
    # Not an instantiation of the class.
    duplicate_filter_class = DuplicateFilter

    # Callback to be run after all workers are finished.
    post_crawl_callback = None

    # URLs to start the crawl.
    start_urls: List[Union[str, URL]] = []
    # Domain patterns that are allowed to be crawled.
    allowed_domains = []

    # Max number of concurrent http requests.
    concurrency: int = 10
    # Max size of incoming http response content.
    max_content_length = 1024 * 1024 * 10
    # Max crawl depth. i.e. The max length of the response history.
    max_depth: int = 4
    # Max callback recursion depth, to prevent accidental infinite recursion from AsyncGenerators.
    max_callback_recursion: int = 10
    # Time in seconds to delay each HTTP request.
    delay: float = 0

    # List of worker tasks.
    _workers = []

    # ClientSession for requests. Created on Crawl start.
    _session: aiohttp.ClientSession
    # Task queue for Requests. Created on Crawl start.
    _request_queue: CrawlerPriorityQueue
    # Semaphore for controlling HTTP Request concurrency.
    _download_semaphore: asyncio.Semaphore
    # Semaphore for controlling parsing concurrency.
    _parse_semaphore: asyncio.Semaphore

    def __init__(
        self,
        start_urls: List[Union[str, URL]] = [],
        allowed_domains: List[str] = [],
        concurrency: int = 10,
        total_timeout: Union[float, ClientTimeout] = DEFAULT_TOTAL_TIMEOUT,
        request_timeout: Union[float, ClientTimeout] = DEFAULT_REQUEST_TIMEOUT,
        user_agent: str = "",
        max_content_length: int = DEFAULT_MAX_CONTENT_LENGTH,
        max_depth: int = 10,
        headers: dict = {},
        allowed_schemes: List[str] = [],
        delay: float = 0.5,
        max_retries: int = 3,
        ssl: bool = False,
        trace: bool = False,
        respect_robots: bool = True,
        stats_level: StatisticsLevel = StatisticsLevel.STANDARD,
        stats_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        stats_callback_interval: float = 5.0,
        *args,
        **kwargs,
    ):
        """
        Base class for a WebCrawler implementation.

        :param allowed_schemes: List of strings of allowed Request URI schemes. e.g. ["http", "https"]
        :param start_urls: List of initial URLs to crawl.
        :param allowed_domains: List of domain patterns that are allowed. Uses Unix shell-style wildcards.
        :param concurrency: Max number of workers and of concurrent HTTP requests.
        :param total_timeout: Total aiohttp ClientSession timeout in seconds.
            Crawl will end if this timeout is triggered.
        :param request_timeout: Total timeout in seconds for each individual HTTP request.
        :param user_agent: Default User-Agent for HTTP requests.
        :param max_content_length: Max size in bytes of incoming http response content.
        :param max_depth: Max crawl depth. i.e. The max length of the response history.
        :param headers: Default HTTP headers to be included in each request.
        :param delay: Time in seconds to delay each HTTP request.
        :param max_retries: Maximum number of retries for each failed HTTP request.
        :param ssl: Enables strict SSL checking.
        :param trace: Enables aiohttp trace debugging.
        :param respect_robots: If True, fetch robots.txt first and respect disallow rules. Default True.
        :param stats_level: Statistics collection level (MINIMAL/STANDARD/DETAILED).
        :param stats_callback: Optional callback for real-time statistics updates.
        :param stats_callback_interval: Seconds between statistics callback invocations.
        :param args: Additional positional arguments for subclasses.
        :param kwargs: Additional keyword arguments for subclasses.
        """
        self.start_urls = start_urls or []
        self.allowed_domains = allowed_domains or []

        self.concurrency = concurrency

        if not isinstance(total_timeout, ClientTimeout):
            total_timeout = ClientTimeout(total=float(total_timeout))
        if not isinstance(request_timeout, ClientTimeout):
            request_timeout = ClientTimeout(total=float(request_timeout))

        self.total_timeout: ClientTimeout = total_timeout
        self.request_timeout: ClientTimeout = request_timeout

        self.max_content_length = max_content_length
        self.max_depth = max_depth

        self.user_agent = user_agent or (
            "Mozilla/5.0 (compatible; Feedsearch-Crawler; +https://pypi.org/project/feedsearch-crawler)"
        )

        self.headers = {"User-Agent": self.user_agent, "Upgrade-Insecure-Requests": "1"}

        if headers:
            self.headers = {**self.headers, **headers}

        self.allowed_schemes = allowed_schemes
        self.delay = delay
        self.max_retries = max_retries
        self._ssl = ssl
        self._trace = trace
        self.respect_robots = respect_robots

        # Default set for parsed items.
        self.items: set[Item] = set()

        # URL Duplicate Filter instance.
        self._duplicate_filter = self.duplicate_filter_class()

        # Store robots.txt and sitemap information
        self._robots_middleware: Optional[RobotsMiddleware] = None
        self._sitemap_urls: Dict[str, List[str]] = {}  # host -> list of sitemap URLs

        # New StatsCollector for efficient statistics tracking
        self.stats_collector = StatsCollector(
            level=stats_level,
            callback=stats_callback,
            callback_interval=stats_callback_interval,
        )

        # Legacy stats dictionary (kept for backward compatibility)
        # Will be populated from stats_collector.get_stats()
        self.stats: Dict[Stats, Any] = {
            Stats.REQUESTS_QUEUED: 0,
            Stats.REQUESTS_SUCCESSFUL: 0,
            Stats.REQUESTS_FAILED: 0,
            Stats.CONTENT_LENGTH_TOTAL: 0,
            Stats.CONTENT_LENGTH_AVG: 0,
            Stats.CONTENT_LENGTH_MIN: 0,
            Stats.CONTENT_LENGTH_MAX: 0,
            Stats.CONTENT_LENGTH_MEDIAN: 0,
            Stats.ITEMS_PROCESSED: 0,
            Stats.URLS_SEEN: 0,
            Stats.REQUESTS_DURATION_AVG: 0,
            Stats.REQUESTS_DURATION_MAX: 0,
            Stats.REQUESTS_DURATION_MIN: 0,
            Stats.REQUESTS_DURATION_TOTAL: 0,
            Stats.REQUESTS_DURATION_MEDIAN: 0,
            Stats.REQUESTS_LATENCY_AVG: 0,
            Stats.REQUESTS_LATENCY_MAX: 0,
            Stats.REQUESTS_LATENCY_MIN: 0,
            Stats.REQUESTS_LATENCY_MEDIAN: 0,
            Stats.REQUESTS_LATENCY_TOTAL: 0,
            Stats.TOTAL_DURATION: 0,
            Stats.STATUS_CODES: {},
            Stats.QUEUE_WAIT_MAX: 0,
            Stats.QUEUE_WAIT_MIN: 0,
            Stats.QUEUE_WAIT_AVG: 0,
            Stats.QUEUE_WAIT_MEDIAN: 0,
            Stats.QUEUE_SIZE_MAX: 0,
            Stats.QUEUE_SIZE_AVG: 0,
            Stats.QUEUE_SIZE_MEDIAN: 0,
            Stats.QUEUED_TOTAL: 0,
            Stats.REQUESTS_RETRIED: 0,
        }

        # Build middleware list - conditionally add RobotsMiddleware
        self.middlewares = []
        if self.respect_robots:
            self._robots_middleware = RobotsMiddleware(user_agent=self.user_agent)
            self.middlewares.append(self._robots_middleware)

        self.middlewares.extend(
            [
                ThrottleMiddleware(rate_per_sec=2),
                RetryMiddleware(max_retries=3),
                CookieMiddleware(),
                ContentTypeMiddleware(),
                MonitoringMiddleware(),
            ]
        )

    async def _handle_request(self, request: Request) -> None:
        """
        Handle fetching of Requests and processing of Request callbacks.

        :param request: Request
        :return: None
        """
        try:
            if request.has_run and not request.should_retry:
                logger.warning("%s has already run", request)
                return

            start = time.perf_counter()

            # Fetch the request using the downloader
            async with self._download_semaphore:
                response = await self._downloader.fetch(request)

            # Run the callback if available (parsing can be done with separate concurrency limit)
            callback_result = None
            if response.ok and request.callback:
                async with self._parse_semaphore:
                    callback_result = request.callback(
                        request=request, response=response, **request.cb_kwargs
                    )
            elif not response.ok and request.failure_callback:
                async with self._parse_semaphore:
                    callback_result = request.failure_callback(
                        request=request, response=response, **request.cb_kwargs
                    )

            dur_ms = (time.perf_counter() - start) * 1000
            latency_ms = getattr(response, "latency_ms", dur_ms)

            logger.debug(
                "Fetched: url=%s dur=%.2fms status=%s",
                response.url,
                dur_ms,
                response.status_code,
            )

            # Record in new stats collector
            if response.ok:
                await self.stats_collector.record_request_successful(
                    status_code=response.status_code,
                    duration_ms=dur_ms,
                    latency_ms=latency_ms,
                    content_length=response.content_length,
                    host=response.url.host,
                )
            else:
                # Categorize error based on status code
                error_category = ErrorCategory.OTHER
                if response.status_code >= 500:
                    error_category = ErrorCategory.HTTP_SERVER
                elif response.status_code >= 400:
                    error_category = ErrorCategory.HTTP_CLIENT

                await self.stats_collector.record_request_failed(
                    error_category=error_category,
                    error_message=f"HTTP {response.status_code}",
                    status_code=response.status_code,
                    url=str(response.url),
                )

            # Mark the Response URL as seen in the duplicate filter, as it may be different from the Request URL
            # due to redirects.
            await self._duplicate_filter.is_url_seen(response.url, response.method)

            # Add callback results to the queue for processing.
            if callback_result:
                self._put_queue(CallbackResult(callback_result, 0))

            # Add Request back to the queue for retrying.
            if request.should_retry:
                await self.stats_collector.record_request_retried()
                self._put_queue(request)

        except asyncio.CancelledError as e:
            logger.debug("Cancelled: %s, %s", request, e)
        except Exception as e:
            logger.exception("Exception during %s: %s", request, e)
        finally:
            return

    async def _process_request_callback_result(
        self,
        result: Union[
            CallbackResult,
            AsyncGenerator[Any, Any],
            Coroutine[Any, Any, Any],
            Request,
            Item,
        ],
        callback_recursion: int = 0,
    ) -> None:
        """
        Process the Request callback result depending on the result type.
        Request callbacks may contain nested iterators.

        :param result: Callback Result. May be an CallbackResult class, AsyncGenerator, Coroutine, Request, or Item.
        :param callback_recursion: Incremented counter to limit this method's recursion.
        :return: None
        """
        if callback_recursion >= self.max_callback_recursion:
            logger.warning(
                "Max callback recursion of %d reached for %s",
                self.max_callback_recursion,
                result,
            )
            return

        try:
            # If a CallbackResult class is passed, process the result values from within the class.
            if isinstance(result, CallbackResult):
                await self._process_request_callback_result(
                    result.item, result.callback_recursion
                )
            # For async generators, put each value back on the queue for processing.
            # This will happen recursively until the end of the recursion chain or max_callback_recursion is reached.
            elif inspect.isasyncgen(result):
                async for value in result:
                    if value:
                        self._put_queue(CallbackResult(value, callback_recursion + 1))
            # For coroutines, await the result then put the value back on the queue for further processing.
            elif inspect.iscoroutine(result):
                value = await result
                self._put_queue(CallbackResult(value, callback_recursion + 1))
            # Requests are put onto the queue to be fetched.
            elif isinstance(result, Request):
                self._process_request(result)

            # Items are handled by the implementing Class.
            elif isinstance(result, Item):
                await self.process_item(result)
                await self.stats_collector.record_item_processed()
        except Exception as e:
            logger.exception(e)

    def _process_request(self, request: Request) -> None:
        """
        Process a Request onto the Request Queue.

        :param request: HTTP Request
        :return: None
        """
        if not request:
            return

        priority: int = request.priority or 100

        # Record queued request (sync call for performance)
        self.stats_collector.record_request_queued()
        logger.debug("Queue Add: %s", request)
        # Add the Request to the queue for processing.
        # Request is already a Queueable, so just set its priority and add it directly
        request.priority = priority
        self._put_queue(request)

    def is_allowed_domain(self, url: URL) -> bool:
        """
        Check that the URL host is in the list of allowed domain patterns.
        Domain patterns are Unix shell-style wildcards.
        https://docs.python.org/3/library/fnmatch.html

        :param url: URL object
        :return: boolean
        """
        if not self.allowed_domains:
            return True

        try:
            if not url or not url.host:
                return False
            host = url.host
            for domain_pattern in self.allowed_domains:
                if fnmatch(host, domain_pattern):
                    return True
        except Exception as e:
            logger.warning(e)
        return False

    async def follow(
        self,
        url: Union[str, URL],
        callback: Callable,
        response: Optional[Response] = None,
        max_content_length: Optional[int] = None,
        timeout: Optional[float] = None,
        method: str = "GET",
        delay: float = 0,
        priority: int = 0,
        allow_domain: bool = False,
        cb_kwargs: Dict = {},
        retries: int = 0,
        **kwargs,
    ) -> Optional[Request]:
        """
        Follow a URL by creating an HTTP Request.

        If the URL is not absolute then it is joined with the previous Response URL.
        The previous Response history is copied to the Request.

        Before a Request is followed, first check that the Request URL has not already been seen,
        that the max URL depth has not been reached, and that the URI scheme is allowed.

        These checks are performed before the Request is created so that we don't yield multiple requests
        to the same URL to the queue for further processing. We want to stop duplicates and invalid
        requests as early as possible.

        :param url: URL to follow.
        :param callback: Callback method to run if the Request is successful.
        :param response: Previous Response that contained the Request URL.
        :param kwargs: Optional Request keyword arguments. See Request for details.
        :param method: HTTP method for Request.
        :param delay: Optionally override the default delay for the Request.
        :param priority: Optionally override the default priority of the Request.
        :param allow_domain: Optionally override the allowed domains check.
        :param max_content_length: Optionally override the maximum allowed size in bytes of Response body.
        :param retries: Optionally override the number of Request retries.
        :param timeout: Optionally override the Request timeout.
        :param cb_kwargs: Optional Dictionary of keyword arguments to be passed to the callback function.
        :return: Request
        """
        original_url = copy.copy(url)
        request_url: URL
        if isinstance(url, str):
            parsed_url: Union[URL, None] = parse_href_to_url(url)
            if not parsed_url:
                logger.warning("Cannot parse str to URL: %s", original_url)
                return
            request_url = parsed_url
        else:
            request_url = url

        if not request_url:
            logger.warning("Attempted to follow invalid URL: %s", original_url)
            return

        history: List[URL] = []
        if response:
            # Join the URL to the Response URL if it doesn't contain a domain.
            if not request_url.is_absolute() or not request_url.scheme:
                request_url = coerce_url(
                    response.origin.join(request_url), default_scheme=response.scheme
                )

            # Restrict the depth of the Request chain to the maximum depth.
            # This test happens before the URL duplicate check so that the URL might still be reachable by another path.
            if self.max_depth and len(response.history) >= self.max_depth:
                logger.debug("Max Depth of '%d' reached: %s", self.max_depth, url)
                return

            # Copy the Response history so that it isn't a reference to a mutable object.
            history = copy.deepcopy(response.history)
        else:
            if not request_url.is_absolute():
                logger.debug("URL should have domain: %s", url)
                return

            if not request_url.scheme:
                url = coerce_url(url)

        # The URL scheme must be in the list of allowed schemes.
        if self.allowed_schemes and request_url.scheme not in self.allowed_schemes:
            logger.debug("URI Scheme '%s' not allowed: %s", request_url.scheme, url)
            return

        # The URL host must be in the list of allowed domains.
        if not allow_domain and not self.is_allowed_domain(request_url):
            logger.debug("Domain '%s' not allowed: %s", request_url.host, url)
            return

        # Check if URL is not already seen, and add it to the duplicate filter seen list.
        is_duplicate = await self._duplicate_filter.is_url_seen(request_url, method)
        await self.stats_collector.record_url_seen(is_duplicate=is_duplicate)
        if is_duplicate:
            return

        request = Request(
            url=request_url,
            history=history,
            callback=callback,
            max_content_length=max_content_length or self.max_content_length,
            timeout=timeout or self.request_timeout,
            method=method,
            delay=delay if delay else self.delay,
            retries=retries or self.max_retries,
            cb_kwargs=cb_kwargs,
            **kwargs,
        )

        # Override the Request priority only if the kwarg is provided.
        if priority:
            request.priority = priority

        return request

    @abstractmethod
    async def process_item(self, item: Item) -> None:
        """
        Processed a parsed Item in some way. e.g. Add it to the Item set, or database, or send a signal.

        :param item: A parsed Item.
        """
        raise NotImplementedError("Not Implemented")

    @abstractmethod
    async def parse_response_content(self, response_text: str) -> Any:
        """
        Parse Response content.
        Used to allow implementations to provide their own HTML parser.

        :param response_text: Response text as string.
        """
        raise NotImplementedError("Not Implemented")

    @abstractmethod
    def parse_response(
        self, request: Request, response: Response
    ) -> AsyncGenerator[Any, Any]:
        """
        Parse an HTTP Response. Must yield Items, Requests, AsyncGenerators, or Coroutines.

        :param request: HTTP Request that created the Response.
        :param response: HTTP Response.
        """
        raise NotImplementedError("Not Implemented")

    async def parse_robots_txt(
        self, request: Request, response: Response
    ) -> AsyncGenerator[Any, Any]:
        """Parse robots.txt response and queue sitemap requests.

        This callback is called when a robots.txt file is fetched.
        It extracts sitemap URLs and creates high-priority requests for them.

        Sitemaps are always fetched regardless of respect_robots setting
        to discover feed URLs.

        :param request: HTTP Request for robots.txt
        :param response: HTTP Response containing robots.txt
        :return: AsyncGenerator yielding sitemap Requests
        """
        if not response.ok or not response.text:
            return

        # Extract sitemaps from robots.txt content
        sitemap_urls = self._extract_sitemap_urls_from_text(response.text)

        if sitemap_urls:
            logger.info(
                f"Found {len(sitemap_urls)} sitemap(s) in {response.url}: {sitemap_urls}"
            )

        # Queue sitemap requests with priority=5 (high priority, after robots.txt)
        for sitemap_url in sitemap_urls:
            req = await self.follow(
                sitemap_url,
                self.parse_sitemap,
                priority=5,
                allow_domain=True,
            )
            if req:
                yield req

    async def parse_sitemap(
        self, request: Request, response: Response
    ) -> AsyncGenerator[Any, Any]:
        """Parse sitemap XML and extract feed URLs.

        This callback parses sitemap.xml files and extracts feed-like URLs.
        Discovered URLs are queued with priority=10.

        :param request: HTTP Request for sitemap
        :param response: HTTP Response containing sitemap XML
        :return: AsyncGenerator yielding feed URL Requests
        """
        if not response.ok or not response.text:
            return

        # Use enhanced parse_sitemap function from lib
        from feedsearch_crawler.crawler.lib import parse_sitemap

        feed_urls = parse_sitemap(response.text)

        if feed_urls:
            logger.info(
                f"Found {len(feed_urls)} potential feed URL(s) in {response.url}"
            )

        # Queue discovered URLs with priority=10 (medium-high priority)
        for url in feed_urls:
            req = await self.follow(
                url,
                self.parse_response_content,  # Use normal spider callback
                response=response,
                priority=10,
                allow_domain=True,
            )
            if req:
                yield req

    def _extract_sitemap_urls_from_text(self, robots_txt: str) -> List[str]:
        """Extract sitemap URLs from robots.txt content.

        :param robots_txt: Content of robots.txt file
        :return: List of sitemap URLs
        """
        sitemap_urls: List[str] = []
        for line in robots_txt.split("\n"):
            line = line.strip()
            if line.lower().startswith("sitemap:"):
                # Extract URL after "Sitemap:"
                sitemap_url = line.split(":", 1)[1].strip()
                if sitemap_url:
                    sitemap_urls.append(sitemap_url)
        return sitemap_urls

    def _get_robots_txt_url(self, url: URL) -> str:
        """Get robots.txt URL for a given domain URL.

        :param url: Domain URL
        :return: robots.txt URL for the domain
        """
        return f"{url.scheme}://{url.host}/robots.txt"

    def _put_queue(self, queueable: Queueable) -> None:
        """
        Put an object that inherits from Queueable onto the Request Queue.

        :param queueable: An object that inherits from Queueable.
        """
        queueable.set_queue_put_time()
        self._request_queue.put_nowait(queueable)
        self.stats[Stats.QUEUED_TOTAL] += 1

    async def _work(self, task_num: int) -> None:
        """
        Worker function for handling request queue items.
        """
        try:
            while True:
                self._stats_queue_sizes.append(self._request_queue.qsize())
                queue_item: Queueable = await self._request_queue.get()

                if item_wait_time := queue_item.get_queue_wait_time():
                    self._stats_queue_wait_times.append(item_wait_time)

                if self._session.closed:
                    logger.debug("Session is closed. Cannot run %s", queue_item)
                    continue

                try:
                    # Process Callback results
                    if isinstance(queue_item, CallbackResult):
                        await self._process_request_callback_result(
                            queue_item.item, queue_item.callback_recursion
                        )
                    else:
                        item: Request | CallbackResult = queue_item.item
                        # Fetch Request and handle callbacks
                        if isinstance(item, Request):
                            await self._handle_request(item)
                        # Process Callback results
                        elif isinstance(item, CallbackResult):
                            await self._process_request_callback_result(
                                item.item, item.callback_recursion
                            )

                except Exception as e:
                    logger.exception("Error handling item: %s : %s", item, e)
                finally:
                    self._request_queue.task_done()
        except asyncio.CancelledError:
            logger.debug("Cancelled Worker: %s", task_num)

    @staticmethod
    async def _run_callback(callback: Any, *args: Any, **kwargs: Any) -> None:
        """
        Runs a callback function.

        :param callback: Function to run. May be async.
        :param args: Positional arguments to pass to the function.
        :param kwargs: Keyword arguments to pass to the function.
        :return: None
        """
        if not callback:
            return
        if inspect.iscoroutinefunction(callback):
            await callback(*args, **kwargs)
        elif inspect.isfunction(callback):
            callback(*args, **kwargs)
        else:
            logger.warning("Callback %s must be a coroutine or function", callback)

    def create_start_urls(self, urls: List[Union[URL, str]]) -> List[URL]:
        """
        Create the start URLs for the crawl from an initial URL. May be overridden.

        :param urls: Initial URLs
        """
        crawl_start_urls: Set[URL] = set()

        for url in urls + self.start_urls:
            if isinstance(url, str):
                if "//" not in url:
                    url = f"//{url}"
                url = URL(url)

            if url.scheme.lower() not in ["http", "https"]:
                url = url.with_scheme("http")

            crawl_start_urls.add(url)

        return list(crawl_start_urls)

    def record_statistics(self) -> None:
        """
        Record statistics and update legacy stats dict for backward compatibility.
        """
        # Get statistics from new collector
        new_stats = self.stats_collector.get_stats()

        # Map new stats to legacy Stats enum keys
        summary = new_stats.get("summary", {})
        requests = new_stats.get("requests", {})
        items = new_stats.get("items", {})
        urls = new_stats.get("urls", {})
        performance = new_stats.get("performance", {})
        content = new_stats.get("content", {})
        queue = new_stats.get("queue", {})

        # Update legacy stats dictionary
        self.stats[Stats.REQUESTS_QUEUED] = requests.get("queued", 0)
        self.stats[Stats.REQUESTS_SUCCESSFUL] = requests.get("successful", 0)
        self.stats[Stats.REQUESTS_FAILED] = requests.get("failed", 0)
        self.stats[Stats.REQUESTS_RETRIED] = requests.get("retried", 0)
        self.stats[Stats.ITEMS_PROCESSED] = items.get("processed", 0)
        self.stats[Stats.URLS_SEEN] = urls.get("seen", 0)
        self.stats[Stats.TOTAL_DURATION] = int(
            summary.get("total_duration_sec", 0) * 1000
        )
        self.stats[Stats.STATUS_CODES] = new_stats.get("status_codes", {})

        # Request duration stats
        req_dur = performance.get("request_duration_ms", {})
        self.stats[Stats.REQUESTS_DURATION_AVG] = int(req_dur.get("mean", 0))
        self.stats[Stats.REQUESTS_DURATION_MIN] = int(req_dur.get("min", 0))
        self.stats[Stats.REQUESTS_DURATION_MAX] = int(req_dur.get("max", 0))
        self.stats[Stats.REQUESTS_DURATION_MEDIAN] = int(
            performance.get("request_duration_percentiles_ms", {}).get("p50", 0)
        )

        # Request latency stats
        req_lat = performance.get("request_latency_ms", {})
        self.stats[Stats.REQUESTS_LATENCY_AVG] = int(req_lat.get("mean", 0))
        self.stats[Stats.REQUESTS_LATENCY_MIN] = int(req_lat.get("min", 0))
        self.stats[Stats.REQUESTS_LATENCY_MAX] = int(req_lat.get("max", 0))
        self.stats[Stats.REQUESTS_LATENCY_MEDIAN] = int(
            performance.get("request_latency_percentiles_ms", {}).get("p50", 0)
        )

        # Content length stats
        self.stats[Stats.CONTENT_LENGTH_TOTAL] = content.get("total_bytes", 0)
        self.stats[Stats.CONTENT_LENGTH_AVG] = content.get("mean_bytes", 0)
        self.stats[Stats.CONTENT_LENGTH_MIN] = content.get("min_bytes", 0)
        self.stats[Stats.CONTENT_LENGTH_MAX] = content.get("max_bytes", 0)

        # Queue stats
        queue_wait = queue.get("wait_time_ms", {})
        self.stats[Stats.QUEUE_WAIT_AVG] = queue_wait.get("mean", 0)
        self.stats[Stats.QUEUE_WAIT_MIN] = queue_wait.get("min", 0)
        self.stats[Stats.QUEUE_WAIT_MAX] = queue_wait.get("max", 0)

        queue_size = queue.get("size", {})
        self.stats[Stats.QUEUE_SIZE_AVG] = int(queue_size.get("mean", 0))
        self.stats[Stats.QUEUE_SIZE_MAX] = int(queue_size.get("max", 0))

    def get_stats(self) -> Dict[str, Any]:
        """
        Return crawl statistics in new grouped format.
        For legacy format, use get_legacy_stats().
        """
        return self.stats_collector.get_stats()

    def get_legacy_stats(self) -> Dict[str, Any]:
        """
        Return crawl statistics in legacy flat format (backward compatibility).
        """
        stats = {str(k): v for k, v in self.stats.items()}
        return dict(OrderedDict(sorted(stats.items())).items())

    async def crawl(self, urls: Union[URL, str, List[Union[URL, str]]] = []) -> None:
        """
        Start the web crawler.

        :param urls: An optional URL or List of URLS to start the crawl, in addition to start_urls.
        """

        # Fix for ssl errors
        ignore_aiohttp_ssl_error(asyncio.get_running_loop())

        # Start statistics collection
        self.stats_collector.start()

        # Create start urls from the initial URL if provided.
        if not urls:
            urls = []
        if isinstance(urls, (URL, str)):
            urls = [urls]
        initial_urls = self.create_start_urls(urls)

        if not initial_urls:
            raise ValueError("crawler.start_urls are required")

        # Create the Request Queue within the asyncio loop (unless already set by tests).
        if not hasattr(self, "_request_queue") or self._request_queue is None:
            self._request_queue = CrawlerPriorityQueue()

        # Create semaphores for controlling different types of concurrency within the asyncio loop.
        self._download_semaphore = asyncio.Semaphore(self.concurrency)
        self._parse_semaphore = asyncio.Semaphore(
            self.concurrency * 2
        )  # Allow more parsing concurrency

        trace_configs: List[TraceConfig] = []
        if self._trace:
            trace_configs.append(add_trace_config())

        ttl_dns_cache: float = (
            self.total_timeout.total
            if self.total_timeout.total is not None
            else DEFAULT_TOTAL_TIMEOUT
        )
        conn = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=self.concurrency,  # Per-host limit matches concurrency
            ssl=self._ssl,
            ttl_dns_cache=int(ttl_dns_cache),
            enable_cleanup_closed=True,  # Clean up closed connections
            keepalive_timeout=30,  # Keep connections alive for reuse
            force_close=False,  # Reuse connections
            use_dns_cache=True,  # Enable DNS caching
            family=0,  # Allow both IPv4/IPv6 (socket.AF_UNSPEC)
            happy_eyeballs_delay=0.25,  # Fast IPv6 fallback
        )
        # Create the ClientSession for HTTP Requests within the asyncio loop.
        self._session = aiohttp.ClientSession(
            timeout=self.total_timeout,
            headers=self.headers,
            connector=conn,
            trace_configs=trace_configs,
        )

        # Create the Downloader with the session and middleware
        self._downloader = Downloader(
            request_session=self._session,
            middlewares=self.middlewares,
        )

        # Queue robots.txt AND standard sitemap.xml URLs immediately (parallel fetch)
        # robots.txt has priority=1, sitemaps have priority=5
        # Any additional sitemaps discovered from robots.txt will be added later
        robots_urls_added = set()
        sitemap_urls_added = set()

        for url in initial_urls:
            coerced_url = coerce_url(url)

            # Queue robots.txt (priority=1)
            robots_url = self._get_robots_txt_url(coerced_url)
            if robots_url not in robots_urls_added:
                robots_req = await self.follow(
                    robots_url,
                    self.parse_robots_txt,
                    priority=1,  # Highest priority
                    allow_domain=True,
                )
                if robots_req:
                    self._process_request(robots_req)
                    robots_urls_added.add(robots_url)
                    logger.debug(f"Queued robots.txt: {robots_url}")

            # Queue standard sitemap.xml (priority=5) - doesn't wait for robots.txt
            standard_sitemap_url = (
                f"{coerced_url.scheme}://{coerced_url.host}/sitemap.xml"
            )
            if standard_sitemap_url not in sitemap_urls_added:
                sitemap_req = await self.follow(
                    standard_sitemap_url,
                    self.parse_sitemap,
                    priority=5,  # High priority, but after robots.txt
                    allow_domain=True,
                )
                if sitemap_req:
                    self._process_request(sitemap_req)
                    sitemap_urls_added.add(standard_sitemap_url)
                    logger.debug(f"Queued standard sitemap: {standard_sitemap_url}")

        # Create a Request for each start URL and add it to the Request Queue (priority=100 default).
        for url in initial_urls:
            req = await self.follow(coerce_url(url), self.parse_response, delay=0)
            if req:
                self._process_request(req)

        # Create workers to process the Request Queue.
        # Optimize worker count - enough to handle requests and callbacks without excessive overhead
        worker_count = min(max(self.concurrency, int(self.concurrency * 1.5)), 20)
        self._workers = [
            asyncio.create_task(self._work(i)) for i in range(worker_count)
        ]

        try:
            # Run workers within the ClientSession.
            async with self._session:
                await asyncio.wait_for(
                    self._request_queue.join(), timeout=self.total_timeout.total
                )
        except asyncio.TimeoutError:
            logger.debug("Timed out after %s seconds", self.total_timeout.total)
            self._request_queue.clear()
        finally:
            # Make sure all workers are cancelled.
            for w in self._workers:
                w.cancel()
            # Wait until all worker tasks are cancelled.
            await asyncio.gather(*self._workers, return_exceptions=True)

        # Run the post crawl callback if it exists.
        await self._run_callback(self.post_crawl_callback)

        # The ClientSession is closed only after all work is completed.
        await self._session.close()

        # Stop statistics collection
        await self.stats_collector.stop()

        self.record_statistics()

        logger.info(
            "Crawl finished: requests=%s time=%.2fs",
            self.stats[Stats.REQUESTS_QUEUED],
            self.stats[Stats.TOTAL_DURATION] / 1000,
        )
        logger.debug("Stats: %s", self.stats)
