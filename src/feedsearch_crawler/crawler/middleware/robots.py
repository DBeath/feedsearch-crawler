import logging
from typing import Dict, List, Optional
from urllib.robotparser import RobotFileParser

from feedsearch_crawler.crawler.middleware.base import BaseDownloaderMiddleware
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
from feedsearch_crawler.exceptions import RobotsBlockedError

logger = logging.getLogger(__name__)


class RobotsMiddleware(BaseDownloaderMiddleware):
    """Blocks requests disallowed by robots.txt.

    The robots.txt content itself is fetched asynchronously by the crawler
    (queued at highest priority at crawl start) and registered here via
    ``register_robots_txt``. This middleware never performs any I/O of its
    own: until the robots.txt for a host has been registered, requests are
    allowed (permissive), and the crawler exempts the robots.txt request
    itself from checking.
    """

    def __init__(self, user_agent: str = "Feedsearch-Crawler") -> None:
        self.user_agent = user_agent
        self.cache: Dict[str, Optional[RobotFileParser]] = {}
        self.sitemap_urls: Dict[str, List[str]] = {}  # host -> list of sitemap URLs

    @staticmethod
    def _cache_key(request_url) -> str:
        """Cache key for a request's robots.txt (scheme + host + port)."""
        return str(request_url.with_path("/robots.txt"))

    def register_robots_txt(self, robots_url, text: Optional[str]) -> None:
        """Register fetched robots.txt content for a host.

        :param robots_url: The robots.txt URL that was fetched.
        :param text: robots.txt content, or None if unavailable.
        """
        key = str(robots_url)
        if not text:
            # Cache None to indicate robots.txt is unavailable
            self.cache[key] = None
            return

        try:
            rp = RobotFileParser()
            rp.set_url(key)
            rp.parse(text.splitlines())
            self.cache[key] = rp
            self._extract_sitemaps(key, rp)
        except Exception as e:
            logger.debug("Failed to parse robots.txt from %s: %s", key, e)
            self.cache[key] = None

    async def pre_request(self, request: Request) -> None:
        """Check if the request is allowed by robots.txt before it is sent."""
        if not request.url.host:
            return  # Allow requests without host

        # The robots.txt request itself must never be blocked.
        if request.url.path == "/robots.txt":
            return

        rp = self.cache.get(self._cache_key(request.url))
        # Unknown or unavailable robots.txt allows the request (permissive).
        if rp and not rp.can_fetch(self.user_agent, str(request.url)):
            raise RobotsBlockedError(f"Blocked by robots.txt: {request.url}")

    async def process_request(self, request: Request) -> None:
        """Called after the request has been sent."""
        pass

    def _extract_sitemaps(self, robots_url: str, robot_parser: RobotFileParser) -> None:
        """Extract sitemap URLs from robots.txt parser.

        :param robots_url: The robots.txt URL
        :param robot_parser: Parsed RobotFileParser instance
        """
        try:
            # Extract host for storage
            from urllib.parse import urlparse

            parsed = urlparse(robots_url)
            host = f"{parsed.scheme}://{parsed.netloc}"

            # RobotFileParser exposes sitemaps via the site_maps() method
            sitemaps = robot_parser.site_maps()
            if sitemaps:
                self.sitemap_urls[host] = list(sitemaps)
                logger.debug(
                    f"Found {len(sitemaps)} sitemap(s) in {robots_url}: {sitemaps}"
                )
        except Exception as e:
            logger.debug(f"Failed to extract sitemaps from {robots_url}: {e}")

    def get_sitemaps_for_host(self, host: str) -> List[str]:
        """Get list of sitemap URLs for a given host.

        :param host: Host URL (e.g., https://example.com)
        :return: List of sitemap URLs
        """
        return self.sitemap_urls.get(host, [])

    async def process_response(self, response: Response) -> None:
        """Called after processing a response."""
        pass

    async def process_exception(self, request: Request, exception: Exception) -> None:
        """Called when an exception occurs during request processing."""
        pass
