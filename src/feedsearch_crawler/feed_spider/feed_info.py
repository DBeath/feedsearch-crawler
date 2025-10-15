from datetime import datetime
from typing import List, Union, Dict, Any

from yarl import URL

from feedsearch_crawler.crawler import Item


class FeedInfo(Item):
    """Feed information with metadata and validation.

    Represents a discovered RSS/Atom/JSON feed with its metadata.
    All numeric fields are validated to be non-negative.
    """

    # Core identification
    url: Union[URL, None] = None
    title: str = ""
    description: str = ""
    version: str = ""

    # Content metadata
    item_count: int = 0
    last_updated: Union[datetime, None] = None
    velocity: float = 0.0

    # Site metadata
    site_name: str = ""
    site_url: Union[URL, None] = None
    favicon: Union[URL, None] = None
    favicon_data_uri: str = ""

    # Feed properties
    is_push: bool = False
    is_podcast: bool = False
    hubs: List[str] = []

    # Technical details
    content_type: str = ""
    content_length: int = 0
    bozo: int = 0
    self_url: Union[URL, None] = None

    # Scoring
    score: int = 0

    def __init__(self, **kwargs: Dict[str, Any]) -> None:
        """Initialize FeedInfo with validation."""
        super().__init__(**kwargs)
        self._validate()

    def _validate(self) -> None:
        """Validate field values after initialization."""
        if self.bozo not in (0, 1):
            raise ValueError(f"bozo must be 0 or 1, got {self.bozo}")
        if self.score < 0:
            raise ValueError(f"score must be >= 0, got {self.score}")
        if self.item_count < 0:
            raise ValueError(f"item_count must be >= 0, got {self.item_count}")
        if self.content_length < 0:
            raise ValueError(f"content_length must be >= 0, got {self.content_length}")
        if self.velocity < 0:
            raise ValueError(f"velocity must be >= 0, got {self.velocity}")

    @staticmethod
    def _url_to_str(url: Union[URL, None]) -> Union[str, None]:
        """Convert URL to string, handling None values."""
        return str(url) if url is not None else None

    def serialize(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict.

        Returns dict with all fields in a consistent order.
        URL objects are converted to strings, None values preserved.
        """
        return {
            # Core identification
            "url": self._url_to_str(self.url),
            "title": self.title,
            "description": self.description,
            "version": self.version,
            # Content metadata
            "item_count": self.item_count,
            "last_updated": self.last_updated.isoformat()
            if self.last_updated
            else None,
            "velocity": self.velocity,
            # Site metadata
            "site_name": self.site_name,
            "site_url": self._url_to_str(self.site_url),
            "favicon": self._url_to_str(self.favicon),
            "favicon_data_uri": self.favicon_data_uri,
            # Feed properties
            "is_push": self.is_push,
            "is_podcast": self.is_podcast,
            "hubs": self.hubs,
            # Technical details
            "content_type": self.content_type,
            "content_length": self.content_length,
            "bozo": self.bozo,
            "self_url": self._url_to_str(self.self_url),
            # Scoring
            "score": self.score,
        }

    def __eq__(self, other: "FeedInfo") -> bool:
        if not isinstance(other, FeedInfo):
            return False
        return self.url == other.url

    def __hash__(self) -> str:
        return hash(self.url)

    def __repr__(self) -> str:
        return f"FeedInfo(url={self.url}, title={self.title})"
