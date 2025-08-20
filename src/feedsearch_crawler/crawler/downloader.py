import asyncio
import copy
import json
import logging
import uuid
from asyncio import Semaphore, IncompleteReadError, LimitOverrunError, CancelledError
from random import random
from typing import List, Tuple, Any, Union, Optional, Dict

import aiohttp
import time
from aiohttp import ClientSession, ClientTimeout, hdrs, ClientResponse, ClientRequest
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL
from .lib import ContentLengthError, ContentReadError

from feedsearch_crawler.crawler.queueable import Queueable
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
from feedsearch_crawler.crawler.middleware import BaseDownloaderMiddleware

logger = logging.getLogger(__name__)


class Downloader:
    def __init__(
        self,
        request_session: ClientSession,
        middlewares: Optional[List[BaseDownloaderMiddleware]] = None,
    ) -> None:
        self.request_session: ClientSession = request_session
        self.middlewares: List[BaseDownloaderMiddleware] = middlewares or []

    async def fetch(self, request: Request) -> Response:
        """
        Run HTTP Request and fetch HTTP Response.

        :return: Response object
        """
        # Delay the request if self.delay is > 0
        await self._delay_request()

        # Copy the Request history so that it isn't a pointer.
        history: List[URL] = copy.deepcopy(request.history)

        # Make sure that retry is reset.
        self.should_retry = False
        response = None
        start = time.perf_counter()

        response_status_code: int = 0

        # Pass the request to the middleware before the request is sent
        for middleware in self.middlewares:
            await middleware.pre_request(request)

        try:
            async with self._create_request() as resp:
                resp_received = time.perf_counter()
                self.req_latency = int((resp_received - start) * 1000)
                history.append(resp.url)

                # Pass the request to the middleware
                for middleware in self.middlewares:
                    await middleware.process_request(request)

                # Fail the response if the content length header is too large.
                content_length: int = int(resp.headers.get(hdrs.CONTENT_LENGTH, "0"))
                if content_length > request.max_content_length:
                    raise ContentLengthError(request.max_content_length)

                # Read the response content, and fail the response if the actual content size is too large.
                actual_content_length = await self._read_response(
                    resp, request.max_content_length
                )

                if content_length and content_length != actual_content_length:
                    logger.debug(
                        "Header Content-Length %d different from actual content-length %d: %s",
                        content_length,
                        actual_content_length,
                        self,
                    )

                # Set encoding automatically from response if not specified.
                if not self.encoding:
                    self.encoding = resp.get_encoding()

                # Read response content
                try:
                    # Read response content as text
                    resp_text: str = await resp.text(encoding=self.encoding)

                    # Attempt to read response content as JSON
                    resp_json: dict = await self._read_json(resp_text)
                # If response content can't be decoded then neither text or JSON can be set.
                except UnicodeDecodeError:
                    resp_text: str = ""
                    resp_json: dict = {}

                # Close the asyncio response
                if not resp.closed:
                    resp.close()

                self.content_read = int((time.perf_counter() - resp_received) * 1000)

                response = Response(
                    url=resp.url,
                    method=resp.method,
                    encoding=self.encoding,
                    headers=resp.headers,
                    status_code=resp.status,
                    history=history,
                    text=resp_text,
                    data=resp._body,
                    json=resp_json,
                    xml_parser=self._xml_parser,
                    cookies=resp.cookies,
                    redirect_history=resp.history,
                    content_length=actual_content_length,
                    meta=copy.copy(self.cb_kwargs),
                )

                # Raise exception after the Response object is created, because we only catch TimeoutErrors and
                # asyncio.ClientResponseErrors, and there may be valid data otherwise.
                resp.raise_for_status()

        except asyncio.TimeoutError:
            logger.debug("Failed fetch: url=%s reason=timeout", request.url)
            history.append(request.url)
            response_status_code = 408
        except ContentLengthError as e:
            logger.debug(
                "Content Length of Response body greater than max %d: %s",
                e.max_content_length,
                request,
            )
            response_status_code = 413
        except ContentReadError as e:
            response_status_code = 413
        except aiohttp.ClientResponseError as e:
            logger.debug("Failed fetch: url=%s reason=%s", request.url, e.message)
            response_status_code = e.status
        except Exception as e:
            logger.debug("Failed fetch: url=%s reason=%s", request.url, e)
            if isinstance(e, CancelledError):
                response_status_code = 499
        finally:
            self.has_run = True

            if not response_status_code:
                response_status_code = 500

            # Make sure there is a valid Response object.
            if not response:
                response = Response(
                    url=request.url,
                    method=request.method,
                    encoding=self.encoding,
                    headers={},
                    history=history or [],
                    status_code=response_status_code,
                )

            # Tell the crawler to retry this Request
            if response_status_code in [429, 503, 408]:
                request.set_retry()

            return response

    def _create_request(self) -> ClientRequest:
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

    def _failed_response(
        self, status: int, history: List[URL], headers: Optional[Dict[str, str]] = None
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
            headers=headers or {},
            history=history or [],
            status_code=status,
        )

    async def _read_response(
        self, resp: ClientResponse, max_content_length: int
    ) -> int:
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
                if len(body) > max_content_length:
                    raise ContentLengthError(max_content_length)
        except (IncompleteReadError, LimitOverrunError) as e:
            logger.exception("Failed to read Response content: %s: %s", self, e)
            raise ContentReadError

        resp._body = body  # type: ignore
        return len(body)

    async def _delay_request(self, delay: int = 0) -> None:
        """
        Delay the request by sleeping.
        """
        if delay > 0:
            # Sleep for the delay plus up to one extra second of random time, to spread out requests.
            await asyncio.sleep(delay + random())
