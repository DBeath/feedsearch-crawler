from typing import List

from yarl import URL

from feedsearch_crawler.crawler import Item


class SiteMeta(Item):
    url: URL = None
    site_url: str = ""
    site_name: str = ""
    icon_url: URL = None
    icon_data_uri: str = ""
    possible_icons: List = []
    host: str = ""

    def __init__(self, url: URL, **kwargs) -> None:
        super().__init__(**kwargs)
        self.url = url

    def serialize(self):
        return dict(
            url=str(self.url), site_name=self.site_name, icon_url=str(self.icon_url)
        )

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.url == other.url

    def __hash__(self):
        return hash(self.url)

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self.url)})"
