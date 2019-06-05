import uuid
from typing import List, Dict, Any

from yarl import URL


class Response:
    def __init__(
        self,
        url: URL,
        method: str,
        encoding: str = "",
        text: str = "",
        parsed_xml: Any = None,
        json: Dict = None,
        history: List[URL] = None,
        headers=None,
        status_code: int = -1,
    ):
        self.url = url
        self.encoding = encoding
        self.method = method
        self.text = text
        self.json = json
        self.history = history or []
        self.headers = headers
        self.status_code = status_code
        self.parsed_xml = parsed_xml
        self.id = uuid.uuid4()

    @property
    def ok(self) -> bool:
        return self.status_code == 0 or 200 <= self.status_code <= 299

    @property
    def domain(self) -> str:
        return self.url.host

    @property
    def previous_domain(self) -> str:
        if not self.history:
            return ""
        return self.history[-1].host

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self.url)})"
