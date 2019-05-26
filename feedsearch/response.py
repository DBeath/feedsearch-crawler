from typing import List
from yarl import URL


class Response:
    def __init__(self,
                 url: URL,
                 method: str,
                 encoding: str = "",
                 data: str = "",
                 history: List[URL] = None,
                 headers: dict = None,
                 status_code: int = -1):
        self.url = url
        self.encoding = encoding
        self.method = method
        self.data = data
        self.history = history
        self.headers = headers
        self.status_code = status_code

    @property
    def domain(self) -> str:
        return self.url.host

    @property
    def previous_domain(self) -> str:
        if not self.history:
            return ""
        return self.history[-1].host