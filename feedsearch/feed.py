from crawler.item import Item
from typing import List


class Feed(Item):
    score: int = ""
    url: str = ""
    content_type: str = ""
    version: str = ""
    title: str = ""
    hubs: List[str] = []
    description: str = ""
    is_push: bool = False
    self_url: str = ""

    def serialize(self):
        return dict(
            url=self.url,
            title=self.title,
            version=self.version,
            score=self.score,
            hubs=self.hubs,
            description=self.description,
            is_push=self.is_push,
            self_url=self.self_url,
        )
