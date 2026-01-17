"""Search result types."""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from feedsearch_crawler.exceptions import SearchError
from feedsearch_crawler.feed_spider.feed_info import FeedInfo


@dataclass
class SearchResult:
    """
    Result of a feed search operation.

    Contains discovered feeds and optional error information if the
    root URL failed to load.
    """

    feeds: List[FeedInfo] = field(default_factory=list)
    """List of discovered feeds"""

    root_error: Optional[SearchError] = None
    """Error from root URL if it failed to load"""

    stats: Optional[Dict[str, Any]] = None
    """Optional statistics from the crawl"""

    # Backward compatibility methods
    def __iter__(self) -> Iterator[FeedInfo]:
        """Allow iteration over feeds directly."""
        return iter(self.feeds)

    def __len__(self) -> int:
        """Return number of feeds found."""
        return len(self.feeds)

    def __bool__(self) -> bool:
        """Return True if any feeds were found."""
        return len(self.feeds) > 0

    def __getitem__(self, index: int) -> FeedInfo:
        """Allow indexing into feeds."""
        return self.feeds[index]
