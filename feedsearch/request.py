from types import AsyncGeneratorType
from typing import List, Union, Tuple
from yarl import URL
import logging
from aiohttp import ClientSession
import aiohttp
import asyncio
from .response import Response
from .item import Item
from inspect import iscoroutinefunction

class Request:
    METHOD = ['GET', 'POST']

    def __init__(self,
                 url: URL,
                 request_session: ClientSession,
                 encoding: str = 'UTF-8',
                 method: str = "GET",
                 headers: dict = None,
                 timeout: float = 5.0,
                 history: List = None,
                 callback = None):
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


        self.logger = logging.getLogger("feedsearch")

    async def fetch(self) -> Tuple[AsyncGeneratorType, Response]:
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            resp = await self.request_session.get(self.url, headers=self.headers, timeout=timeout)
            try:
                resp_data = await resp.text(encoding=self.encoding)
            except UnicodeDecodeError:
                resp_data = await resp.read()

            history = self.history.append(resp.url)
            headers = resp.headers
            response = Response(url=resp.url, method=resp.method, encoding=resp.get_encoding(), status_code=resp.status, history=history, data=resp_data, headers=headers)

        except asyncio.TimeoutError:
            self.logger.warning("Timeout fetching URL: %s", self.url)
            response = self.failed_response(408)

        if iscoroutinefunction(self.callback):
            callback_result = await self.callback(self, response)
        else:
            callback_result = self.callback(self, response)

        return callback_result, response


    def failed_response(self, status: int) -> Response:
        return Response(url=self.url, method=self.method, encoding=self.encoding, history=self.history, status_code=status)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.url})"
