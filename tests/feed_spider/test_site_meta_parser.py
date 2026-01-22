"""Comprehensive tests for SiteMetaParser - HTML metadata and favicon extraction."""

import pytest
from bs4 import BeautifulSoup
from yarl import URL

from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
from feedsearch_crawler.feed_spider.site_meta import SiteMeta
from feedsearch_crawler.feed_spider.site_meta_parser import SiteMetaParser
from feedsearch_crawler.feed_spider.spider import FeedsearchSpider


@pytest.fixture
def site_meta_parser():
    """Create a SiteMetaParser instance."""
    spider = FeedsearchSpider(concurrency=2, favicon_data_uri=False)
    parser = SiteMetaParser(crawler=spider)
    return parser


@pytest.fixture
def sample_html_with_metadata():
    """Sample HTML with various metadata."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Example Website</title>
    <link rel="canonical" href="https://example.com/" />
    <link rel="icon" href="/favicon.ico" />
    <link rel="shortcut icon" href="/shortcut.ico" />
    <meta property="og:site_name" content="Example Site" />
    <meta property="og:url" content="https://example.com" />
    <meta property="og:title" content="Example Title" />
    <meta name="twitter:app:name:iphone" content="Example App" />
</head>
<body>
    <h1>Example Site</h1>
</body>
</html>"""


class TestSiteMetaParserInitialization:
    """Test site metadata parser initialization."""

    @pytest.mark.asyncio
    async def test_parse_item_basic(self, site_meta_parser, sample_html_with_metadata):
        """Test basic site metadata parsing."""
        request = Request(url=URL("https://example.com"))

        # Create parser for HTML
        async def mock_parser(text):
            return BeautifulSoup(text, "html.parser")

        response = Response(
            url=URL("https://example.com"),
            method="GET",
            text=sample_html_with_metadata,
            xml_parser=mock_parser,
            history=[URL("https://example.com")],
        )

        items = []
        async for item in site_meta_parser.parse_item(request, response):
            items.append(item)

        # Should yield SiteMeta and possibly Favicons
        site_metas = [i for i in items if isinstance(i, SiteMeta)]
        assert len(site_metas) >= 1

    @pytest.mark.asyncio
    async def test_parse_item_no_xml(self, site_meta_parser):
        """Test handling when XML parsing fails."""
        request = Request(url=URL("https://example.com"))
        response = Response(
            url=URL("https://example.com"),
            method="GET",
            text="",
            xml_parser=None,
            history=[URL("https://example.com")],
        )

        items = []
        async for item in site_meta_parser.parse_item(request, response):
            items.append(item)

        # Should return nothing when XML parsing fails
        assert len(items) == 0


class TestFindSiteURL:
    """Test finding canonical site URL."""

    def test_find_site_url_canonical(self, site_meta_parser):
        """Test finding site URL from canonical link."""
        html = """<html><head>
            <link rel="canonical" href="https://example.com/page" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")
        url = URL("https://example.com/different")

        result = site_meta_parser.find_site_url(soup, url)

        assert result == URL("https://example.com")

    def test_find_site_url_og_url(self, site_meta_parser):
        """Test finding site URL from og:url meta tag."""
        html = """<html><head>
            <meta property="og:url" content="https://example.com/" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")
        url = URL("https://test.com")

        result = site_meta_parser.find_site_url(soup, url)

        assert result == URL("https://example.com")

    def test_find_site_url_canonical_slash(self, site_meta_parser):
        """Test handling of canonical with just slash."""
        html = """<html><head>
            <link rel="canonical" href="/" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")
        url = URL("https://example.com/page")

        result = site_meta_parser.find_site_url(soup, url)

        # Should return the current URL when canonical is just "/"
        assert result == url

    def test_find_site_url_fallback_to_origin(self, site_meta_parser):
        """Test fallback to URL origin when no metadata found."""
        html = """<html><head><title>Test</title></head></html>"""
        soup = BeautifulSoup(html, "html.parser")
        url = URL("https://example.com/some/deep/path")

        result = site_meta_parser.find_site_url(soup, url)

        assert result == URL("https://example.com")

    def test_find_site_url_invalid_canonical(self, site_meta_parser):
        """Test handling of invalid canonical URL."""
        html = """<html><head>
            <link rel="canonical" href="not-a-valid-url" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")
        url = URL("https://example.com")

        result = site_meta_parser.find_site_url(soup, url)

        # Should fallback to origin on error
        assert result == URL("https://example.com")


class TestFindSiteName:
    """Test finding site name from metadata."""

    def test_find_site_name_og_site_name(self, site_meta_parser):
        """Test finding site name from og:site_name."""
        html = """<html><head>
            <meta property="og:site_name" content="Example Site" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")

        result = site_meta_parser.find_site_name(soup)

        assert result == "Example Site"

    def test_find_site_name_og_title(self, site_meta_parser):
        """Test finding site name from og:title."""
        html = """<html><head>
            <meta property="og:title" content="Example Title" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")

        result = site_meta_parser.find_site_name(soup)

        assert result == "Example Title"

    def test_find_site_name_application_name(self, site_meta_parser):
        """Test finding site name from application:name."""
        html = """<html><head>
            <meta property="application:name" content="App Name" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")

        result = site_meta_parser.find_site_name(soup)

        assert result == "App Name"

    def test_find_site_name_twitter_app(self, site_meta_parser):
        """Test finding site name from Twitter app meta."""
        html = """<html><head>
            <meta property="twitter:app:name:iphone" content="Twitter App" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")

        result = site_meta_parser.find_site_name(soup)

        assert result == "Twitter App"

    def test_find_site_name_title_fallback(self, site_meta_parser):
        """Test fallback to title tag."""
        html = """<html><head>
            <title>Page Title</title>
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")

        result = site_meta_parser.find_site_name(soup)

        assert result == "Page Title"

    def test_find_site_name_priority_order(self, site_meta_parser):
        """Test that og:site_name takes priority."""
        html = """<html><head>
            <meta property="og:site_name" content="OG Site Name" />
            <meta property="og:title" content="OG Title" />
            <title>Title Tag</title>
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")

        result = site_meta_parser.find_site_name(soup)

        # Should return first match (og:site_name)
        assert result == "OG Site Name"

    def test_find_site_name_empty_when_none(self, site_meta_parser):
        """Test empty string returned when no name found."""
        html = """<html><head></head></html>"""
        soup = BeautifulSoup(html, "html.parser")

        result = site_meta_parser.find_site_name(soup)

        assert result == ""


class TestFindSiteIconURLs:
    """Test finding favicon URLs."""

    def test_find_site_icon_favicon_ico(self, site_meta_parser):
        """Test default favicon.ico is always included."""
        html = """<html><head></head></html>"""
        soup = BeautifulSoup(html, "html.parser")
        url = URL("https://example.com/page")
        host = "example.com"

        result = site_meta_parser.find_site_icon_urls(soup, url, host)

        # Should always include favicon.ico as fallback
        assert any(icon.url.path.endswith("/favicon.ico") for icon in result)

    def test_find_site_icon_link_rel_icon(self, site_meta_parser):
        """Test finding icon from link rel=icon."""
        html = """<html><head>
            <link rel="icon" href="/custom-icon.png" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")
        url = URL("https://example.com")
        host = "example.com"

        result = site_meta_parser.find_site_icon_urls(soup, url, host)

        assert any(icon.url.path.endswith("/custom-icon.png") for icon in result)

    def test_find_site_icon_shortcut_icon(self, site_meta_parser):
        """Test finding shortcut icon."""
        html = """<html><head>
            <link rel="shortcut icon" href="/shortcut.ico" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")
        url = URL("https://example.com")
        host = "example.com"

        result = site_meta_parser.find_site_icon_urls(soup, url, host)

        assert any(icon.url.path.endswith("/shortcut.ico") for icon in result)

    def test_find_site_icon_priority_ordering(self, site_meta_parser):
        """Test that icons are sorted by priority."""
        html = """<html><head>
            <link rel="icon" href="/icon.png" />
            <link rel="shortcut icon" href="/shortcut.ico" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")
        url = URL("https://example.com")
        host = "example.com"

        result = site_meta_parser.find_site_icon_urls(soup, url, host)

        # Shortcut icon should have priority 1 (highest)
        assert result[0].rel == "shortcut icon"

    def test_find_site_icon_relative_url(self, site_meta_parser):
        """Test handling of relative icon URLs."""
        html = """<html><head>
            <link rel="icon" href="/images/icon.png" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")
        url = URL("https://example.com/page")
        host = "example.com"

        result = site_meta_parser.find_site_icon_urls(soup, url, host)

        # Should join relative URL with base
        icons_with_path = [
            icon for icon in result if icon.url.path.endswith("/images/icon.png")
        ]
        assert len(icons_with_path) > 0

    def test_find_site_icon_absolute_url(self, site_meta_parser):
        """Test handling of absolute icon URLs."""
        html = """<html><head>
            <link rel="icon" href="https://cdn.example.com/icon.png" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")
        url = URL("https://example.com")
        host = "example.com"

        result = site_meta_parser.find_site_icon_urls(soup, url, host)

        assert any(icon.url.host == "cdn.example.com" for icon in result)

    def test_find_site_icon_empty_href(self, site_meta_parser):
        """Test handling of link with no href."""
        html = """<html><head>
            <link rel="icon" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")
        url = URL("https://example.com")
        host = "example.com"

        result = site_meta_parser.find_site_icon_urls(soup, url, host)

        # Should still return favicon.ico as fallback
        assert len(result) >= 1

    def test_find_site_icon_site_host_assignment(self, site_meta_parser):
        """Test that site_host is correctly assigned to icons."""
        html = """<html><head>
            <link rel="icon" href="/icon.png" />
        </head></html>"""
        soup = BeautifulSoup(html, "html.parser")
        url = URL("https://example.com")
        host = "example.com"

        result = site_meta_parser.find_site_icon_urls(soup, url, host)

        # All icons should have the site_host
        assert all(icon.site_host == host for icon in result)


class TestSiteMetaIntegration:
    """Test complete site metadata extraction scenarios."""

    @pytest.mark.asyncio
    async def test_complete_metadata_extraction(self, site_meta_parser):
        """Test extraction of all metadata together."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Example Site</title>
    <link rel="canonical" href="https://example.com/" />
    <link rel="icon" href="/favicon.png" />
    <meta property="og:site_name" content="Example" />
</head>
<body>Content</body>
</html>"""

        async def mock_parser(text):
            return BeautifulSoup(text, "html.parser")

        request = Request(url=URL("https://example.com"))
        response = Response(
            url=URL("https://example.com"),
            method="GET",
            text=html,
            xml_parser=mock_parser,
            history=[URL("https://example.com")],
        )

        items = []
        async for item in site_meta_parser.parse_item(request, response):
            items.append(item)

        site_metas = [i for i in items if isinstance(i, SiteMeta)]
        assert len(site_metas) >= 1

        site_meta = site_metas[0]
        assert site_meta.site_name == "Example"
        assert len(site_meta.possible_icons) > 0

    @pytest.mark.asyncio
    async def test_minimal_html(self, site_meta_parser):
        """Test handling of minimal HTML."""
        html = """<html><head><title>Test</title></head><body></body></html>"""

        async def mock_parser(text):
            return BeautifulSoup(text, "html.parser")

        request = Request(url=URL("https://example.com"))
        response = Response(
            url=URL("https://example.com"),
            method="GET",
            text=html,
            xml_parser=mock_parser,
            history=[URL("https://example.com")],
        )

        items = []
        async for item in site_meta_parser.parse_item(request, response):
            items.append(item)

        # Should still extract some metadata
        site_metas = [i for i in items if isinstance(i, SiteMeta)]
        assert len(site_metas) >= 1

    @pytest.mark.asyncio
    async def test_favicon_data_uri_mode(self):
        """Test favicon handling with data URI mode enabled."""
        spider = FeedsearchSpider(concurrency=2, favicon_data_uri=True)
        parser = SiteMetaParser(crawler=spider)

        html = """<html><head>
            <link rel="icon" href="/icon.png" />
        </head></html>"""

        async def mock_parser(text):
            return BeautifulSoup(text, "html.parser")

        request = Request(url=URL("https://example.com"))
        response = Response(
            url=URL("https://example.com"),
            method="GET",
            text=html,
            xml_parser=mock_parser,
            history=[URL("https://example.com")],
        )

        items = []
        async for item in parser.parse_item(request, response):
            items.append(item)

        # With favicon_data_uri=True, should yield requests for icons
        # (actual behavior depends on implementation)
        assert len(items) > 0
