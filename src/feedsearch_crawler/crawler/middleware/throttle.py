from typing import Dict, Any
from feedsearch_crawler.crawler.middleware.base import BaseDownloaderMiddleware
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
import asyncio


class ThrottleMiddleware(BaseDownloaderMiddleware):
    def __init__(self, rate_per_sec: float) -> None:
        self.rate_per_sec = rate_per_sec
        self.last_request: float = 0

    async def pre_request(self, request: Request) -> None:
        """Called before processing a request."""
        pass

    async def process_request(self, request: Request) -> None:
        now = asyncio.get_event_loop().time()
        wait = max(0, (1 / self.rate_per_sec) - (now - self.last_request))
        if wait > 0:
            await asyncio.sleep(wait)
        self.last_request = asyncio.get_event_loop().time()

    async def process_response(self, response: Response) -> None:
        """Called after processing a response."""
        pass

    async def process_exception(self, request: Request, exception: Exception) -> None:
        """Called when an exception occurs during request processing."""
        pass
