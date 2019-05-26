from typing import List
from yarl import URL
import logging
from aiohttp import ClientSession
from .response import Response

class Request:
    METHOD = ['GET', 'POST']

    def __init__(self,
                 url: URL,
                 request_session: ClientSession,
                 method: str = "GET",
                 headers: dict = None,
                 history: List = None):
        self.url = url
        self.method = method.upper()
        if self.method not in self.METHOD:
            raise ValueError(f"{self.method} is not supported")
        if not isinstance(request_session, ClientSession):
            raise ValueError(f"request_session must be of type ClientSession")
        self.request_session = request_session

        self.logger = logging.getLogger("feedsearch")

    async def fetch(self) -> Response:
        try:
            async with 