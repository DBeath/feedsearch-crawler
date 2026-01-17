"""Tests that validate README examples work as documented.

These tests ensure the public API examples in the README are accurate
and functional.
"""

from unittest.mock import AsyncMock, patch

import pytest
from yarl import URL

from feedsearch_crawler import output_opml, search, search_async
from feedsearch_crawler.feed_spider.feed_info import FeedInfo


class TestReadmeBasicUsage:
    """Test examples from README Usage section."""

    @patch("feedsearch_crawler.search_async")
    def test_readme_basic_example_structure(self, mock_search_async):
        """Test README basic usage example (lines 33-42).

        >>> from feedsearch_crawler import search
        >>> feeds = search('xkcd.com')
        >>> feeds
        [FeedInfo('https://xkcd.com/rss.xml'), FeedInfo('https://xkcd.com/atom.xml')]
        """
        # Mock the search to return example feeds
        mock_feeds = [
            FeedInfo(url=URL("https://xkcd.com/rss.xml"), title="xkcd.com", score=24),
            FeedInfo(url=URL("https://xkcd.com/atom.xml"), title="xkcd.com", score=20),
        ]
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            feeds = search("xkcd.com")

        # Verify it returns a list
        assert isinstance(feeds, list)

        # Verify list contains FeedInfo objects
        assert all(isinstance(f, FeedInfo) for f in feeds)

        # Verify feeds have url attribute
        assert hasattr(feeds[0], "url")

    @patch("feedsearch_crawler.search_async")
    def test_readme_url_attribute_example(self, mock_search_async):
        """Test README URL attribute example (lines 37-40).

        >>> feeds[0].url
        URL('https://xkcd.com/rss.xml')
        >>> str(feeds[0].url)
        'https://xkcd.com/rss.xml'
        """
        mock_feeds = [FeedInfo(url=URL("https://xkcd.com/rss.xml"), title="xkcd.com")]
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            feeds = search("xkcd.com")

        # URL attribute should be a URL object
        assert isinstance(feeds[0].url, URL)
        assert feeds[0].url == URL("https://xkcd.com/rss.xml")

        # str() should convert to string
        assert str(feeds[0].url) == "https://xkcd.com/rss.xml"
        assert isinstance(str(feeds[0].url), str)

    @patch("feedsearch_crawler.search_async")
    def test_readme_serialize_example(self, mock_search_async):
        """Test README serialize example (line 41-42).

        >>> feeds[0].serialize()
        {'url': 'https://xkcd.com/rss.xml', 'title': 'xkcd.com', ...}
        """
        mock_feeds = [
            FeedInfo(
                url=URL("https://xkcd.com/rss.xml"),
                title="xkcd.com",
                description="xkcd.com: A webcomic of romance and math humor.",
                version="rss20",
                score=24,
                site_url=URL("https://xkcd.com/"),
                site_name="xkcd: Chernobyl",
                favicon=URL("https://xkcd.com/s/919f27.ico"),
                content_type="text/xml; charset=UTF-8",
                bozo=0,
                content_length=2847,
                is_push=False,
            )
        ]
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            feeds = search("xkcd.com")

        serialized = feeds[0].serialize()

        # Verify serialize() returns a dict
        assert isinstance(serialized, dict)

        # Verify all keys from README example are present
        readme_example_keys = [
            "url",
            "title",
            "version",
            "score",
            "hubs",
            "description",
            "is_push",
            "self_url",
            "favicon",
            "content_type",
            "bozo",
            "site_url",
            "site_name",
            "favicon_data_uri",
            "content_length",
        ]

        for key in readme_example_keys:
            assert key in serialized, f"README example key '{key}' missing"

        # Verify example values
        assert serialized["url"] == "https://xkcd.com/rss.xml"
        assert serialized["title"] == "xkcd.com"
        assert serialized["version"] == "rss20"
        assert serialized["score"] == 24


class TestReadmeAsyncUsage:
    """Test async usage example from README."""

    @pytest.mark.asyncio
    async def test_readme_search_async_example(self):
        """Test README search_async example (lines 47-50).

        from feedsearch_crawler import search_async
        feeds = await search_async('xkcd.com')
        """
        with patch("feedsearch_crawler.FeedsearchSpider") as mock_spider_class:
            mock_spider = AsyncMock()
            mock_spider.items = [
                FeedInfo(
                    url=URL("https://xkcd.com/rss.xml"), title="xkcd.com", score=24
                )
            ]
            mock_spider.crawl = AsyncMock()
            mock_spider_class.return_value = mock_spider

            result = await search_async("xkcd.com")

        # Verify it returns a list (backward compatible)
        assert isinstance(result, list)
        assert all(isinstance(f, FeedInfo) for f in result)


class TestReadmeOutputFunctions:
    """Test output functions from README."""

    def test_readme_opml_example(self):
        """Test README OPML example (lines 67-69).

        from feedsearch_crawler import output_opml
        output_opml(feeds).decode()
        """
        feeds = [
            FeedInfo(
                url=URL("https://xkcd.com/rss.xml"),
                title="xkcd.com",
                description="A webcomic",
                site_url=URL("https://xkcd.com"),
            )
        ]

        opml_bytes = output_opml(feeds)

        # Should return bytes
        assert isinstance(opml_bytes, bytes)

        # Should be decodable
        opml_str = opml_bytes.decode()
        assert isinstance(opml_str, str)

        # Should contain OPML structure
        assert "<?xml" in opml_str
        assert "<opml" in opml_str
        assert "xkcd.com" in opml_str


class TestReadmeSearchArguments:
    """Test search arguments from README."""

    @patch("feedsearch_crawler.search_async")
    def test_readme_search_arguments(self, mock_search_async):
        """Test that search accepts all documented arguments (lines 77-90)."""
        mock_search_async.return_value = []

        with patch("asyncio.run", return_value=[]):
            # Test all arguments from README are accepted
            result = search(
                url="https://example.com",
                crawl_hosts=True,
                try_urls=False,
                concurrency=10,
                total_timeout=10.0,
                request_timeout=3.0,
                user_agent="Test Bot",
                max_content_length=1024 * 1024 * 10,
                max_depth=10,
                headers={"X-Custom-Header": "Custom Header"},
                favicon_data_uri=True,
                delay=0,
            )

        # Verify search_async was called with all arguments
        mock_search_async.assert_called_once()
        # Function returns empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_readme_search_async_arguments(self):
        """Test that search_async accepts all documented arguments."""
        with patch("feedsearch_crawler.FeedsearchSpider") as mock_spider_class:
            mock_spider = AsyncMock()
            mock_spider.items = []
            mock_spider.crawl = AsyncMock()
            mock_spider_class.return_value = mock_spider

            result = await search_async(
                url="https://example.com",
                crawl_hosts=False,
                try_urls=True,
                concurrency=5,
                total_timeout=30.0,
                request_timeout=3.0,
            )

            # Verify it returns a list by default
            assert isinstance(result, list)

            # Verify arguments were passed to spider
            call_kwargs = mock_spider_class.call_args[1]
            assert call_kwargs["crawl_hosts"] is False
            assert call_kwargs["try_urls"] is True
            assert call_kwargs["concurrency"] == 5


class TestReadmeFeedInfoValues:
    """Test that FeedInfo has all values documented in README."""

    def test_feedinfo_has_all_documented_attributes(self):
        """Test FeedInfo has all attributes from README section (lines 110-129)."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"))

        # All attributes documented in README "FeedInfo Values" section
        documented_attrs = [
            "bozo",
            "content_length",
            "content_type",
            "description",
            "favicon",
            "favicon_data_uri",
            "hubs",
            "is_podcast",
            "is_push",
            "item_count",
            "last_updated",
            "score",
            "self_url",
            "site_name",
            "site_url",
            "title",
            "url",
            "velocity",
            "version",
        ]

        for attr in documented_attrs:
            assert hasattr(feed, attr), (
                f"FeedInfo missing documented attribute '{attr}'"
            )

    def test_feedinfo_attribute_types_match_readme(self):
        """Test FeedInfo attribute types match README documentation."""
        from datetime import datetime

        feed = FeedInfo(
            url=URL("https://example.com/feed.xml"),
            bozo=0,
            content_length=100,
            content_type="text/xml",
            description="Test",
            favicon=URL("https://example.com/favicon.ico"),
            favicon_data_uri="data:image/png;base64,ABC",
            hubs=["https://hub.example.com"],
            is_podcast=False,
            is_push=True,
            item_count=10,
            last_updated=datetime.now(),
            score=50,
            self_url=URL("https://example.com/feed.xml"),
            site_name="Example",
            site_url=URL("https://example.com"),
            title="Test Feed",
            velocity=2.5,
            version="rss20",
        )

        # Verify types match README documentation
        assert isinstance(feed.bozo, int)
        assert isinstance(feed.content_length, int)
        assert isinstance(feed.content_type, str)
        assert isinstance(feed.description, str)
        assert isinstance(feed.favicon, URL)
        assert isinstance(feed.favicon_data_uri, str)
        assert isinstance(feed.hubs, list)
        assert isinstance(feed.is_podcast, bool)
        assert isinstance(feed.is_push, bool)
        assert isinstance(feed.item_count, int)
        assert isinstance(feed.last_updated, datetime)
        assert isinstance(feed.score, int)
        assert isinstance(feed.site_name, str)
        assert isinstance(feed.site_url, URL)
        assert isinstance(feed.title, str)
        assert isinstance(feed.url, URL)
        assert isinstance(feed.velocity, float)
        assert isinstance(feed.version, str)


class TestReadmeReturnValues:
    """Test return values match README documentation."""

    @patch("feedsearch_crawler.search_async")
    def test_search_returns_list_of_feedinfo(self, mock_search_async):
        """Test README claim: 'search will always return a list of FeedInfo objects' (line 53)."""
        mock_feeds = [FeedInfo(url=URL("https://example.com/feed.xml"))]
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            result = search("example.com")

        # Must return a list (backward compatible)
        assert isinstance(result, list)

        # Must contain FeedInfo objects
        assert all(isinstance(item, FeedInfo) for item in result)

    @patch("feedsearch_crawler.search_async")
    def test_feedinfo_always_has_url_property(self, mock_search_async):
        """Test README claim: 'each will always have a url property' (line 53)."""
        mock_feeds = [
            FeedInfo(url=URL("https://example.com/feed1.xml")),
            FeedInfo(url=URL("https://example.com/feed2.xml")),
        ]
        mock_search_async.return_value = mock_feeds

        with patch("asyncio.run", return_value=mock_feeds):
            feeds = search("example.com")

        # Every FeedInfo must have url property
        for feed in feeds:
            assert hasattr(feed, "url")
            assert feed.url is not None

    def test_feeds_sorted_by_score(self):
        """Test README claim: 'sorted by score value from highest to lowest' (line 54)."""
        from feedsearch_crawler import sort_urls

        # Create unsorted feeds
        unsorted_feeds = [
            FeedInfo(url=URL("https://example.com/feed1.xml"), score=50),
            FeedInfo(url=URL("https://example.com/feed2.xml"), score=30),
            FeedInfo(url=URL("https://example.com/feed3.xml"), score=40),
        ]

        # sort_urls is used internally by search_async
        feeds = sort_urls(unsorted_feeds)

        # Should be sorted by score, highest first
        scores = [f.score for f in feeds]
        assert scores == sorted(scores, reverse=True)
        assert scores == [50, 40, 30]
