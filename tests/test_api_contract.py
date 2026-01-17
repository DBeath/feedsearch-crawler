"""
Contract tests for public API.

These tests enforce the API contract that must not be broken in v1.x releases.
Breaking these contracts requires a major version bump (v2.0.0).
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from feedsearch_crawler import (
    SearchResult,
    search,
    search_async,
    search_with_info,
    search_async_with_info,
)
from feedsearch_crawler.feed_spider.feed_info import FeedInfo


class TestSearchReturnTypeContract:
    """
    CONTRACT: search() must always return List[FeedInfo] in v1.x.

    This contract ensures backward compatibility. Breaking this requires v2.0.0.
    """

    @patch("feedsearch_crawler.search_async")
    def test_search_returns_list_type(self, mock_search_async):
        """CONTRACT: search() return type must be list."""
        mock_feeds = [FeedInfo(url="https://example.com/feed.xml")]
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            result = search("https://example.com")

        # CRITICAL: Must be exactly list type
        assert type(result) is list, (
            f"CONTRACT VIOLATION: search() must return list, got {type(result).__name__}"
        )

    @patch("feedsearch_crawler.search_async")
    def test_search_returns_list_of_feedinfo(self, mock_search_async):
        """CONTRACT: search() must return List[FeedInfo]."""
        mock_feeds = [
            FeedInfo(url="https://example.com/feed1.xml"),
            FeedInfo(url="https://example.com/feed2.xml"),
        ]
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            result = search("https://example.com")

        # CRITICAL: Must be list of FeedInfo objects
        assert isinstance(result, list), "Must be list"
        assert all(isinstance(item, FeedInfo) for item in result), (
            "All items must be FeedInfo"
        )

    @patch("feedsearch_crawler.search_async")
    def test_search_empty_list_is_list(self, mock_search_async):
        """CONTRACT: search() returns empty list (not None, not other falsy value)."""
        mock_feeds = []
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            result = search("https://example.com")

        # CRITICAL: Empty result must be list, not None
        assert type(result) is list, "Empty result must be list"
        assert result == [], "Empty result must be []"
        assert not result, "Empty list must be falsy"

    @patch("feedsearch_crawler.search_async")
    def test_search_never_returns_searchresult(self, mock_search_async):
        """CONTRACT: search() must never return SearchResult."""
        mock_feeds = []
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            result = search("https://example.com")

        # CRITICAL: Must not be SearchResult
        assert not isinstance(result, SearchResult), (
            "CONTRACT VIOLATION: search() must not return SearchResult"
        )


class TestSearchAsyncReturnTypeContract:
    """
    CONTRACT: search_async() must always return List[FeedInfo] in v1.x.

    This contract ensures backward compatibility. Breaking this requires v2.0.0.
    """

    @pytest.mark.asyncio
    async def test_search_async_returns_list_type(self):
        """CONTRACT: search_async() return type must be list."""
        with patch("feedsearch_crawler.FeedsearchSpider") as mock_spider_class:
            mock_spider = Mock()
            mock_spider.items = [FeedInfo(url="https://example.com/feed.xml")]
            mock_spider.crawl = AsyncMock()
            mock_spider_class.return_value = mock_spider

            result = await search_async("https://example.com")

        # CRITICAL: Must be exactly list type
        assert type(result) is list, (
            f"CONTRACT VIOLATION: search_async() must return list, got {type(result).__name__}"
        )

    @pytest.mark.asyncio
    async def test_search_async_returns_list_of_feedinfo(self):
        """CONTRACT: search_async() must return List[FeedInfo]."""
        with patch("feedsearch_crawler.FeedsearchSpider") as mock_spider_class:
            mock_spider = Mock()
            mock_spider.items = [
                FeedInfo(url="https://example.com/feed1.xml"),
                FeedInfo(url="https://example.com/feed2.xml"),
            ]
            mock_spider.crawl = AsyncMock()
            mock_spider_class.return_value = mock_spider

            result = await search_async("https://example.com")

        # CRITICAL: Must be list of FeedInfo objects
        assert isinstance(result, list), "Must be list"
        assert all(isinstance(item, FeedInfo) for item in result), (
            "All items must be FeedInfo"
        )

    @pytest.mark.asyncio
    async def test_search_async_never_returns_searchresult(self):
        """CONTRACT: search_async() must never return SearchResult."""
        with patch("feedsearch_crawler.FeedsearchSpider") as mock_spider_class:
            mock_spider = Mock()
            mock_spider.items = []
            mock_spider.crawl = AsyncMock()
            mock_spider_class.return_value = mock_spider

            result = await search_async("https://example.com")

        # CRITICAL: Must not be SearchResult
        assert not isinstance(result, SearchResult), (
            "CONTRACT VIOLATION: search_async() must not return SearchResult"
        )


class TestSearchWithInfoReturnTypeContract:
    """
    CONTRACT: search_with_info() must always return SearchResult in v1.x.

    This is the new API that provides error information.
    """

    @patch("feedsearch_crawler.search_async_with_info")
    def test_search_with_info_returns_searchresult_type(self, mock_async):
        """CONTRACT: search_with_info() return type must be SearchResult."""
        mock_result = SearchResult(feeds=[], root_error=None, stats=None)
        mock_async.return_value = mock_result

        with patch("asyncio.run", return_value=mock_result):
            result = search_with_info("https://example.com")

        # CRITICAL: Must be exactly SearchResult type
        assert type(result) is SearchResult, (
            f"CONTRACT VIOLATION: search_with_info() must return SearchResult, "
            f"got {type(result).__name__}"
        )

    @patch("feedsearch_crawler.search_async_with_info")
    def test_search_with_info_never_returns_list(self, mock_async):
        """CONTRACT: search_with_info() must never return plain list."""
        mock_result = SearchResult(feeds=[], root_error=None, stats=None)
        mock_async.return_value = mock_result

        with patch("asyncio.run", return_value=mock_result):
            result = search_with_info("https://example.com")

        # CRITICAL: Must not be plain list
        assert type(result) is not list, (
            "CONTRACT VIOLATION: search_with_info() must not return plain list"
        )


class TestSearchAsyncWithInfoReturnTypeContract:
    """
    CONTRACT: search_async_with_info() must always return SearchResult in v1.x.

    This is the new async API that provides error information.
    """

    @pytest.mark.asyncio
    async def test_search_async_with_info_returns_searchresult_type(self):
        """CONTRACT: search_async_with_info() return type must be SearchResult."""
        with patch("feedsearch_crawler.FeedsearchSpider") as mock_spider_class:
            mock_spider = Mock()
            mock_spider.items = []
            mock_spider.crawl = AsyncMock()
            mock_spider.get_root_error = Mock(return_value=None)
            mock_spider.get_stats = Mock(return_value={})
            mock_spider_class.return_value = mock_spider

            result = await search_async_with_info("https://example.com")

        # CRITICAL: Must be exactly SearchResult type
        assert type(result) is SearchResult, (
            f"CONTRACT VIOLATION: search_async_with_info() must return SearchResult, "
            f"got {type(result).__name__}"
        )

    @pytest.mark.asyncio
    async def test_search_async_with_info_never_returns_list(self):
        """CONTRACT: search_async_with_info() must never return plain list."""
        with patch("feedsearch_crawler.FeedsearchSpider") as mock_spider_class:
            mock_spider = Mock()
            mock_spider.items = []
            mock_spider.crawl = AsyncMock()
            mock_spider.get_root_error = Mock(return_value=None)
            mock_spider.get_stats = Mock(return_value={})
            mock_spider_class.return_value = mock_spider

            result = await search_async_with_info("https://example.com")

        # CRITICAL: Must not be plain list
        assert type(result) is not list, (
            "CONTRACT VIOLATION: search_async_with_info() must not return plain list"
        )


class TestBehaviorContract:
    """
    CONTRACT: Behavior contracts that must be maintained.
    """

    @patch("feedsearch_crawler.search_async")
    def test_search_and_search_with_info_return_same_feeds(self, mock_search_async):
        """
        CONTRACT: search() and search_with_info() must return the same feeds list.

        The only difference should be the wrapper (list vs SearchResult).
        """
        mock_feeds = [
            FeedInfo(url="https://example.com/feed1.xml"),
            FeedInfo(url="https://example.com/feed2.xml"),
        ]

        # Mock for search()
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            list_result = search("https://example.com")

        # Mock for search_with_info()
        mock_result = SearchResult(feeds=mock_feeds, root_error=None, stats=None)

        with patch("feedsearch_crawler.search_async_with_info") as mock_info:
            mock_info.return_value = mock_result
            with patch("asyncio.run", return_value=mock_result):
                searchresult_result = search_with_info("https://example.com")

        # CRITICAL: Both must return the same feeds
        assert list_result == searchresult_result.feeds, (
            "CONTRACT VIOLATION: search() and search_with_info() must return same feeds"
        )

    @patch("feedsearch_crawler.search_async")
    def test_search_respects_list_protocol(self, mock_search_async):
        """CONTRACT: search() result must support all list operations."""
        mock_feeds = [
            FeedInfo(url="https://example.com/feed1.xml"),
            FeedInfo(url="https://example.com/feed2.xml"),
        ]
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            result = search("https://example.com")

        # CRITICAL: Must support list operations
        assert len(result) == 2, "Must support len()"
        assert result[0] == mock_feeds[0], "Must support indexing"
        assert result[-1] == mock_feeds[-1], "Must support negative indexing"
        assert list(result) == mock_feeds, "Must support iteration"
        assert result == mock_feeds, "Must support equality"

        # Should be mutable like a list
        result.append(FeedInfo(url="https://example.com/feed3.xml"))
        assert len(result) == 3, "Must support append()"


class TestTypeAnnotationContract:
    """
    CONTRACT: Type annotations must be accurate and stable.

    Type checkers (mypy, pyright) must pass with these signatures.
    """

    def test_search_has_correct_type_annotation(self):
        """CONTRACT: search() annotation must be List[FeedInfo]."""
        from typing import get_type_hints

        hints = get_type_hints(search)
        return_type = hints.get("return")

        # Check if return type is List[FeedInfo]
        assert hasattr(return_type, "__origin__"), "Return type must have __origin__"
        assert return_type.__origin__ is list, (
            f"CONTRACT VIOLATION: search() must be annotated as returning list, "
            f"got {return_type}"
        )

    def test_search_with_info_has_correct_type_annotation(self):
        """CONTRACT: search_with_info() annotation must be SearchResult."""
        from typing import get_type_hints

        hints = get_type_hints(search_with_info)
        return_type = hints.get("return")

        # Check if return type is SearchResult
        assert return_type is SearchResult, (
            f"CONTRACT VIOLATION: search_with_info() must be annotated as returning "
            f"SearchResult, got {return_type}"
        )
