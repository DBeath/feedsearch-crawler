"""Integration tests for FeedsearchSpider."""

import pytest
from yarl import URL

from feedsearch_crawler.crawler import Request, Response
from feedsearch_crawler.feed_spider.favicon import Favicon
from feedsearch_crawler.feed_spider.feed_info import FeedInfo
from feedsearch_crawler.feed_spider.site_meta import SiteMeta
from feedsearch_crawler.feed_spider.spider import FeedsearchSpider


@pytest.mark.asyncio
class TestFeedsearchSpiderBasics:
    """Basic spider functionality tests."""

    async def test_spider_initialization_with_options(self):
        """Test spider initialization with various options."""
        spider = FeedsearchSpider(
            concurrency=5,
            try_urls=True,
            favicon_data_uri=False,
            full_crawl=True,
            crawl_hosts=False,
            total_timeout=1.0,
        )

        assert spider.concurrency == 5
        assert spider.try_urls is True
        assert spider.favicon_data_uri is False
        assert spider.full_crawl is True
        assert spider.crawl_hosts is False
        assert spider.site_meta_processor is not None
        assert spider.feed_info_parser is not None
        assert isinstance(spider.site_metas, set)
        assert isinstance(spider.favicons, dict)

    async def test_spider_parse_non_ok_response(self):
        """Test spider handling of non-OK responses."""
        spider = FeedsearchSpider(concurrency=1, total_timeout=1.0)

        request = Request(url=URL("https://example.com/notfound"))
        response = Response(
            url=URL("https://example.com/notfound"),
            method="GET",
            status_code=404,
            text="Not Found",
            history=[],
        )

        items = []
        async for item in spider.parse_response(request, response):
            items.append(item)

        # Should yield nothing for non-OK response
        assert len(items) == 0

    async def test_spider_parse_response_without_text(self):
        """Test spider handling of responses without text."""
        spider = FeedsearchSpider(concurrency=1, total_timeout=1.0)

        request = Request(url=URL("https://example.com/binary"))
        response = Response(
            url=URL("https://example.com/binary"),
            method="GET",
            status_code=200,
            data=b"binary data",
            text=None,
            history=[],
        )

        items = []
        async for item in spider.parse_response(request, response):
            items.append(item)

        # Should handle gracefully
        assert isinstance(items, list)

    async def test_spider_process_feed_item(self):
        """Test spider processing FeedInfo items."""
        spider = FeedsearchSpider(concurrency=1, total_timeout=1.0)

        feed = FeedInfo(url="https://example.com/feed.xml")
        await spider.process_item(feed)

        assert feed in spider.items

    async def test_spider_process_site_meta_item(self):
        """Test spider processing SiteMeta items."""
        spider = FeedsearchSpider(concurrency=1, total_timeout=1.0)

        site_meta = SiteMeta(url=URL("https://example.com"))
        await spider.process_item(site_meta)

        assert site_meta in spider.site_metas

    async def test_spider_process_favicon_item(self):
        """Test spider processing Favicon items."""
        spider = FeedsearchSpider(concurrency=1, total_timeout=1.0)

        favicon = Favicon(url=URL("https://example.com/favicon.ico"))
        await spider.process_item(favicon)

        assert favicon.url in spider.favicons

    async def test_spider_add_favicon(self):
        """Test adding favicons to spider."""
        spider = FeedsearchSpider(concurrency=1, total_timeout=1.0)

        favicon1 = Favicon(url=URL("https://example.com/favicon.ico"))
        favicon1.data_uri = "data:image/png;base64,test"
        spider.add_favicon(favicon1)

        assert spider.favicons[favicon1.url].data_uri == "data:image/png;base64,test"

        # Adding same favicon without data_uri should not replace existing
        favicon2 = Favicon(url=URL("https://example.com/favicon.ico"))
        spider.add_favicon(favicon2)

        assert spider.favicons[favicon1.url].data_uri == "data:image/png;base64,test"

    async def test_spider_parse_html(self):
        """Test spider HTML parsing with parse_xml method.

        Note: parse_xml() uses html.parser intentionally because it parses
        both HTML pages (to extract links) and needs to handle XML gracefully.
        Actual feed XML is parsed by FeedInfoParser using feedparser.
        """
        spider = FeedsearchSpider(concurrency=1, total_timeout=1.0)

        html_text = """<html>
        <body>
            <a href="/feed.xml">Feed</a>
        </body>
        </html>"""

        result = await spider.parse_response_content(html_text)

        assert result is not None
        # BeautifulSoup parses it, so we can check it's a BS object
        assert hasattr(result, "name")
        # Should find the link
        link = result.find("a")
        assert link is not None
        assert link.get("href") == "/feed.xml"

    async def test_spider_populate_feed_site_meta(self):
        """Test post-crawl callback that populates feed metadata."""
        spider = FeedsearchSpider(concurrency=1, total_timeout=1.0)

        # Create test data
        site_meta = SiteMeta(url=URL("https://example.com"))
        site_meta.site_name = "Example Site"
        site_meta.site_url = URL("https://example.com")
        site_meta.host = "example.com"
        favicon = Favicon(url=URL("https://example.com/favicon.ico"))
        site_meta.favicons = [favicon]

        spider.site_metas.add(site_meta)
        spider.favicons[favicon.url] = favicon

        feed = FeedInfo(url=URL("https://example.com/feed.xml"))
        feed.site_url = URL("https://example.com")
        spider.items.add(feed)

        # Run post-crawl callback
        await spider.populate_feed_site_meta()

        # Check that feed was populated with site metadata
        assert feed.site_name == "Example Site"
        # Favicon gets populated if feed has a favicon set
        # This test focuses on site_name being populated

    async def test_spider_default_favicon_data_uri_enabled(self):
        """Test spider has favicon_data_uri enabled by default."""
        spider = FeedsearchSpider(concurrency=1, total_timeout=1.0)
        assert spider.favicon_data_uri is True

    async def test_spider_default_full_crawl_disabled(self):
        """Test spider has full_crawl disabled by default."""
        spider = FeedsearchSpider(concurrency=1, total_timeout=1.0)
        assert spider.full_crawl is False

    async def test_spider_default_crawl_hosts_enabled(self):
        """Test spider has crawl_hosts enabled by default."""
        spider = FeedsearchSpider(concurrency=1, total_timeout=1.0)
        assert spider.crawl_hosts is True

    async def test_spider_duplicate_filter_class(self):
        """Test spider uses NoQueryDupeFilter."""
        spider = FeedsearchSpider(concurrency=1, total_timeout=1.0)
        from feedsearch_crawler.feed_spider.dupefilter import NoQueryDupeFilter

        assert spider.duplicate_filter_class == NoQueryDupeFilter

    async def test_spider_htmlparser_setting(self):
        """Test spider HTML parser setting."""
        spider = FeedsearchSpider(concurrency=1, total_timeout=1.0)
        assert spider.htmlparser == "html.parser"
