from typing import Dict
from feedsearch_crawler.crawler.middleware.base import BaseDownloaderMiddleware
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
import asyncio


class ThrottleMiddleware(BaseDownloaderMiddleware):
    def __init__(self, rate_per_sec: float) -> None:
        self.rate_per_sec = rate_per_sec
        self.host_timers: Dict[str, float] = {}  # Track per-host timing

    async def pre_request(self, request: Request) -> None:
        """Called before processing a request."""
        pass

    async def process_request(self, request: Request) -> None:
        host = request.url.host or "unknown"
        now = asyncio.get_event_loop().time()
        last_request = self.host_timers.get(host, 0)
        wait = max(0, (1 / self.rate_per_sec) - (now - last_request))
        if wait > 0:
            await asyncio.sleep(wait)
        self.host_timers[host] = asyncio.get_event_loop().time()

    async def process_response(self, response: Response) -> None:
        """Called after processing a response."""
        pass

    async def process_exception(self, request: Request, exception: Exception) -> None:
        """Called when an exception occurs during request processing."""
        pass
