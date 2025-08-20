from feedsearch_crawler.crawler.middleware.base import BaseDownloaderMiddleware
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
from yarl import URL

class CookieMiddleware(BaseDownloaderMiddleware):
    def __init__(self):
        self.cookie_jar = {}

    async def pre_request(self, request: Request):
        """Called before processing a request."""
        pass

    async def process_request(self, request: Request):
        # Attach cookies for the domain
        domain = URL(request.url).host
        request.cookies = self.cookie_jar.get(domain, {})

    async def process_response(self, response: Response):
        # Store cookies from response
        domain = URL(response.url).host
        self.cookie_jar[domain] = response.cookies

    async def process_exception(self, request: Request, exception: Exception):
        """Called when an exception occurs during request processing."""
        pass