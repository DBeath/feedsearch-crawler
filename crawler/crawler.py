import asyncio
import logging
import time
from types import AsyncGeneratorType
from typing import List
from typing import Union
import copy
import inspect

import aiohttp
from yarl import URL

from crawler.item import Item
from crawler.lib import coerce_url
from crawler.request import Request
from crawler.response import Response
from crawler.duplicatefilter import DuplicateFilter

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    uvloop = None
    pass


class Crawler:
    dupefilter = DuplicateFilter()
    post_crawl_callback = None

    def __init__(self, start_urls: List = None, max_tasks: int = 10, timeout: int = 10):
        self.max_tasks = max_tasks
        self.session = None
        self.request_queue = None
        self.items = set()
        self.requests = 0
        self.start_urls = start_urls
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36"
        )
        self.headers = {"User-Agent": self.user_agent}
        self.logger = logging.getLogger(__name__)
        self.timeout = timeout

    async def _handle_request(self, request: Request):
        try:
            start = time.perf_counter()

            results, response = await request.fetch()

            dur = int((time.perf_counter() - start) * 1000)
            self.logger.debug(
                "Fetched: %s in %dms. Status: %s",
                response.url,
                dur,
                response.status_code,
            )

            self.requests += 1

            if results and inspect.isasyncgen(results):
                await self._process_parsed_response(results)

        except asyncio.CancelledError:
            self.logger.debug("Cancelled URL: %s", request.url)
        except Exception as e:
            self.logger.exception("Exception at URL: %s, %s", request.url, e)
        finally:
            return

    async def _process_parsed_response(self, results: AsyncGeneratorType):
        try:
            async for result in results:
                if isinstance(result, Request):
                    await self._process_request(result)
                elif isinstance(result, Item):
                    await self.process_item(result)

        except Exception as e:
            self.logger.error(e)

    async def process_item(self, item: Item) -> None:
        self.items.add(item)

    async def _process_request(self, request: Request) -> None:
        seen = await self.dupefilter.request_seen(request)
        if not seen:
            self.request_queue.put_nowait(request)

    def follow(
        self, url: Union[str, URL], callback=None, response: Response = None, **kwargs
    ) -> Request:
        if isinstance(url, str):
            url = URL(url)

        history = []
        if response:
            url = response.url.join(url)
            history = copy.deepcopy(response.history)

        request = Request(
            url=url,
            request_session=self.session,
            history=history,
            callback=callback,
            xml_parser=self.parse_xml,
            **kwargs,
        )

        return request

    async def parse_xml(self, response_text: str):
        raise NotImplementedError("Not Implemented")

    async def parse(self, request: Request, response: Response):
        raise NotImplementedError("Not Implemented")

    async def _work(self):
        while True:
            request = await self.request_queue.get()

            # Download page and add new links to self.q.
            try:
                await asyncio.shield(self._handle_request(request))
            except asyncio.CancelledError:
                self.logger.debug("Cancelled Request: %s", request)
            finally:
                self.request_queue.task_done()

    async def post_crawl(self, *args, **kwargs):
        pass

    async def run_callback(self, callback, *args, **kwargs):
        if not callback:
            return
        if inspect.iscoroutinefunction(callback):
            return await callback(*args, **kwargs)
        elif inspect.isfunction(callback):
            return callback(*args, **kwargs)
        else:
            self.logger.warning("Callback %s must be a coroutine or function", callback)

    async def crawl(self):
        start = time.perf_counter()
        self.request_queue = asyncio.Queue()
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        self.seen_lock = asyncio.Lock()

        for url in self.start_urls:
            await self.request_queue.put(self.follow(coerce_url(url), self.parse))

        workers = [asyncio.create_task(self._work()) for _ in range(self.max_tasks)]

        # When all work is done, exit.
        try:
            async with self.session:
                await asyncio.wait_for(self.request_queue.join(), timeout=self.timeout)
                # await self.request_queue.join()
        except asyncio.TimeoutError:
            self.logger.debug("Timed out after %s seconds", self.timeout)
        finally:
            for w in workers:
                w.cancel()

        await self.run_callback(self.post_crawl_callback)

        await self.session.close()

        duration = int((time.perf_counter() - start) * 1000)
        self.logger.info("Crawled %s URLs in %dms", self.requests, duration)
