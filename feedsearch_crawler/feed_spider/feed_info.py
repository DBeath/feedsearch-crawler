from datetime import datetime
from typing import List

from yarl import URL

from feedsearch_crawler.crawler import Item, to_string


class FeedInfo(Item):
    bozo: int = 0
    content_length: int = 0
    content_type: str = ""
    description: str = ""
    favicon: URL = ""
    favicon_data_uri: str = ""
    hubs: List[str] = []
    is_podcast: bool = False
    is_push: bool = False
    item_count: int = 0
    last_updated: datetime = None
    score: int = 0
    self_url: URL = ""
    site_name: str = ""
    site_url: URL = ""
    title: str = ""
    url: URL = ""
    velocity: float = 0
    version: str = ""

    def serialize(self):
        last_updated = self.last_updated.isoformat() if self.last_updated else ""

        return dict(
            bozo=self.bozo,
            description=self.description,
            content_length=self.content_length,
            content_type=self.content_type,
            favicon=to_string(self.favicon),
            favicon_data_uri=self.favicon_data_uri,
            hubs=self.hubs,
            is_podcast=self.is_podcast,
            is_push=self.is_push,
            item_count=self.item_count,
            last_updated=last_updated,
            score=self.score,
            self_url=to_string(self.self_url),
            site_name=self.site_name,
            site_url=to_string(self.site_url),
            title=self.title,
            url=to_string(self.url),
            velocity=self.velocity,
            version=self.version,
        )

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.url == other.url

    def __hash__(self):
        return hash(self.url)

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self.url)})"
