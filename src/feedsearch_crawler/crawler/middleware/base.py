from abc import ABC, abstractmethod

from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response


class BaseDownloaderMiddleware(ABC):
    """Base class for all downloader middleware implementations.

    This abstract base class defines the interface that all downloader middleware
    classes must implement. Middleware classes can hook into different stages of
    the request/response cycle.
    """

    @abstractmethod
    async def pre_request(self, request: Request) -> None:
        """Called before a request is made.

        Args:
            request: The request object that will be sent.
        """
        pass

    @abstractmethod
    async def process_request(self, request: Request) -> None:
        """Called when processing a request.

        Args:
            request: The request object being processed.
        """
        pass

    @abstractmethod
    async def process_response(self, response: Response) -> None:
        """Called when processing a response.

        Args:
            response: The response object received.
        """
        pass

    @abstractmethod
    async def process_exception(self, request: Request, exception: Exception) -> None:
        """Called when an exception occurs during request processing.

        Args:
            request: The request object that caused the exception.
            exception: The exception that occurred.
        """
        pass
