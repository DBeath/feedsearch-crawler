from feedsearch_crawler.crawler.middleware.base import BaseDownloaderMiddleware
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
import asyncio


class MonitoringMiddleware(BaseDownloaderMiddleware):
    def __init__(self):
        self.stats = {}

    async def pre_request(self, request: Request):
        """Called before processing a request."""
        pass

    async def process_request(self, request: Request):
        request._start_time = asyncio.get_event_loop().time()

    async def process_response(self, response: Response) -> None:
        elapsed = asyncio.get_event_loop().time() - response.request._start_time
        self.stats.setdefault("latencies", []).append(elapsed)
        self.stats.setdefault("status_codes", {}).setdefault(response.status_code, 0)
        self.stats["status_codes"][response.status_code] += 1

    async def process_exception(self, request: Request, exception: Exception) -> None:
        """Called when an exception occurs during request processing."""
        pass
