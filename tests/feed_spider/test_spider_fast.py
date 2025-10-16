"""Fast unit tests for FeedsearchSpider components."""

import pytest

from feedsearch_crawler.feed_spider.feed_info import FeedInfo
from feedsearch_crawler.feed_spider.spider import FeedsearchSpider


class TestFeedsearchSpiderFast:
    """Fast unit tests for spider components."""

    def test_spider_initialization(self):
        """Test spider initialization with default parameters."""
        spider = FeedsearchSpider()

        assert spider.concurrency > 0
        assert isinstance(spider.site_metas, set)
        assert isinstance(spider.favicons, dict)
        assert isinstance(spider.feeds_seen, dict)

    @pytest.mark.asyncio
    async def test_html_parsing(self, sample_html_with_feeds):
        """Test HTML parsing capability."""
        spider = FeedsearchSpider()

        # Test that HTML can be parsed without errors
        soup = await spider.parse_response_content(sample_html_with_feeds)
        assert soup is not None

        # Verify feed links are found
        feed_links = soup.find_all("link", rel="alternate")
        assert len(feed_links) >= 3

    def test_feed_info_creation(self):
        """Test FeedInfo object creation."""
        feed_info = FeedInfo(
            url="https://example.com/feed.xml",
            title="Test Feed",
            description="Test Description",
        )

        assert feed_info.url == "https://example.com/feed.xml"
        assert feed_info.title == "Test Feed"
        assert feed_info.description == "Test Description"

    def test_feed_info_equality(self):
        """Test FeedInfo equality comparison."""
        feed1 = FeedInfo(url="https://example.com/feed.xml", title="Feed 1")
        feed2 = FeedInfo(url="https://example.com/feed.xml", title="Feed 2")
        feed3 = FeedInfo(url="https://different.com/feed.xml", title="Feed 3")

        # Same URL should be equal
        assert feed1 == feed2
        # Different URL should not be equal
        assert feed1 != feed3

    def test_feed_info_hashing(self):
        """Test FeedInfo can be hashed (for sets)."""
        feed = FeedInfo(url="https://example.com/feed.xml", title="Test")

        # Should be hashable
        feed_set = {feed}
        assert len(feed_set) == 1

    @pytest.mark.asyncio
    async def test_spider_process_item(self):
        """Test spider can process items."""
        spider = FeedsearchSpider()
        feed_info = FeedInfo(url="https://example.com/feed.xml", title="Test")

        # Should not raise an error
        await spider.process_item(feed_info)
        assert len(spider.items) == 1

    def test_spider_tag_has_href(self):
        """Test tag filtering method."""
        spider = FeedsearchSpider()

        # Mock tag with href
        class MockTag:
            def __init__(self, has_href=True):
                self.attrs = {"href": "/test"} if has_href else {}

            def has_attr(self, attr):
                return attr in self.attrs

        # Should accept tags with href
        assert spider.tag_has_href(MockTag(True)) is True
        # Should reject tags without href
        assert spider.tag_has_href(MockTag(False)) is False

    def test_spider_configuration_options(self):
        """Test spider configuration options."""
        spider = FeedsearchSpider(
            concurrency=5,
            try_urls=False,
            favicon_data_uri=True,
            crawl_hosts=False,
            full_crawl=True,
        )

        assert spider.concurrency == 5
        assert spider.try_urls is False
        assert spider.favicon_data_uri is True
        assert spider.crawl_hosts is False
        assert spider.full_crawl is True
