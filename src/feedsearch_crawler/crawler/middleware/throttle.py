from typing import Dict
from feedsearch_crawler.crawler.middleware.base import BaseDownloaderMiddleware
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
import asyncio


class ThrottleMiddleware(BaseDownloaderMiddleware):
    """Limits the request rate per host.

    The wait happens in pre_request, i.e. before the HTTP request is sent.
    A rate_per_sec of 0 (or less) disables throttling.
    """

    def __init__(self, rate_per_sec: float) -> None:
        self.rate_per_sec = rate_per_sec
        self.host_timers: Dict[str, float] = {}  # Track per-host timing

    async def pre_request(self, request: Request) -> None:
        """Delay the request so the per-host rate limit is respected."""
        if self.rate_per_sec <= 0:
            return
        host = request.url.host or "unknown"
        now = asyncio.get_event_loop().time()
        last_request = self.host_timers.get(host, 0)
        wait = max(0, (1 / self.rate_per_sec) - (now - last_request))
        # Reserve the slot before sleeping so concurrent requests to the
        # same host queue up behind each other instead of racing.
        self.host_timers[host] = now + wait
        if wait > 0:
            await asyncio.sleep(wait)

    async def process_request(self, request: Request) -> None:
        """Called after the request has been sent."""
        pass

    async def process_response(self, response: Response) -> None:
        """Called after processing a response."""
        pass

    async def process_exception(self, request: Request, exception: Exception) -> None:
        """Called when an exception occurs during request processing."""
        pass
