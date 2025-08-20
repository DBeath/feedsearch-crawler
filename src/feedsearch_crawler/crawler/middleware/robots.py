from typing import Dict, Any
from feedsearch_crawler.crawler.middleware.base import BaseDownloaderMiddleware
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
from yarl import URL


class RobotsMiddleware(BaseDownloaderMiddleware):
    def __init__(self, user_agent: str) -> None:
        self.user_agent = user_agent
        self.cache: Dict[str, Any] = {}

    async def pre_request(self, request: Request) -> None:
        """Called before processing a request."""
        pass

    async def process_request(self, request: Request) -> None:
        robots_url = str(URL(request.url).origin().with_path("/robots.txt"))
        if robots_url not in self.cache:
            # Fetch and parse robots.txt (use aiohttp or requests)
            # Store parsed rules in self.cache[robots_url]
            pass
        rules = self.cache[robots_url]
        if not rules.can_fetch(self.user_agent, str(request.url)):
            raise Exception(f"Blocked by robots.txt: {request.url}")

    async def process_response(self, response: Response) -> None:
        """Called after processing a response."""
        pass

    async def process_exception(self, request: Request, exception: Exception) -> None:
        """Called when an exception occurs during request processing."""
        pass
