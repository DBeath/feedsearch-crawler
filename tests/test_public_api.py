"""Tests for the public API in __init__.py."""

from unittest.mock import AsyncMock, patch

import pytest

from feedsearch_crawler import search, search_async, sort_urls, output_opml
from feedsearch_crawler.feed_spider.feed_info import FeedInfo


class TestSearchFunction:
    """Test the synchronous search function."""

    @patch("feedsearch_crawler.search_async")
    def test_search_single_url_string(self, mock_search_async):
        """Test search with a single URL string."""
        mock_feeds = [
            FeedInfo(url="https://example.com/feed.xml", title="Test Feed", score=10)
        ]
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            result = search("https://example.com")

        assert result == mock_feeds

    @patch("feedsearch_crawler.search_async")
    def test_search_with_try_urls(self, mock_search_async):
        """Test search with try_urls parameter."""
        mock_feeds = [
            FeedInfo(url="https://example.com/feed.xml", title="Test Feed", score=10)
        ]
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            result = search("https://example.com", try_urls=True)

        assert result == mock_feeds

    @patch("feedsearch_crawler.search_async")
    def test_search_list_of_urls(self, mock_search_async):
        """Test search with a list of URLs."""
        mock_feeds = [
            FeedInfo(url="https://example.com/feed.xml", title="Feed 1", score=10),
            FeedInfo(url="https://example.org/rss.xml", title="Feed 2", score=8),
        ]
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            result = search(["https://example.com", "https://example.org"])

        assert len(result) == 2


class TestSearchAsyncFunction:
    """Test the asynchronous search function."""

    @pytest.mark.asyncio
    async def test_search_async_single_url(self):
        """Test async search with a single URL."""
        with patch("feedsearch_crawler.FeedsearchSpider") as mock_spider_class:
            mock_spider = AsyncMock()
            mock_spider.items = [
                FeedInfo(url="https://example.com/feed.xml", title="Test", score=10)
            ]
            mock_spider.crawl = AsyncMock()
            mock_spider_class.return_value = mock_spider

            result = await search_async("https://example.com")

            assert len(result) == 1
            assert result[0].url == "https://example.com/feed.xml"
            mock_spider.crawl.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_async_with_kwargs(self):
        """Test async search with additional keyword arguments."""
        with patch("feedsearch_crawler.FeedsearchSpider") as mock_spider_class:
            mock_spider = AsyncMock()
            mock_spider.items = []
            mock_spider.crawl = AsyncMock()
            mock_spider_class.return_value = mock_spider

            await search_async(
                "https://example.com", try_urls=True, concurrency=5, total_timeout=10.0
            )

            mock_spider_class.assert_called_once()
            call_kwargs = mock_spider_class.call_args[1]
            assert call_kwargs["try_urls"] is True
            assert call_kwargs["concurrency"] == 5
            assert call_kwargs["total_timeout"] == 10.0


class TestSortUrls:
    """Test the sort_urls function."""

    def test_sort_urls_by_score(self):
        """Test that feeds are sorted by score in descending order."""
        feeds = [
            FeedInfo(url="https://example.com/feed1.xml", score=5),
            FeedInfo(url="https://example.com/feed2.xml", score=10),
            FeedInfo(url="https://example.com/feed3.xml", score=7),
        ]

        sorted_feeds = sort_urls(feeds)

        assert len(sorted_feeds) == 3
        assert sorted_feeds[0].score == 10
        assert sorted_feeds[1].score == 7
        assert sorted_feeds[2].score == 5

    def test_sort_urls_removes_duplicates(self):
        """Test that duplicate feeds are removed."""
        feeds = [
            FeedInfo(url="https://example.com/feed.xml", score=10),
            FeedInfo(url="https://example.com/feed.xml", score=10),  # Duplicate
            FeedInfo(url="https://example.org/rss.xml", score=8),
        ]

        sorted_feeds = sort_urls(feeds)

        assert len(sorted_feeds) == 2

    def test_sort_urls_filters_non_feedinfo(self):
        """Test that non-FeedInfo objects are filtered out."""
        feeds = [
            FeedInfo(url="https://example.com/feed.xml", score=10),
            "not a feed",  # Should be filtered
            {"url": "dict"},  # Should be filtered
            FeedInfo(url="https://example.org/rss.xml", score=8),
        ]

        sorted_feeds = sort_urls(feeds)

        assert len(sorted_feeds) == 2
        assert all(isinstance(f, FeedInfo) for f in sorted_feeds)

    def test_sort_urls_empty_list(self):
        """Test sorting an empty list."""
        sorted_feeds = sort_urls([])
        assert sorted_feeds == []


class TestOutputOpml:
    """Test the output_opml function."""

    def test_output_opml_basic(self):
        """Test basic OPML output generation."""
        feeds = [
            FeedInfo(
                url="https://example.com/feed.xml",
                title="Test Feed",
                description="A test feed",
                site_url="https://example.com",
                version="rss20",
            )
        ]

        opml = output_opml(feeds)

        assert isinstance(opml, bytes)
        assert b'<opml version="2.0">' in opml
        assert b"<title>Feeds</title>" in opml
        assert b"https://example.com/feed.xml" in opml
        assert b"Test Feed" in opml

    def test_output_opml_multiple_feeds(self):
        """Test OPML output with multiple feeds."""
        feeds = [
            FeedInfo(url="https://example.com/feed1.xml", title="Feed 1"),
            FeedInfo(url="https://example.org/feed2.xml", title="Feed 2"),
            FeedInfo(url="https://test.com/feed3.xml", title="Feed 3"),
        ]

        opml = output_opml(feeds)

        assert b"Feed 1" in opml
        assert b"Feed 2" in opml
        assert b"Feed 3" in opml

    def test_output_opml_with_all_fields(self):
        """Test OPML output with all FeedInfo fields populated."""
        feeds = [
            FeedInfo(
                url="https://example.com/feed.xml",
                title="Complete Feed",
                description="Feed description",
                site_url="https://example.com",
                version="atom10",
            )
        ]

        opml = output_opml(feeds)

        assert b"Complete Feed" in opml
        assert b"Feed description" in opml
        assert b"https://example.com" in opml
        assert b"atom10" in opml

    def test_output_opml_missing_optional_fields(self):
        """Test OPML output when optional fields are missing."""
        feeds = [
            FeedInfo(url="https://example.com/feed.xml")  # Only URL
        ]

        opml = output_opml(feeds)

        assert isinstance(opml, bytes)
        assert b"https://example.com/feed.xml" in opml

    def test_output_opml_skips_feeds_without_url(self):
        """Test that feeds without URL are skipped."""
        feeds = [
            FeedInfo(url="https://example.com/feed.xml", title="Valid Feed"),
            FeedInfo(url=None, title="Invalid Feed"),  # No URL
            FeedInfo(url="", title="Empty URL"),  # Empty URL
        ]

        opml = output_opml(feeds)

        assert b"Valid Feed" in opml
        assert b"Invalid Feed" not in opml
        assert b"Empty URL" not in opml

    def test_output_opml_empty_list(self):
        """Test OPML output with empty feed list."""
        opml = output_opml([])

        assert isinstance(opml, bytes)
        assert b'<opml version="2.0">' in opml
        assert b"<title>Feeds</title>" in opml
        # Should have structure but no feed entries

    def test_output_opml_xml_structure(self):
        """Test that OPML has correct XML structure."""
        feeds = [FeedInfo(url="https://example.com/feed.xml", title="Test")]

        opml = output_opml(feeds)

        # Check for required OPML structure elements
        assert b"<opml" in opml
        assert b"<head>" in opml
        assert b"<body>" in opml
        assert b"<outline" in opml
        assert b'type="rss"' in opml
        assert b"xmlUrl=" in opml
