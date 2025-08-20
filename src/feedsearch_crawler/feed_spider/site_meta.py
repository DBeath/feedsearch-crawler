from typing import List, Union, Dict, Any

from yarl import URL

from feedsearch_crawler.crawler import Item


class SiteMeta(Item):
    url: Union[URL, None] = None
    site_url: str = ""
    site_name: str = ""
    icon_url: Union[URL, None] = None
    icon_data_uri: str = ""
    possible_icons: List = []
    host: str = ""

    def __init__(self, url: URL, **kwargs) -> None:
        super().__init__(**kwargs)
        self.url = url

    def serialize(self) -> Dict[str, Any]:
        return {
            "url": str(self.url),
            "site_name": self.site_name,
            "icon_url": str(self.icon_url) if self.icon_url else None,
        }

    def __eq__(self, other: "SiteMeta") -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.url == other.url

    def __hash__(self) -> str:
        return hash(self.url)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(url={str(self.url)}, title={self.title})"
