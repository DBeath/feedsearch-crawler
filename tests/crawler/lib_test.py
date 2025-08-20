import pytest
from yarl import URL
from typing import Any

from feedsearch_crawler.crawler.lib import (
    CrawlerPriorityQueue,
    coerce_url,
    is_same_domain,
)


def test_coerce_url() -> None:
    assert coerce_url("test.com") == URL("http://test.com")
    assert coerce_url("https://test.com") == URL("https://test.com")
    assert coerce_url(" https://test.com") == URL("https://test.com")
    assert coerce_url("test.com/path/path2") == URL("http://test.com/path/path2")

    assert coerce_url("test.com", https=True) == URL("https://test.com")
    assert coerce_url("https://test.com", https=True) == URL("https://test.com")
    assert coerce_url(" https://test.com", https=True) == URL("https://test.com")
    assert coerce_url("http://test.com", https=True) == URL("https://test.com")
    assert coerce_url("test.com/path/path2", https=True) == URL(
        "https://test.com/path/path2"
    )
    assert coerce_url("//test.com") == URL("http://test.com")
    assert coerce_url("feed://test.com") == URL("feed://test.com")
    assert coerce_url("feed://www.internet-law.de/?feed=/feed/") == URL(
        "feed://www.internet-law.de/?feed=/feed/"
    )


def test_is_same_domain() -> None:
    assert is_same_domain("test.com", "test.com") is True
    assert is_same_domain("example.com", "test.com") is False
    assert is_same_domain("feeds.test.com", "test.com") is False
    assert is_same_domain("test.com", "feeds.test.com") is True
    assert is_same_domain("test.com", "test.feeds.test.com") is True
    assert is_same_domain("www.test.com", "test.com") is True
    assert is_same_domain("www.test.com", "feed.test.com") is True
    assert is_same_domain("test.www.test.com", "test.com") is False


@pytest.mark.asyncio
async def test_crawler_priority_queue() -> None:
    queue = CrawlerPriorityQueue()

    # Test empty queue
    assert queue.empty()
    assert queue.qsize() == 0

    # Test put and get
    await queue.put((1, "data1"))
    await queue.put((3, "data3"))
    await queue.put((2, "data2"))

    assert queue.qsize() == 3
    assert await queue.get() == (1, "data1")
    assert await queue.get() == (2, "data2")
    assert await queue.get() == (3, "data3")

    # Test clear
    await queue.put((5, "data5"))
    await queue.put((4, "data4"))
    queue.clear()

    assert queue.empty()
    assert queue.qsize() == 0

    # Test put with custom item class
    class CustomItem:
        def __init__(self, priority: int, data: str) -> None:
            self.priority = priority
            self.data = data

        def __lt__(self, other: Any) -> bool:
            return self.priority < other.priority

        def __eq__(self, other: Any) -> bool:
            return self.priority == other.priority and self.data == other.data

    await queue.put(CustomItem(9, "data9"))
    await queue.put(CustomItem(8, "data8"))

    assert queue.qsize() == 2
    assert await queue.get() == CustomItem(8, "data8")
    assert await queue.get() == CustomItem(9, "data9")
