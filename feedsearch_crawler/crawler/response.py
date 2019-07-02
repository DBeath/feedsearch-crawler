import uuid
from typing import List, Dict, Any, Optional

from yarl import URL


class Response:
    _xml = None

    def __init__(
        self,
        url: URL,
        method: str,
        encoding: str = "",
        text: str = "",
        json: Dict = None,
        data: bytes = b"",
        history: List[URL] = None,
        headers=None,
        status_code: int = -1,
        cookies=None,
        xml_parser=None,
        redirect_history=None,
        content_length: int = 0,
    ):
        self.url = url
        self.encoding = encoding
        self.method = method
        self.text = text
        self.json = json
        self.data = data
        self.history = history or []
        self.headers = headers or {}
        self.status_code = status_code
        self.cookies = cookies
        self.id = uuid.uuid4()
        self._xml_parser = xml_parser
        self.redirect_history = redirect_history
        self.content_length = content_length

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

    @property
    def originator_url(self) -> Optional[URL]:
        if not self.history or len(self.history) == 1:
            return None
        return self.history[-2]

    @property
    async def xml(self) -> Any:
        if self._xml:
            return self._xml

        if not self._xml_parser:
            return None

        if not self.text or not self.data or not self.encoding:
            self.text = self.data.decode(self.encoding)

        self._xml = await self._xml_parser(self.text)
        return self._xml

    def is_max_depth_reached(self, max_depth: int) -> bool:
        """
        Check if the max response depth has been reached.

        :param max_depth: Max length of response history
        :return: boolean
        """
        if max_depth and len(self.history) >= max_depth:
            return True
        return False

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self.url)})"
