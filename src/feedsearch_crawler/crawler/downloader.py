import asyncio
import copy
import json
import logging
from asyncio import IncompleteReadError, LimitOverrunError, CancelledError
from random import random
from typing import List, Tuple, Optional, Dict

import aiohttp
from aiohttp import ClientSession, ClientTimeout, hdrs, ClientResponse, ClientRequest
from yarl import URL
from .lib import ContentLengthError, ContentReadError

from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
from feedsearch_crawler.crawler.middleware import BaseDownloaderMiddleware
from feedsearch_crawler.exceptions import ErrorType

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
        # Delay the request if request.delay is > 0
        await self._delay_request(request.delay)

        # Copy the Request history so that it isn't a pointer.
        history: List[URL] = copy.deepcopy(request.history)

        response = None
        response_status_code: int = 0

        # Pass the request to the middleware before the request is sent
        for middleware in self.middlewares:
            await middleware.pre_request(request)

        error_type_hint: Optional[ErrorType] = None
        try:
            async with self._create_request(request) as resp:
                history.append(resp.url)

                # Pass the request to the middleware
                for middleware in self.middlewares:
                    await middleware.process_request(request)

                # Check content type early to avoid downloading irrelevant content
                content_type = resp.headers.get(hdrs.CONTENT_TYPE, "").lower()
                if not any(
                    ct in content_type
                    for ct in ["xml", "rss", "atom", "json", "html", "text"]
                ):
                    # Skip downloading body for irrelevant content types
                    resp.close()
                    return self._failed_response(request, 415, history)

                # Fail the response if the content length header is too large.
                content_length: int = int(resp.headers.get(hdrs.CONTENT_LENGTH, "0"))
                if content_length > request.max_content_length:
                    raise ContentLengthError(request.max_content_length)

                # Read the response content, and fail the response if the actual content size is too large.
                resp_data, actual_content_length = await self._read_response(
                    resp, request.max_content_length
                )

                if content_length and content_length != actual_content_length:
                    logger.debug(
                        "Header Content-Length %d different from actual content-length %d: %s",
                        content_length,
                        actual_content_length,
                        request,
                    )

                # Set encoding automatically from response if not specified.
                encoding = request.encoding or resp.get_encoding()

                # Read response content
                try:
                    # Read response content as text, using the data we already read
                    if resp_data:
                        resp_text = resp_data.decode(encoding)
                    else:
                        resp_text = ""

                    # Attempt to read response content as JSON
                    resp_json: dict = await self._read_json(resp_text)
                # If response content can't be decoded then neither text or JSON can be set.
                except UnicodeDecodeError:
                    resp_text: str = ""
                    resp_json: dict = {}

                # Close the asyncio response
                if not resp.closed:
                    resp.close()

                response = Response(
                    url=resp.url,
                    method=resp.method,
                    encoding=encoding,
                    headers=resp.headers,
                    status_code=resp.status,
                    history=history,
                    text=resp_text,
                    data=resp_data,
                    json=resp_json,
                    xml_parser=request.xml_parser,
                    cookies=resp.cookies,
                    redirect_history=resp.history,
                    content_length=actual_content_length,
                    meta=copy.copy(request.cb_kwargs),
                    request=request,
                )

                # Pass the response to the middleware
                for middleware in self.middlewares:
                    await middleware.process_response(response)

                # Raise exception after the Response object is created, because we only catch TimeoutErrors and
                # asyncio.ClientResponseErrors, and there may be valid data otherwise.
                resp.raise_for_status()

        except asyncio.TimeoutError:
            logger.debug("Failed fetch: url=%s reason=timeout", request.url)
            history.append(request.url)
            response_status_code = 408
            error_type_hint = ErrorType.TIMEOUT
        except ContentLengthError as e:
            logger.debug(
                "Content Length of Response body greater than max %d: %s",
                e.max_content_length,
                request,
            )
            response_status_code = 413
        except ContentReadError:
            response_status_code = 413
        except aiohttp.ClientConnectorDNSError:
            logger.debug("Failed fetch: url=%s reason=DNS failure", request.url)
            response_status_code = 500
            error_type_hint = ErrorType.DNS_FAILURE
        except aiohttp.ClientConnectorSSLError:
            logger.debug("Failed fetch: url=%s reason=SSL error", request.url)
            response_status_code = 500
            error_type_hint = ErrorType.SSL_ERROR
        except aiohttp.ClientConnectorError:
            logger.debug("Failed fetch: url=%s reason=connection error", request.url)
            response_status_code = 500
            error_type_hint = ErrorType.CONNECTION_ERROR
        except aiohttp.ClientResponseError as e:
            logger.debug("Failed fetch: url=%s reason=%s", request.url, e.message)
            response_status_code = e.status
        except Exception as e:
            logger.debug("Failed fetch: url=%s reason=%s", request.url, e)
            if isinstance(e, CancelledError):
                response_status_code = 499
            else:
                response_status_code = 500

            # Pass the exception to the middleware
            for middleware in self.middlewares:
                await middleware.process_exception(request, e)
        finally:
            # Make sure there is a valid Response object.
            if not response:
                response = Response(
                    url=request.url,
                    method=request.method,
                    encoding=request.encoding,
                    headers={},
                    history=history or [],
                    status_code=response_status_code or 500,
                    request=request,
                    error_type=error_type_hint,
                )

            # Tell the crawler to retry this Request
            if response.status_code in [429, 503, 408]:
                request.set_retry()

            return response

    def _create_request(self, request: Request) -> ClientRequest:
        """
        Create an asyncio HTTP Request.

        :param request: Request object containing request details
        :return: asyncio HTTP Request
        """
        # Convert timeout to ClientTimeout if it's a float
        timeout = request.timeout
        if isinstance(timeout, (int, float)):
            timeout = ClientTimeout(total=float(timeout))

        if request.method.upper() == "GET":
            return self.request_session.get(
                request.url,
                headers=request.headers,
                timeout=timeout,
                params=request.params,
            )
        elif request.method.upper() == "POST":
            return self.request_session.post(
                request.url,
                headers=request.headers,
                timeout=timeout,
                params=request.params,
                data=request.data,
                json=request.json_data,
            )
        elif request.method.upper() == "PUT":
            return self.request_session.put(
                request.url,
                headers=request.headers,
                timeout=timeout,
                params=request.params,
                data=request.data,
                json=request.json_data,
            )
        elif request.method.upper() == "DELETE":
            return self.request_session.delete(
                request.url,
                headers=request.headers,
                timeout=timeout,
                params=request.params,
            )
        else:
            raise ValueError(
                f"HTTP method {request.method} is not valid. Must be GET, POST, PUT, or DELETE"
            )

    def _failed_response(
        self,
        request: Request,
        status: int,
        history: List[URL],
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        """
        Create a failed Response object with the provided Status Code.

        :param request: Request object
        :param status: HTTP Status Code
        :param history: Response History as list of URLs
        :param headers: Response Headers
        :return: Failed Response object
        """
        return Response(
            url=request.url,
            method=request.method,
            encoding=request.encoding,
            headers=headers or {},
            history=history or [],
            status_code=status,
            request=request,
        )

    async def _read_response(
        self, resp: ClientResponse, max_content_length: int
    ) -> Tuple[bytes, int]:
        """
        Read HTTP Response content as bytes.

        :param resp: asyncio HTTP Response
        :param max_content_length: Maximum allowed content length
        :return: Tuple (body bytes, content length in bytes)
        """
        body: bytes = b""
        try:
            async for chunk in resp.content.iter_chunked(
                8192
            ):  # 8KB chunks for better performance
                if not chunk:
                    break
                body += chunk
                if len(body) > max_content_length:
                    raise ContentLengthError(max_content_length)
        except (IncompleteReadError, LimitOverrunError) as e:
            logger.exception("Failed to read Response content: %s: %s", self, e)
            raise ContentReadError

        return body, len(body)

    @staticmethod
    async def _read_json(resp_text: str) -> dict:
        """
        Attempt to read Response content as JSON.

        :param resp_text: HTTP response content as text string
        :return: JSON dict or empty dict
        """
        # If the text hasn't been parsed then we won't be able to parse JSON either.
        if not resp_text:
            return {}

        stripped = resp_text.strip()
        if not stripped:
            return {}

        try:
            return json.loads(stripped)
        except (ValueError, json.JSONDecodeError):
            return {}

    async def _delay_request(self, delay: float = 0) -> None:
        """
        Delay the request by sleeping.

        :param delay: Time in seconds to delay
        """
        if delay > 0:
            # Sleep for the delay plus up to 100ms of random jitter to spread out requests.
            await asyncio.sleep(delay + (random() * 0.1))
