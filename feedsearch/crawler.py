import asyncio
import time
import traceback
from types import AsyncGeneratorType
from typing import Any, AsyncGenerator, Union
from typing import List

import aiohttp
from bs4 import BeautifulSoup
from yarl import URL
from .lib import coerce_url
import logging
from .response import Response
from .request import Request
from .item import Item



class Crawler:
    def __init__(self, start_urls: List = None, max_tasks: int = 10, timeout: int=10):
        self.max_tasks = max_tasks
        self.session = None
        self.seen_urls = set()
        self.q = None
        self.seen_lock = None
        self.items = set()
        self.requests = 0
        self.start_urls = start_urls
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36"
        self.headers = {"User-Agent": self.user_agent}
        self.logger = logging.getLogger("feedsearch")
        self.timeout = timeout

    async def handle_request(self, request: Request):
        try:
            start = time.perf_counter()

            results, response = await request.fetch()

            dur = int((time.perf_counter() - start) * 1000)
            print(f"Fetched: {response.url} in {dur}ms. Status: {response.status_code}")

            self.requests += 1

            await self.process_parsed_response(results)

        except asyncio.CancelledError:
            print(f"Cancelled URL: {request.url}")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Exception at URL: {request.url}, {e}")
            print(tb)
        finally:
            return

    async def process_parsed_response(self, results: AsyncGeneratorType):
        try:
            async for result in results:
                if isinstance(result, Request):
                    await self.process_request(result)
                elif isinstance(result, Item):
                    await self.process_item(result)

        except Exception as e:
            self.logger.error(e)


    async def process_item(self, item: Item) -> None:
        print(item)
        self.items.add(item)


    async def process_request(self, request: Request) -> None:
        async with self.seen_lock:
            request_url = str(request.url)
            if request_url not in self.seen_urls:
                print(request_url)
                self.q.put_nowait(request)
                self.seen_urls.update(request_url)

    def follow(self, url: Union[str, URL], callback=None, response: Response=None, **kwargs) -> Request:
        if isinstance(url, str):
            url = URL(url)

        history = []
        if response:
            url = response.url.join(url)
            history = response.history

        request = Request(
            url=url,
            request_session=self.session,
            history=history,
            callback=callback,
            **kwargs
        )
        return request

    async def parse(self, request: Request, response: Response):
        url = response.url
        text = response.data
        if not text:
            print(f"No text at {url}")
            return

        soup = BeautifulSoup(text, features="html.parser")
        content_type = response.headers.get("content-type")

        data = text.lower()

        if not data:
            return

        if content_type:
            if "json" in content_type and data.count("jsonfeed.org"):
                item = Item()
                item.url = str(response.url)
                item.content_type = content_type
                yield item
        else:
            print(f"No content type at URL: {url}")

        if bool(data.count("<rss") + data.count("<rdf") + data.count("<feed")):
            item = Item()
            item.url = str(response.url)
            item.content_type = "application/rss+xml"
            yield item

        # links = set()
        link_tags = soup.find_all("link")
        if not link_tags:
            return
        for link in link_tags:
            if link.get("type") in [
                "application/rss+xml",
                "text/xml",
                "application/atom+xml",
                "application/x.atom+xml",
                "application/x-atom+xml",
                "application/json",
            ]:
                href = link.get("href", "")
                #url = url.join(URL(href))
                # links.add(str(url))
                yield self.follow(href, self.parse, response)
        # return links

    async def work(self):
        while True:
            request = await self.q.get()

            # Download page and add new links to self.q.
            try:
                await asyncio.shield(self.handle_request(request))
            except asyncio.CancelledError:
                print(f"Cancelled Request: {request}")
            finally:
                self.q.task_done()

    async def crawl(self):
        start = time.perf_counter()
        self.q = asyncio.Queue()
        self.session = aiohttp.ClientSession()
        self.seen_lock = asyncio.Lock()

        for url in self.start_urls:
            await self.q.put(self.follow(coerce_url(url), self.parse))

        workers = [asyncio.create_task(self.work())
                   for _ in range(self.max_tasks)]

        # When all work is done, exit.
        try:
            await asyncio.wait_for(self.q.join(), timeout=self.timeout)
        except asyncio.TimeoutError:
            self.logger.debug("Timed out after %s seconds", self.timeout)
        finally:
            for w in workers:
                w.cancel()

        await self.session.close()

        duration = int((time.perf_counter() - start) * 1000)
        self.logger.info("Crawled %s URLs in %dms", self.requests, duration)

        print([item.url for item in self.items])
