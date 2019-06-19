from datetime import datetime
from typing import List

from yarl import URL

from feedsearch_crawler.crawler import Item, to_string


class FeedInfo(Item):
    score: int = ""
    url: URL = ""
    content_type: str = ""
    version: str = ""
    title: str = ""
    hubs: List[str] = []
    description: str = ""
    is_push: bool = False
    self_url: str = ""
    bozo: int = 0
    favicon: URL = ""
    site_url: URL = ""
    site_name: str = ""
    favicon_data_uri: str = ""
    content_length: int = 0
    last_updated: datetime = None

    def serialize(self):
        last_updated = self.last_updated.isoformat() if self.last_updated else ""

        return dict(
            url=to_string(self.url),
            title=self.title,
            version=self.version,
            score=self.score,
            hubs=self.hubs,
            description=self.description,
            is_push=self.is_push,
            self_url=self.self_url,
            favicon=to_string(self.favicon),
            content_type=self.content_type,
            bozo=self.bozo,
            site_url=to_string(self.site_url),
            site_name=self.site_name,
            favicon_data_uri=self.favicon_data_uri,
            content_length=self.content_length,
            last_updated=last_updated,
        )

    def __init__(self, url: URL, content_type: str):
        super().__init__()
        self.url = url
        self.content_type = content_type

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.url == other.url

    def __hash__(self):
        return hash(self.url)

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self.url)})"
