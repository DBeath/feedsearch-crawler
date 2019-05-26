import asyncio
import time
import traceback
from typing import Any, AsyncGenerator
from typing import List

import aiohttp
from bs4 import BeautifulSoup
from yarl import URL

urls = [
    'http://arstechnica.com',
    'http://davidbeath.com',
    'http://xkcd.com',
    'http://jsonfeed.org',
    'en.wikipedia.com',
    'scientificamerican.org',
    'newyorktimes.com'
]


def coerce_url(url: str, https: bool = False) -> str:
    """
    Coerce URL to valid format

    :param url: URL
    :param https: Force https if no scheme in url
    :return: str
    """
    url.strip()
    if url.startswith("feed://"):
        return f"http://{url[7:]}"
    for proto in ["http://", "https://"]:
        if url.startswith(proto):
            return url
    if https:
        return f"https://{url}"
    else:
        return f"http://{url}"


class Crawler:
    def __init__(self, start_urls: List = None, max_tasks: int = 10):
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

    async def fetch(self, url):
        try:
            start = time.perf_counter()

            response = await self.session.get(url, headers=self.headers)

            dur = int((time.perf_counter() - start) * 1000)
            print(f"Fetched: {response.url} in {dur}ms")
            self.requests += 1

            links: AsyncGenerator[str, Any] = self.parse(response)

            async for link in links:
                async with self.seen_lock:
                    if link not in self.seen_urls:
                        self.q.put_nowait(link)
                        self.seen_urls.update(link)

        except asyncio.CancelledError:
            print(f"Cancelled URL: {url}")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Exception at URL: {url}, {e}")
            print(tb)
        finally:
            return

    async def parse(self, response):
        url = response.url
        text = await response.text()
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
                self.items.add(str(response.url))
                return
        else:
            print(f"No content type at URL: {url}")

        if bool(data.count("<rss") + data.count("<rdf") + data.count("<feed")):
            self.items.add(str(response.url))
            return

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
                url = url.join(URL(href))
                # links.add(str(url))
                yield str(url)
        # return links

    async def work(self):
        while True:
            url = await self.q.get()

            # Download page and add new links to self.q.
            try:
                await asyncio.shield(self.fetch(url))
            except asyncio.CancelledError:
                print(f"Cancelled URL: {url}")
            finally:
                self.q.task_done()

    async def crawl(self):
        start = time.perf_counter()
        self.q = asyncio.Queue()
        self.session = aiohttp.ClientSession()
        self.seen_lock = asyncio.Lock()

        for url in self.start_urls:
            await self.q.put(coerce_url(url))

        workers = [asyncio.create_task(self.work())
                   for _ in range(self.max_tasks)]

        # When all work is done, exit.
        try:
            await asyncio.wait_for(self.q.join(), timeout=10)
        except asyncio.TimeoutError:
            print("Timeout!")
        finally:
            for w in workers:
                w.cancel()

        await self.session.close()
        print(f"Found items: {self.items}")
        print(f"Requests made: {self.requests}")

        dur = int((time.perf_counter() - start) * 1000)
        print(f"Crawled {self.requests} URLs in {dur}ms")


if __name__ == "__main__":
    crawler = Crawler(start_urls=urls, max_tasks=30)
    asyncio.run(crawler.crawl())