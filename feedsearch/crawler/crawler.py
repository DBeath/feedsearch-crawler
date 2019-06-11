import asyncio
import copy
import inspect
import logging
import time
from abc import ABC, abstractmethod
from types import AsyncGeneratorType
from typing import List, Any
from typing import Union

import aiohttp
from aiohttp import ClientTimeout
from yarl import URL

from feedsearch.crawler.duplicatefilter import DuplicateFilter
from feedsearch.crawler.item import Item
from feedsearch.crawler.lib import coerce_url, case_insensitive_key
from feedsearch.crawler.request import Request
from feedsearch.crawler.response import Response

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    uvloop = None
    pass


class Crawler(ABC):
    duplicate_filter_class = DuplicateFilter
    post_crawl_callback = None

    concurrency: int = 10
    max_request_size = 1024 * 1024 * 10
    max_depth: int = 0
    max_callback_recursion: int = 10

    workers = []

    total_timeout: ClientTimeout
    request_timeout: ClientTimeout

    stats: dict = {
        "requests_added": 0,
        "requests_successful": 0,
        "requests_failed": 0,
        "total_content_length": 0,
        "items_processed": 0,
        "urls_seen": 0,
    }

    _dupefilter = None

    def __init__(
        self,
        start_urls: List = None,
        concurrency: int = 10,
        total_timeout: Union[float, ClientTimeout] = 10,
        request_timeout: Union[float, ClientTimeout] = 3,
        user_agent: str = "",
        max_request_size: int = 1024 * 1024 * 10,
        max_depth: int = 10,
        headers: dict = None,
        *args,
        **kwargs,
    ):
        self.start_urls = start_urls or []
        self.concurrency = concurrency
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36"
        )

        if not isinstance(total_timeout, ClientTimeout):
            total_timeout = aiohttp.ClientTimeout(total=total_timeout)
        if not isinstance(request_timeout, ClientTimeout):
            request_timeout = aiohttp.ClientTimeout(total=request_timeout)

        self.total_timeout = total_timeout
        self.request_timeout = request_timeout

        self.max_request_size = max_request_size
        self.max_depth = max_depth

        self.headers = headers or {"User-Agent": self.user_agent}

        if not case_insensitive_key("User-Agent", self.headers):
            self.headers["User-Agent"] = self.user_agent

        self.logger = logging.getLogger(__name__)

        self.session = None
        self.request_queue = None
        self.items = set()
        self.seen_lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(self.concurrency)

        self._dupefilter = self.duplicate_filter_class()

    async def _handle_request(self, request: Request):
        try:
            start = time.perf_counter()

            results, response = await request.fetch_callback(self.semaphore)

            dur = int((time.perf_counter() - start) * 1000)
            self.logger.debug(
                "Fetched: url=%s dur=%dms status=%s prev=%s",
                response.url,
                dur,
                response.status_code,
                response.originator_url,
            )

            if response.ok:
                self.stats["requests_successful"] += 1
            else:
                self.stats["requests_failed"] += 1

            self.stats["total_content_length"] += response.content_length

            await self._dupefilter.url_seen(response.url, response.method)

            if results:
                await self._process_request_callback_result(results)

        except asyncio.CancelledError:
            self.logger.debug("Cancelled %s", request)
        except Exception as e:
            self.logger.exception("Exception during %s, %s", request, e)
        finally:
            return

    async def _process_request_callback_result(
        self, result: Any, callback_recursion: int = 0
    ):
        if callback_recursion >= self.max_callback_recursion:
            return

        try:
            if inspect.isasyncgen(result):
                async for value in result:
                    await self._process_request_callback_result(
                        value, callback_recursion + 1
                    )
            elif inspect.iscoroutine(result):
                await self._process_request_callback_result(
                    await result, callback_recursion + 1
                )
            elif isinstance(result, Request):
                await self._process_request(result)
            elif isinstance(result, Item):
                await self.process_item(result)
                self.stats["items_processed"] += 1
        except Exception as e:
            self.logger.exception(e)

    async def _process_request(self, request: Request) -> None:
        seen = await self._dupefilter.url_seen(request.url, request.method)

        if self.max_depth and len(request.history) == self.max_depth:
            self.logger.debug("Max Depth reached: %s", request)
            return

        if not seen:
            self.stats["requests_added"] += 1
            self.logger.debug("Queue Add: %s", request)
            self.request_queue.put_nowait(request)

    def follow(
        self, url: Union[str, URL], callback=None, response: Response = None, **kwargs
    ) -> Request:
        if isinstance(url, str):
            url = URL(url)

        history = []
        if response:
            if not url.is_absolute():
                url = response.url.origin().join(url)
            history = copy.deepcopy(response.history)

        request = Request(
            url=url,
            request_session=self.session,
            history=history,
            callback=callback,
            xml_parser=self.parse_xml,
            max_size=self.max_request_size,
            timeout=self.request_timeout,
            **kwargs,
        )

        return request

    @abstractmethod
    async def process_item(self, item: Item) -> None:
        self.items.add(item)

    @abstractmethod
    async def parse_xml(self, response_text: str) -> Any:
        raise NotImplementedError("Not Implemented")

    @abstractmethod
    async def parse(self, request: Request, response: Response) -> AsyncGeneratorType:
        raise NotImplementedError("Not Implemented")

    async def _work(self):
        while True:
            request = await self.request_queue.get()

            try:
                await self._handle_request(request)
            except asyncio.CancelledError:
                self.logger.debug("Cancelled Request: %s", request)
            finally:
                self.request_queue.task_done()

    async def _run_callback(self, callback, *args, **kwargs):
        if not callback:
            return
        if inspect.iscoroutinefunction(callback):
            return await callback(*args, **kwargs)
        elif inspect.isfunction(callback):
            return callback(*args, **kwargs)
        else:
            self.logger.warning("Callback %s must be a coroutine or function", callback)

    def create_start_urls(self, url: Union[str, URL]):
        if isinstance(url, str):
            url = URL(url)

        if url.scheme not in ["http", "https"]:
            url = url.with_scheme("http")

        self.start_urls = [url]

    async def crawl(self, url: Union[URL, str] = ""):
        if url:
            self.create_start_urls(url)

        if not self.start_urls:
            raise ValueError("crawler.start_urls are required")

        start = time.perf_counter()
        self.request_queue = asyncio.Queue()
        self.session = aiohttp.ClientSession(timeout=self.total_timeout)

        for url in self.start_urls:
            await self._process_request(self.follow(coerce_url(url), self.parse))

        self.workers = [
            asyncio.create_task(self._work()) for _ in range(self.concurrency)
        ]

        # When all work is done, exit.
        try:
            async with self.session:
                await asyncio.wait_for(
                    self.request_queue.join(), timeout=self.total_timeout.total
                )
        except asyncio.TimeoutError:
            self.logger.debug("Timed out after %s seconds", self.total_timeout)
        finally:
            for w in self.workers:
                w.cancel()

        await self._run_callback(self.post_crawl_callback)

        await self.session.close()

        duration = int((time.perf_counter() - start) * 1000)
        self.stats["duration"] = duration
        self.stats["urls_seen"] = len(self._dupefilter.fingerprints)

        self.logger.info(
            "Crawl finished: urls=%s time=%dms",
            (self.stats["requests_failed"] + self.stats["requests_successful"]),
            duration,
        )
        self.logger.debug("Stats: %s", self.stats)
