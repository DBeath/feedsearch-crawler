import logging
from typing import Dict, Optional
from urllib.robotparser import RobotFileParser
from feedsearch_crawler.crawler.middleware.base import BaseDownloaderMiddleware
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response

logger = logging.getLogger(__name__)


class RobotsMiddleware(BaseDownloaderMiddleware):
    def __init__(self, user_agent: str = "Feedsearch-Crawler") -> None:
        self.user_agent = user_agent
        self.cache: Dict[str, Optional[RobotFileParser]] = {}

    async def pre_request(self, request: Request) -> None:
        """Called before processing a request."""
        pass

    async def process_request(self, request: Request) -> None:
        """Check if request is allowed by robots.txt."""
        try:
            host = request.url.host
            if not host:
                return  # Allow requests without host

            robots_url = f"{request.url.scheme}://{host}/robots.txt"

            if robots_url not in self.cache:
                await self._load_robots_txt(robots_url)

            rp = self.cache.get(robots_url)
            if rp and not rp.can_fetch(self.user_agent, str(request.url)):
                raise Exception(f"Blocked by robots.txt: {request.url}")

        except Exception as e:
            # Only catch and allow on robots.txt loading errors, not blocking errors
            if "Blocked by robots.txt" in str(e):
                raise  # Re-raise blocking exceptions
            logger.debug(f"Robots.txt check failed for {request.url}: {e}")
            # Allow request on robots.txt loading errors (be permissive)

    async def _load_robots_txt(self, robots_url: str) -> None:
        """Load and parse robots.txt for a host."""
        try:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            # In a real implementation, this would be async
            # For now, we'll use the blocking read() method
            rp.read()
            self.cache[robots_url] = rp
        except Exception as e:
            logger.debug(f"Failed to load robots.txt from {robots_url}: {e}")
            # Cache None to indicate robots.txt is unavailable
            self.cache[robots_url] = None

    async def process_response(self, response: Response) -> None:
        """Called after processing a response."""
        pass

    async def process_exception(self, request: Request, exception: Exception) -> None:
        """Called when an exception occurs during request processing."""
        pass
