import asyncio
import copy
import hashlib
import inspect
import logging
import uuid
from typing import List, Tuple, Any

import aiohttp
from aiohttp import ClientSession
from w3lib.url import canonicalize_url
from yarl import URL

from crawler.lib import to_bytes
from crawler.response import Response


class Request:
    METHOD = ["GET", "POST"]

    def __init__(
        self,
        url: URL,
        request_session: ClientSession,
        encoding: str = "UTF-8",
        method: str = "GET",
        headers: dict = None,
        timeout: float = 5.0,
        history: List = None,
        callback=None,
        xml_parser=None,
        max_size: int = 1024 * 1024 * 10,
        **kwargs,
    ):
        self.url = url
        self.method = method.upper()
        if self.method not in self.METHOD:
            raise ValueError(f"{self.method} is not supported")
        if not isinstance(request_session, ClientSession):
            raise ValueError(f"request_session must be of type ClientSession")
        self.request_session = request_session
        self.headers = headers
        self.timeout = timeout
        self.history = history or []
        self.encoding = encoding
        self.callback = callback
        self.id = uuid.uuid4()
        self.xml_parser = xml_parser
        self.max_size = max_size

        for key, value in kwargs:
            if hasattr(self, key):
                setattr(self, key, value)

        self.logger = logging.getLogger(__name__)

    async def fetch_callback(self) -> Tuple[Any, Response]:
        response = await self._fetch()

        callback_result = None
        if self.callback:
            if inspect.iscoroutinefunction(self.callback):
                callback_result = await self.callback(self, response)
            else:
                callback_result = self.callback(self, response)

        return callback_result, response

    async def _fetch(self) -> Response:
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            request = self.request_session.get(
                self.url, headers=self.headers, timeout=timeout
            )
            async with request as resp:
                content_length: int = int(resp.headers.get("Content-Length", "0"))
                if content_length > self.max_size:
                    return self._failed_response(413)

                valid_content_length = await self._read_response(resp)
                if not valid_content_length:
                    return self._failed_response(413)

                try:
                    resp_data = await resp.text(encoding=self.encoding)
                except UnicodeDecodeError:
                    resp_data = await resp.read()
                try:
                    resp_json = await resp.json()
                except Exception:
                    resp_json = None

            resp.raise_for_status()

            history = copy.deepcopy(self.history)
            history.append(resp.url)

            parsed_xml = await self._parse_xml(resp_data)

            response = Response(
                url=resp.url,
                method=resp.method,
                encoding=resp.get_encoding(),
                status_code=resp.status,
                history=history,
                text=resp_data,
                json=resp_json,
                headers=resp.headers,
                parsed_xml=parsed_xml,
            )

        except asyncio.TimeoutError:
            self.logger.warning("Timeout fetching URL: %s", self.url)
            response = self._failed_response(408)
        except aiohttp.ClientResponseError as e:
            self.logger.warning(
                "Failed fetching URL: %s, Reason: %s", self.url, e.message
            )
            response = self._failed_response(e.status)

        return response

    async def _read_response(self, resp) -> bool:
        body: bytes = b""
        while True:
            chunk = await resp.content.read(1024)
            if not chunk:
                break
            body += chunk
            if len(body) > self.max_size:
                return False
        resp._body = body
        return True

    def _failed_response(self, status: int) -> Response:
        return Response(
            url=self.url,
            method=self.method,
            encoding=self.encoding,
            history=self.history,
            status_code=status,
            headers={},
        )

    async def _parse_xml(self, response_text: str) -> Any:
        try:
            return await self.xml_parser(response_text)
        except Exception:
            return None

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self.url)})"


def request_fingerprint(request: Request) -> str:
    fp = hashlib.sha1()
    fp.update(to_bytes(request.method))
    fp.update(to_bytes(canonicalize_url(str(request.url))))
    return fp.hexdigest()
