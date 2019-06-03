import asyncio
import copy
import hashlib
import logging
import uuid
from inspect import isasyncgenfunction
from types import AsyncGeneratorType
from typing import List, Tuple

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

        self.logger = logging.getLogger(__name__)

    async def fetch(self) -> Tuple[AsyncGeneratorType, Response]:
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            request = self.request_session.get(
                self.url, headers=self.headers, timeout=timeout
            )
            async with request as resp:
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

            response = Response(
                url=resp.url,
                method=resp.method,
                encoding=resp.get_encoding(),
                status_code=resp.status,
                history=history,
                text=resp_data,
                json=resp_json,
                headers=resp.headers,
            )

        except asyncio.TimeoutError:
            self.logger.warning("Timeout fetching URL: %s", self.url)
            response = self._failed_response(408)
        except aiohttp.ClientResponseError as e:
            self.logger.warning(
                "Failed fetching URL: %s, Reason: %s", self.url, e.message
            )
            response = self._failed_response(e.status)

        callback_result = None
        if self.callback and isasyncgenfunction(self.callback):
            callback_result = self.callback(self, response)
        else:
            self.logger.warning("Response callback must be an asyncgenfunction. %s %s", self, self.callback)

        return callback_result, response

    def _failed_response(self, status: int) -> Response:
        return Response(
            url=self.url,
            method=self.method,
            encoding=self.encoding,
            history=self.history,
            status_code=status,
        )

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self.url)})"


def request_fingerprint(request: Request) -> str:
    fp = hashlib.sha1()
    fp.update(to_bytes(request.method))
    fp.update(to_bytes(canonicalize_url(str(request.url))))
    return fp.hexdigest()
