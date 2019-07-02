import asyncio
import copy
import json
import logging
import time
import uuid
from asyncio import Semaphore, IncompleteReadError, LimitOverrunError, CancelledError
from random import random
from typing import List, Tuple, Any, Union, Optional

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from yarl import URL

from feedsearch_crawler.crawler.queueable import Queueable
from feedsearch_crawler.crawler.response import Response


class Request(Queueable):
    METHOD = ["GET", "POST"]

    def __init__(
        self,
        url: URL,
        request_session: ClientSession,
        params: dict = None,
        data: Union[dict, bytes] = None,
        json_data: dict = None,
        encoding: str = None,
        method: str = "GET",
        headers: dict = None,
        timeout: Union[float, ClientTimeout] = 5.0,
        history: List = None,
        callback=None,
        xml_parser=None,
        failure_callback=None,
        max_content_length: int = 1024 * 1024 * 10,
        delay: float = 0,
        retries: int = 3,
        **kwargs,
    ):
        """
        A pending HTTP request to a URL. Wraps an aiohttp ClientSession request.
        https://aiohttp.readthedocs.io/en/stable/client_reference.html

        :param params: Mapping of query string parameters
        :param data: Dictionary, bytes, or file-like object to send in the body of the request
        :param json_data: Json dict to send as body. Not compatible with data
        :param url: Request URL
        :param request_session: aiohttp ClientSession
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
        :param kwargs: Optional keyword arguments
        """
        self.url = url
        self.method = method.upper()
        if self.method not in self.METHOD:
            raise ValueError(f"{self.method} is not supported")
        if not isinstance(request_session, ClientSession):
            raise ValueError(f"request_session must be of type ClientSession")
        self.request_session = request_session
        self.headers = headers
        if not isinstance(timeout, ClientTimeout):
            timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.timeout = timeout
        self.history = history or []
        self.encoding = encoding
        self._callback = callback
        self._failure_callback = failure_callback
        self.id = uuid.uuid4()
        self._xml_parser = xml_parser
        self.max_content_length = max_content_length
        self.json_data = json_data
        self.data = data
        self.params = params
        self.has_run: bool = False
        self.delay = delay

        self.should_retry: bool = False
        self._max_retries = retries
        # Number of times this request has been retried.
        self._num_retries: int = 0
        # Time in Milliseconds for the HTTP Request to complete.
        self.req_latency: int = 0

        for key, value in kwargs:
            if hasattr(self, key):
                setattr(self, key, value)

        self.logger = logging.getLogger("feedsearch_crawler")

    async def fetch_callback(self, semaphore: Semaphore = None) -> Tuple[Any, Response]:
        """
        Fetch HTTP Response and run Callbacks.

        :param semaphore: asyncio Semaphore
        :returns: Tuple of Callback result and Response object
        """
        if semaphore:
            async with semaphore:
                response = await self._fetch()
        else:
            response = await self._fetch()

        callback_result = None

        if response.ok and self._callback:
            callback_result = self._callback(self, response)
        elif not response.ok and self._failure_callback:
            callback_result = self._failure_callback(self, response)

        return callback_result, response

    # noinspection PyProtectedMember
    async def _fetch(self) -> Response:
        """
        Run HTTP Request and fetch HTTP Response.

        :return: Response object
        """
        # Delay the request if self.delay is > 0
        await self.delay_request()

        # Copy the Request history so that it isn't a pointer.
        history = copy.deepcopy(self.history)

        # Make sure that retry is reset.
        self.should_retry = False
        response = None
        start = time.perf_counter()

        try:
            async with self._create_request() as resp:
                history.append(resp.url)

                # Fail the response if the content length header is too large.
                content_length: int = int(resp.headers.get("Content-Length", "0"))
                if content_length > self.max_content_length:
                    return self._failed_response(413)

                # Read the response content, and fail the response if the actual content size is too large.
                content_read, actual_content_length = await self._read_response(resp)
                if not content_read:
                    return self._failed_response(413)

                # Set encoding automatically from response if not specified.
                if not self.encoding:
                    self.encoding = resp.get_encoding()

                # Read response content
                try:
                    # Read response content as text
                    resp_text = await resp.text(encoding=self.encoding)

                    # Attempt to read response content as JSON
                    resp_json = await self._read_json(resp_text)
                # If response content can't be decoded then neither text or JSON can be set.
                except UnicodeDecodeError:
                    resp_text = None
                    resp_json = None

                # Close the asyncio response
                if not resp.closed:
                    resp.close()

                response = Response(
                    url=resp.url,
                    method=resp.method,
                    encoding=self.encoding,
                    status_code=resp.status,
                    history=history,
                    text=resp_text,
                    data=resp._body,
                    json=resp_json,
                    headers=resp.headers,
                    xml_parser=self._parse_xml,
                    cookies=resp.cookies,
                    redirect_history=resp.history,
                    content_length=actual_content_length,
                )

                # Raise exception after the Response object is created, because we only catch TimeoutErrors and
                # asyncio.ClientResponseErrors, and there may be valid data otherwise.
                resp.raise_for_status()

        except asyncio.TimeoutError:
            self.logger.debug("Failed fetch: url=%s reason=timeout", self.url)
            history.append(self.url)
            response = self._failed_response(408, history)
        except aiohttp.ClientResponseError as e:
            self.logger.debug("Failed fetch: url=%s reason=%s", self.url, e.message)
            if not response:
                response = self._failed_response(e.status, history)
        except Exception as e:
            self.logger.debug("Failed fetch: url=%s reason=%s", self.url, e)
            if isinstance(e, CancelledError) and not response:
                response = self._failed_response(499, history)
        finally:
            self.req_latency = int((time.perf_counter() - start) * 1000)
            self.has_run = True
            # Make sure there is a valid Response object.
            if not response:
                response = self._failed_response(500, history)

            # Tell the crawler to retry this Request
            if response.status_code in [429, 503, 408]:
                self.set_retry()

            return response

    def _create_request(self):
        """
        Create an asyncio HTTP Request.

        :return: asyncio HTTP Request
        """
        if self.method.upper() == "GET":
            return self.request_session.get(
                self.url, headers=self.headers, timeout=self.timeout, params=self.params
            )
        elif self.method.upper() == "POST":
            return self.request_session.post(
                self.url,
                headers=self.headers,
                timeout=self.timeout,
                params=self.params,
                data=self.data,
                json=self.json_data,
            )
        else:
            raise ValueError(
                "HTTP method %s is not valid. Must be GET or POST", self.method
            )

    async def _read_response(self, resp) -> Tuple[bool, int]:
        """
        Read HTTP Response content as bytes.

        :param resp: asyncio HTTP Response
        :return: Tuple (read status, content length in bytes)
        """
        body: bytes = b""
        try:
            async for chunk in resp.content.iter_chunked(1024):
                if not chunk:
                    break
                body += chunk
                if len(body) > self.max_content_length:
                    return False, 0
        except (IncompleteReadError, LimitOverrunError) as e:
            self.logger.exception("Failed to read Response content: %s", e)
            return False, 0
        resp._body = body
        return True, len(body)

    @staticmethod
    async def _read_json(resp_text: Union[str, None]) -> Optional[dict]:
        """
        Attempt to read Response content as JSON.

        :param resp_text: HTTP response context as text string
        :return: JSON dict or None
        """

        # If the text hasn't been parsed then we won't be able to parse JSON either.
        if not resp_text:
            return

        stripped = resp_text.strip()  # type: ignore
        if not stripped:
            return None

        try:
            return json.loads(stripped)
        except ValueError:
            return None

    def _failed_response(
        self, status: int, history: List[URL] = None, headers=None
    ) -> Response:
        """
        Create a failed Response object with the provided Status Code.

        :param status: HTTP Status Code
        :param history: Response History as list of URLs
        :param headers: Response Headers
        :return: Failed Response object
        """
        return Response(
            url=self.url,
            method=self.method,
            encoding=self.encoding,
            history=history or [],
            status_code=status,
            headers=headers or {},
        )

    async def _parse_xml(self, response_text: str) -> Any:
        """
        Use provided XML Parsers method to attempt to parse Response content as XML.

        :param response_text: Response content as text string.
        :return: Response content as parsed XML. Type depends on XML parser.
        """
        try:
            return await self._xml_parser(response_text)
        except Exception as e:
            self.logger.error("Error parsing response xml: %s", e)
            return None

    def set_retry(self) -> None:
        """
        Set the Request to retry.
        """
        if self._num_retries < self._max_retries:
            self.should_retry = True
            self._num_retries += 1
            self.delay = self._num_retries * 1

    async def delay_request(self) -> None:
        """
        Delay the request by sleeping.
        """
        if self.delay > 0:
            # Sleep for the delay plus up to one extra second of random time, to spread out requests.
            await asyncio.sleep(self.delay + random())

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self.url)})"
