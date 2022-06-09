import uuid
import logging
from typing import List, Dict, Any, Optional, Union
from multidict import CIMultiDictProxy

from yarl import URL

from feedsearch_crawler.crawler.lib import is_same_domain


logger = logging.getLogger(__name__)


class Response:
    _xml = None

    def __init__(
        self,
        url: URL,
        method: str,
        headers: Union[CIMultiDictProxy[str], dict],
        status_code: int = -1,
        encoding: str = "",
        text: str = "",
        json: Dict = {},
        data: bytes = b"",
        history: List[URL] = [],
        cookies=None,
        xml_parser=None,
        redirect_history=None,
        content_length: int = 0,
        meta: Dict = {},
    ):
        self.url = url
        self.encoding = encoding
        self.method = method
        self.text = text
        self.json = json
        self.data = data
        self.history = history
        self.headers = headers
        self.status_code = status_code
        self.cookies = cookies
        self.id = uuid.uuid4()
        self._xml_parser = xml_parser
        self.redirect_history = redirect_history
        self.content_length = content_length
        self.meta = meta
        self.origin: URL = url.origin()

    @property
    def ok(self) -> bool:
        return self.status_code == 0 or 200 <= self.status_code <= 299

    @property
    def domain(self) -> Optional[str]:
        return self.url.host

    @property
    def scheme(self) -> str:
        return self.url.scheme

    @property
    def previous_domain(self) -> Optional[str]:
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
        """
        Use provided XML Parsers method to attempt to parse Response content as XML.

        :return: Response content as parsed XML. Type depends on XML parser.
        """
        if self._xml:
            return self._xml

        if not self._xml_parser:
            return self._xml

        if not self.text and self.data and self.encoding:
            try:
                self.text = self.data.decode(self.encoding)
            except UnicodeDecodeError as e:
                logger.exception("Error decoding data to %s: %s", self.encoding, e)
                return self._xml

        try:
            self._xml = await self._xml_parser(self.text)
        except Exception as e:
            logger.exception("Error parsing response xml: %s", e)
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

    def is_original_domain(self) -> bool:
        """
        Check if this response is still at the original domain in the response chain.

        :return: boolean
        """
        # This is the first Response in the chain
        if len(self.history) < 2:
            return True
        # URL is same domain or sub-domain
        if is_same_domain(self.history[0].host, self.url.host):
            return True

        return False

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self.url)})"
