from yarl import URL
from typing import Union

from feedsearch_crawler.crawler import Item


class Favicon(Item):
    url: Union[URL, None] = None
    priority: int = 0
    rel: str = ""
    data_uri: str = ""
    resp_url: Union[URL, None] = None
    site_host: str = ""

    def __eq__(self, other: "Favicon") -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.url == other.url

    def __hash__(self) -> str:
        return hash(self.url)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(url={str(self.url)}, site_host={self.site_host})"

    def matches_host(self, host: str, requires_data_uri: bool = False) -> bool:
        """
        Check that the Favicon site_host is a match for the host.

        :param host: domain host url string
        :param requires_data_uri: Whether the Favicon is required to have a data_uri
        :return: bool
        """
        return (
            bool(self.url)
            and bool(self.site_host)
            and bool(self.site_host in host)
            and (bool(self.data_uri) if requires_data_uri else True)
        )
