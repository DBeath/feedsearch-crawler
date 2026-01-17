"""Tests for error handling and SearchResult functionality."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from yarl import URL

from feedsearch_crawler import (
    SearchResult,
    search,
    search_async,
    search_with_info,
    search_async_with_info,
)
from feedsearch_crawler.exceptions import ErrorType, SearchError
from feedsearch_crawler.feed_spider.feed_info import FeedInfo


class TestSearchResult:
    """Test SearchResult dataclass functionality."""

    def test_search_result_creation(self):
        """Test creating a SearchResult with all fields."""
        feeds = [FeedInfo(url=URL("https://example.com/feed.xml"))]
        error = SearchError(
            url="https://example.com",
            error_type=ErrorType.HTTP_ERROR,
            message="Not found",
            status_code=404,
        )
        stats = {"requests": 10, "responses": 8}

        result = SearchResult(feeds=feeds, root_error=error, stats=stats)

        assert result.feeds == feeds
        assert result.root_error == error
        assert result.stats == stats

    def test_search_result_backward_compatibility_iteration(self):
        """Test that SearchResult is iterable like a list."""
        feeds = [
            FeedInfo(url=URL("https://example.com/feed1.xml")),
            FeedInfo(url=URL("https://example.com/feed2.xml")),
        ]
        result = SearchResult(feeds=feeds)

        # Should be iterable
        feed_list = list(result)
        assert feed_list == feeds

        # Should support for loop
        count = 0
        for feed in result:
            assert isinstance(feed, FeedInfo)
            count += 1
        assert count == 2

    def test_search_result_backward_compatibility_len(self):
        """Test that len() works on SearchResult."""
        feeds = [
            FeedInfo(url=URL("https://example.com/feed1.xml")),
            FeedInfo(url=URL("https://example.com/feed2.xml")),
        ]
        result = SearchResult(feeds=feeds)

        assert len(result) == 2

    def test_search_result_backward_compatibility_bool(self):
        """Test that bool() works on SearchResult."""
        # Non-empty feeds
        result = SearchResult(feeds=[FeedInfo(url=URL("https://example.com/feed.xml"))])
        assert bool(result) is True

        # Empty feeds
        result = SearchResult(feeds=[])
        assert bool(result) is False

    def test_search_result_backward_compatibility_getitem(self):
        """Test that indexing works on SearchResult."""
        feeds = [
            FeedInfo(url=URL("https://example.com/feed1.xml")),
            FeedInfo(url=URL("https://example.com/feed2.xml")),
        ]
        result = SearchResult(feeds=feeds)

        assert result[0] == feeds[0]
        assert result[1] == feeds[1]
        assert result[-1] == feeds[-1]

    def test_search_result_empty(self):
        """Test SearchResult with no feeds."""
        result = SearchResult()

        assert result.feeds == []
        assert result.root_error is None
        assert result.stats is None
        assert len(result) == 0
        assert bool(result) is False


class TestSearchError:
    """Test SearchError dataclass functionality."""

    def test_search_error_creation(self):
        """Test creating a SearchError."""
        error = SearchError(
            url="https://example.com",
            error_type=ErrorType.DNS_FAILURE,
            message="DNS resolution failed",
        )

        assert error.url == "https://example.com"
        assert error.error_type == ErrorType.DNS_FAILURE
        assert error.message == "DNS resolution failed"
        assert error.status_code is None
        assert error.original_exception is None

    def test_search_error_with_status_code(self):
        """Test SearchError with HTTP status code."""
        error = SearchError(
            url="https://example.com",
            error_type=ErrorType.HTTP_ERROR,
            message="Not found",
            status_code=404,
        )

        assert error.status_code == 404

    def test_error_type_enum(self):
        """Test ErrorType enum values."""
        assert ErrorType.DNS_FAILURE.value == "dns_failure"
        assert ErrorType.SSL_ERROR.value == "ssl_error"
        assert ErrorType.CONNECTION_ERROR.value == "connection_error"
        assert ErrorType.HTTP_ERROR.value == "http_error"
        assert ErrorType.TIMEOUT.value == "timeout"
        assert ErrorType.INVALID_URL.value == "invalid_url"
        assert ErrorType.OTHER.value == "other"


class TestPublicAPIErrorHandling:
    """Test error handling in new search_with_info API."""

    @patch("feedsearch_crawler.search_async")
    def test_search_always_returns_list(self, mock_search_async):
        """Test that search() always returns List[FeedInfo]."""
        feeds = [FeedInfo(url=URL("https://example.com/feed.xml"))]
        mock_search_async.return_value = feeds

        with patch("asyncio.run", return_value=feeds):
            result = search("https://example.com")

        assert isinstance(result, list)
        assert type(result) is list
        assert result == feeds

    @patch("feedsearch_crawler.search_async_with_info")
    def test_search_with_info_returns_search_result(self, mock_async_with_info):
        """Test that search_with_info() returns SearchResult."""
        feeds = [FeedInfo(url=URL("https://example.com/feed.xml"))]
        search_result = SearchResult(feeds=feeds, root_error=None, stats=None)
        mock_async_with_info.return_value = search_result

        with patch("asyncio.run", return_value=search_result):
            result = search_with_info("https://example.com")

        assert isinstance(result, SearchResult)
        assert type(result) is SearchResult
        assert result.feeds == feeds

    @pytest.mark.asyncio
    async def test_search_async_always_returns_list(self):
        """Test that search_async() always returns List[FeedInfo]."""
        with patch("feedsearch_crawler.FeedsearchSpider") as mock_spider_class:
            mock_spider = Mock()
            mock_spider.items = [FeedInfo(url=URL("https://example.com/feed.xml"))]
            mock_spider.crawl = AsyncMock()
            mock_spider_class.return_value = mock_spider

            result = await search_async("https://example.com")

            assert isinstance(result, list)
            assert type(result) is list
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_async_with_info_returns_search_result(self):
        """Test that search_async_with_info() returns SearchResult."""
        with patch("feedsearch_crawler.FeedsearchSpider") as mock_spider_class:
            mock_spider = Mock()
            mock_spider.items = [FeedInfo(url=URL("https://example.com/feed.xml"))]
            mock_spider.crawl = AsyncMock()
            mock_spider.get_root_error = Mock(return_value=None)
            mock_spider.get_stats = Mock(return_value={})
            mock_spider_class.return_value = mock_spider

            result = await search_async_with_info("https://example.com")

            assert isinstance(result, SearchResult)
            assert type(result) is SearchResult
            assert len(result.feeds) == 1
            assert result.root_error is None

    @pytest.mark.asyncio
    async def test_search_async_with_info_includes_stats(self):
        """Test that search_async_with_info() includes stats when requested."""
        with patch("feedsearch_crawler.FeedsearchSpider") as mock_spider_class:
            mock_spider = Mock()
            mock_spider.items = []
            mock_spider.crawl = AsyncMock()
            mock_spider.get_root_error = Mock(return_value=None)
            mock_spider.get_stats = Mock(return_value={"requests": 5, "responses": 4})
            mock_spider_class.return_value = mock_spider

            result = await search_async_with_info(
                "https://example.com", include_stats=True
            )

            assert isinstance(result, SearchResult)
            assert result.stats is not None
            assert result.stats["requests"] == 5


class TestRootURLErrorTracking:
    """Test root URL error tracking in FeedsearchSpider."""

    @pytest.mark.asyncio
    async def test_spider_tracks_root_url_error_404(self):
        """Test that spider records HTTP 404 errors for root URLs."""
        from feedsearch_crawler.crawler import Request, Response
        from feedsearch_crawler.feed_spider import FeedsearchSpider

        spider = FeedsearchSpider(concurrency=1, total_timeout=0.5)
        root_url = URL("https://nonexistent.example.com")

        # Track this as a root URL
        spider._track_root_urls([root_url])

        # Create error request and response
        request = Request(url=root_url)
        response = Response(
            url=root_url,
            method="GET",
            encoding="utf-8",
            headers={},
            history=[],
            status_code=404,
        )

        # Call parse_response directly to trigger error handling
        async for _ in spider.parse_response(request, response):
            pass

        root_error = spider.get_root_error()
        assert root_error is not None
        assert root_error.error_type == ErrorType.HTTP_ERROR
        assert root_error.status_code == 404
        assert "404" in root_error.message

    @pytest.mark.asyncio
    async def test_spider_tracks_root_url_error_500(self):
        """Test that spider records HTTP 500 errors for root URLs."""
        from feedsearch_crawler.crawler import Request, Response
        from feedsearch_crawler.feed_spider import FeedsearchSpider

        spider = FeedsearchSpider(concurrency=1, total_timeout=0.5)
        root_url = URL("https://example.com")

        spider._track_root_urls([root_url])

        request = Request(url=root_url)
        response = Response(
            url=root_url,
            method="GET",
            encoding="utf-8",
            headers={},
            history=[],
            status_code=500,
        )

        async for _ in spider.parse_response(request, response):
            pass

        root_error = spider.get_root_error()
        assert root_error is not None
        assert root_error.error_type == ErrorType.HTTP_ERROR
        assert root_error.status_code is None  # Generic 500 doesn't include status_code

    @pytest.mark.asyncio
    async def test_spider_no_error_on_success(self):
        """Test that spider has no root_error on successful response."""
        from feedsearch_crawler.crawler import Request, Response
        from feedsearch_crawler.feed_spider import FeedsearchSpider

        spider = FeedsearchSpider(concurrency=1, total_timeout=0.5)
        root_url = URL("https://example.com")

        spider._track_root_urls([root_url])

        request = Request(url=root_url)
        response = Response(
            url=root_url,
            method="GET",
            encoding="utf-8",
            headers={},
            history=[],
            status_code=200,
            text="<html></html>",
        )

        async for _ in spider.parse_response(request, response):
            pass

        root_error = spider.get_root_error()
        assert root_error is None

    @pytest.mark.asyncio
    async def test_spider_no_error_for_discovered_url_failure(self):
        """Test that discovered URL failures don't create root_error."""
        from feedsearch_crawler.crawler import Request, Response
        from feedsearch_crawler.feed_spider import FeedsearchSpider

        spider = FeedsearchSpider(concurrency=1, total_timeout=0.5)
        root_url = URL("https://example.com")
        discovered_url = URL("https://example.com/feed.xml")

        # Only track the root URL
        spider._track_root_urls([root_url])

        # Create error for discovered URL (not root)
        request = Request(url=discovered_url)
        response = Response(
            url=discovered_url,
            method="GET",
            encoding="utf-8",
            headers={},
            history=[],
            status_code=404,
        )

        async for _ in spider.parse_response(request, response):
            pass

        # Should have no root error because the failing URL wasn't a root URL
        root_error = spider.get_root_error()
        assert root_error is None


class TestErrorTypePreservation:
    """Test that specific error types are preserved through downloader."""

    @pytest.mark.asyncio
    async def test_dns_error_type_preserved(self):
        """Test that DNS errors are categorized correctly."""
        from feedsearch_crawler.crawler import Request, Response
        from feedsearch_crawler.feed_spider import FeedsearchSpider

        spider = FeedsearchSpider(concurrency=1, total_timeout=0.5)
        root_url = URL("https://nonexistent.example.com")

        spider._track_root_urls([root_url])

        request = Request(url=root_url)
        response = Response(
            url=root_url,
            method="GET",
            encoding="utf-8",
            headers={},
            history=[],
            status_code=500,
            error_type=ErrorType.DNS_FAILURE,
        )

        async for _ in spider.parse_response(request, response):
            pass

        root_error = spider.get_root_error()
        assert root_error is not None
        assert root_error.error_type == ErrorType.DNS_FAILURE
        assert "DNS" in root_error.message

    @pytest.mark.asyncio
    async def test_ssl_error_type_preserved(self):
        """Test that SSL errors are categorized correctly."""
        from feedsearch_crawler.crawler import Request, Response
        from feedsearch_crawler.feed_spider import FeedsearchSpider

        spider = FeedsearchSpider(concurrency=1, total_timeout=0.5)
        root_url = URL("https://example.com")

        spider._track_root_urls([root_url])

        request = Request(url=root_url)
        response = Response(
            url=root_url,
            method="GET",
            encoding="utf-8",
            headers={},
            history=[],
            status_code=500,
            error_type=ErrorType.SSL_ERROR,
        )

        async for _ in spider.parse_response(request, response):
            pass

        root_error = spider.get_root_error()
        assert root_error is not None
        assert root_error.error_type == ErrorType.SSL_ERROR
        assert "SSL" in root_error.message

    @pytest.mark.asyncio
    async def test_timeout_error_type_preserved(self):
        """Test that timeout errors are categorized correctly."""
        from feedsearch_crawler.crawler import Request, Response
        from feedsearch_crawler.feed_spider import FeedsearchSpider

        spider = FeedsearchSpider(concurrency=1, total_timeout=0.5)
        root_url = URL("https://example.com")

        spider._track_root_urls([root_url])

        request = Request(url=root_url)
        response = Response(
            url=root_url,
            method="GET",
            encoding="utf-8",
            headers={},
            history=[],
            status_code=408,
            error_type=ErrorType.TIMEOUT,
        )

        async for _ in spider.parse_response(request, response):
            pass

        root_error = spider.get_root_error()
        assert root_error is not None
        assert root_error.error_type == ErrorType.TIMEOUT
        assert "timed out" in root_error.message.lower()

    @pytest.mark.asyncio
    async def test_connection_error_type_preserved(self):
        """Test that connection errors are categorized correctly."""
        from feedsearch_crawler.crawler import Request, Response
        from feedsearch_crawler.feed_spider import FeedsearchSpider

        spider = FeedsearchSpider(concurrency=1, total_timeout=0.5)
        root_url = URL("https://example.com")

        spider._track_root_urls([root_url])

        request = Request(url=root_url)
        response = Response(
            url=root_url,
            method="GET",
            encoding="utf-8",
            headers={},
            history=[],
            status_code=500,
            error_type=ErrorType.CONNECTION_ERROR,
        )

        async for _ in spider.parse_response(request, response):
            pass

        root_error = spider.get_root_error()
        assert root_error is not None
        assert root_error.error_type == ErrorType.CONNECTION_ERROR
        assert "connection" in root_error.message.lower()


class TestBackwardCompatibility:
    """Test backward compatibility with existing code patterns."""

    @patch("feedsearch_crawler.search_async")
    def test_existing_code_pattern_iteration(self, mock_search_async):
        """Test that existing code using iteration still works."""
        feeds = [
            FeedInfo(url=URL("https://example.com/feed1.xml")),
            FeedInfo(url=URL("https://example.com/feed2.xml")),
        ]
        mock_search_async.return_value = feeds

        with patch("asyncio.run", return_value=feeds):
            # Existing code pattern: for feed in search(...)
            feed_urls = []
            for feed in search("https://example.com"):
                feed_urls.append(str(feed.url))

            assert len(feed_urls) == 2
            assert "https://example.com/feed1.xml" in feed_urls

    @patch("feedsearch_crawler.search_async")
    def test_existing_code_pattern_if_check(self, mock_search_async):
        """Test that existing code using if check still works."""
        # Test with feeds
        feeds = [FeedInfo(url=URL("https://example.com/feed.xml"))]
        mock_search_async.return_value = feeds

        with patch("asyncio.run", return_value=feeds):
            result = search("https://example.com")
            # Existing code pattern: if feeds:
            if result:
                assert True
            else:
                assert False, "Should have feeds"

        # Test without feeds
        empty_feeds = []
        mock_search_async.return_value = empty_feeds

        with patch("asyncio.run", return_value=empty_feeds):
            result = search("https://example.com")
            # Existing code pattern: if not feeds:
            if not result:
                assert True
            else:
                assert False, "Should have no feeds"

    @patch("feedsearch_crawler.search_async")
    def test_existing_code_pattern_len_check(self, mock_search_async):
        """Test that existing code using len() still works."""
        feeds = [
            FeedInfo(url=URL("https://example.com/feed1.xml")),
            FeedInfo(url=URL("https://example.com/feed2.xml")),
        ]
        mock_search_async.return_value = feeds

        with patch("asyncio.run", return_value=feeds):
            result = search("https://example.com")
            # Existing code pattern: len(feeds)
            assert len(result) == 2

    @patch("feedsearch_crawler.search_async")
    def test_existing_code_pattern_indexing(self, mock_search_async):
        """Test that existing code using indexing still works."""
        feeds = [FeedInfo(url=URL("https://example.com/feed.xml"))]
        mock_search_async.return_value = feeds

        with patch("asyncio.run", return_value=feeds):
            result = search("https://example.com")
            # Existing code pattern: feeds[0]
            first_feed = result[0]
            assert isinstance(first_feed, FeedInfo)
            assert str(first_feed.url) == "https://example.com/feed.xml"

    @patch("feedsearch_crawler.search_async")
    def test_isinstance_check_works(self, mock_search_async):
        """Test that isinstance(result, list) works."""
        feeds = [FeedInfo(url=URL("https://example.com/feed.xml"))]
        mock_search_async.return_value = feeds

        with patch("asyncio.run", return_value=feeds):
            result = search("https://example.com")
            # Should be a real list
            assert isinstance(result, list)
