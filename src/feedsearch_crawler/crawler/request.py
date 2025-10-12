import logging
import uuid
from typing import List, Union, Optional, Dict

from aiohttp import ClientTimeout
from yarl import URL

from feedsearch_crawler.crawler.queueable import Queueable

logger = logging.getLogger(__name__)


class Request(Queueable):
    METHOD = ["GET", "POST", "PUT", "DELETE"]

    def __init__(
        self,
        url: URL,
        params: Optional[Dict] = None,
        data: Optional[Union[dict, bytes]] = None,
        json_data: Optional[Dict] = None,
        encoding: str = "",
        method: str = "GET",
        headers: Optional[Dict] = None,
        timeout: Union[float, ClientTimeout] = 5.0,
        history: Optional[List[URL]] = None,
        callback=None,
        success_callback=None,
        xml_parser=None,
        failure_callback=None,
        max_content_length: int = 1024 * 1024 * 10,
        delay: float = 0,
        retries: int = 3,
        cb_kwargs: Optional[Dict] = None,
        **kwargs,
    ):
        """
        A pending HTTP request to a URL. Contains request details but does not handle HTTP directly.

        :param params: Mapping of query string parameters
        :param data: Dictionary, bytes, or file-like object to send in the body of the request
        :param json_data: Json dict to send as body. Not compatible with data
        :param url: Request URL
        :param encoding: Default Response encoding
        :param method: HTTP method
        :param headers: HTTP headers for the request
        :param timeout: Seconds before Request times out
        :param history: Response history, list of previous URLs
        :param callback: Callback function to run after request is successful
        :param xml_parser: Function to parse Response XML
        :param failure_callback: Callback function to run if request is unsuccessful
        :param max_content_length: Maximum allowed size in bytes of Response content
        :param delay: Time in seconds to delay Request
        :param retries: Number of times to retry a failed Request
        :param cb_kwargs: Optional Dictionary of keyword arguments to be passed to the callback function.
        :param kwargs: Optional keyword arguments
        """
        # Initialize Queueable with self as the item and default priority
        super().__init__(item=self, priority=100)
        self.url = url
        self.method = method.upper()
        if self.method not in self.METHOD:
            raise ValueError(f"{self.method} is not supported")
        # Remove request_session as Request should not handle HTTP directly
        self.headers = headers
        self.timeout = timeout  # Keep timeout as provided (float or ClientTimeout)
        self.history = history or []
        self.encoding = encoding
        # Support both 'callback' and 'success_callback' for backwards compatibility
        self._callback = success_callback or callback
        self._failure_callback = failure_callback
        self.id = uuid.uuid4()
        self.xml_parser = xml_parser
        self.max_content_length = max_content_length
        self.json_data = json_data
        self.data = data
        self.params = params
        self.has_run: bool = False
        self.delay = delay
        self.cb_kwargs = cb_kwargs or {}

        self.should_retry: bool = False
        self._max_retries = retries
        # Number of times this request has been retried.
        self._num_retries: int = 0

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @property
    def callback(self):
        """Get the success callback function."""
        return self._callback

    @property
    def success_callback(self):
        """Get the success callback function."""
        return self._callback

    @property
    def failure_callback(self):
        """Get the failure callback function."""
        return self._failure_callback

    @property
    def retries(self) -> int:
        """Get the maximum number of retries for this request."""
        return self._max_retries

    @retries.setter
    def retries(self, value: int) -> None:
        """Set the maximum number of retries for this request."""
        self._max_retries = value

    def set_retry(self) -> None:
        """
        Set the Request to retry.
        """
        if self._num_retries < self._max_retries:
            self.should_retry = True
            self._num_retries += 1
            self.delay = self._num_retries * 1

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self.url)})"
