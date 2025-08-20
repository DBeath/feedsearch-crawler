from feedsearch_crawler.crawler.middleware.base import BaseDownloaderMiddleware
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response


class ContentTypeMiddleware(BaseDownloaderMiddleware):
    async def pre_request(self, request: Request) -> None:
        """Called before processing a request."""
        pass

    async def process_request(self, request: Request) -> None:
        """Called during request processing."""
        pass

    async def process_response(self, response: Response) -> None:
        ctype = response.headers.get("content-type", "")
        if "application/json" in ctype:
            response.json = await response.json()
        elif "text/html" in ctype:
            response.text = response.data.decode(response.encoding or "utf-8")
        # ...other types...

    async def process_exception(self, request: Request, exception: Exception) -> None:
        """Called when an exception occurs during request processing."""
        pass
