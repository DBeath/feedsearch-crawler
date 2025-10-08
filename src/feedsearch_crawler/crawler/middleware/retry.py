from typing import List
from feedsearch_crawler.crawler.middleware.base import BaseDownloaderMiddleware
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
from feedsearch_crawler.crawler.exceptions import RetryRequestException


class RetryMiddleware(BaseDownloaderMiddleware):
    def __init__(
        self,
        max_retries: int = 3,
        retry_statuses: List[int] = [429, 500, 502, 503, 504],
    ) -> None:
        self.max_retries = max_retries
        self.retry_statuses = retry_statuses

    async def pre_request(self, request: Request) -> None:
        """Called before processing a request."""
        pass

    async def process_request(self, request: Request) -> None:
        """Called during request processing."""
        pass

    async def process_response(self, response: Response) -> None:
        if (
            response.status_code in self.retry_statuses
            and response.request.retries < self.max_retries
        ):
            response.request.retries += 1
            raise RetryRequestException(response.request)

    async def process_exception(self, request: Request, exception: Exception) -> None:
        """Called when an exception occurs during request processing."""
        pass
