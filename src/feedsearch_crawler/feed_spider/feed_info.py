from datetime import datetime
from typing import List, Union, Dict, Any

from yarl import URL

from feedsearch_crawler.crawler import Item


class FeedInfo(Item):
    bozo: int = 0
    content_length: int = 0
    content_type: str = ""
    description: str = ""
    favicon: Union[URL, None] = None
    favicon_data_uri: str = ""
    hubs: List[str] = []
    is_podcast: bool = False
    is_push: bool = False
    item_count: int = 0
    last_updated: datetime
    score: int = 0
    self_url: Union[URL, None] = None
    site_name: str = ""
    site_url: Union[URL, None] = None
    title: str = ""
    url: Union[URL, None] = None
    velocity: float = 0
    version: str = ""

    def serialize(self) -> Dict[str, Any]:
        return {
            "url": str(self.url),
            "title": self.title,
            "description": self.description,
            "site_name": self.site_name,
            "site_url": str(self.site_url) if self.site_url else None,
            "favicon": str(self.favicon) if self.favicon else None,
            "version": self.version,
            "score": self.score,
            "velocity": self.velocity,
            "last_updated": self.last_updated.isoformat()
            if self.last_updated
            else None,
            "item_count": self.item_count,
            "is_push": self.is_push,
            "hubs": self.hubs,
            "self_url": str(self.self_url) if self.self_url else None,
            "bozo": self.bozo,
        }

    def __eq__(self, other: "FeedInfo") -> bool:
        if not isinstance(other, FeedInfo):
            return False
        return self.url == other.url

    def __hash__(self) -> str:
        return hash(self.url)

    def __repr__(self) -> str:
        return f"FeedInfo(url={self.url}, title={self.title})"
