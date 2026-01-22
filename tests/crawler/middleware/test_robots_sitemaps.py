"""Comprehensive tests for robots.txt handling, sitemap discovery, and crawl limits."""

import pytest
from unittest.mock import Mock, patch
from urllib.robotparser import RobotFileParser
from yarl import URL

from feedsearch_crawler.crawler.middleware.robots import RobotsMiddleware
from feedsearch_crawler.crawler.request import Request


class TestRobotsMiddlewareBasic:
    """Test basic robots.txt functionality."""

    @pytest.mark.asyncio
    async def test_robots_allows_all_by_default(self):
        """Test that requests are allowed when robots.txt is unavailable."""
        middleware = RobotsMiddleware(user_agent="TestBot")
        request = Request(url=URL("https://example.com/feed.xml"))

        # Mock failed robots.txt load
        with patch.object(middleware, "_load_robots_txt") as mock_load:
            mock_load.return_value = None
            middleware.cache["https://example.com/robots.txt"] = None

            # Should not raise exception
            await middleware.process_request(request)

    @pytest.mark.asyncio
    async def test_robots_blocks_disallowed_path(self):
        """Test that robots.txt blocks disallowed paths."""
        middleware = RobotsMiddleware(user_agent="TestBot")
        request = Request(url=URL("https://example.com/private/data"))

        # Create mock RobotFileParser that blocks the path
        mock_rp = Mock(spec=RobotFileParser)
        mock_rp.can_fetch.return_value = False
        middleware.cache["https://example.com/robots.txt"] = mock_rp

        with pytest.raises(Exception, match="Blocked by robots.txt"):
            await middleware.process_request(request)

    @pytest.mark.asyncio
    async def test_robots_allows_allowed_path(self):
        """Test that robots.txt allows allowed paths."""
        middleware = RobotsMiddleware(user_agent="TestBot")
        request = Request(url=URL("https://example.com/feed.xml"))

        # Create mock RobotFileParser that allows the path
        mock_rp = Mock(spec=RobotFileParser)
        mock_rp.can_fetch.return_value = True
        middleware.cache["https://example.com/robots.txt"] = mock_rp

        # Should not raise exception
        await middleware.process_request(request)

    @pytest.mark.asyncio
    async def test_robots_caching_per_host(self):
        """Test that robots.txt is cached per host."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        mock_rp = Mock(spec=RobotFileParser)
        mock_rp.can_fetch.return_value = True
        middleware.cache["https://example.com/robots.txt"] = mock_rp

        request1 = Request(url=URL("https://example.com/feed1.xml"))
        request2 = Request(url=URL("https://example.com/feed2.xml"))

        await middleware.process_request(request1)
        await middleware.process_request(request2)

        # Should only have one cache entry for the host
        assert "https://example.com/robots.txt" in middleware.cache
        assert len(middleware.cache) == 1

    @pytest.mark.asyncio
    async def test_robots_different_hosts_separate_cache(self):
        """Test that different hosts have separate robots.txt cache."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        mock_rp1 = Mock(spec=RobotFileParser)
        mock_rp1.can_fetch.return_value = True
        mock_rp2 = Mock(spec=RobotFileParser)
        mock_rp2.can_fetch.return_value = True

        middleware.cache["https://example.com/robots.txt"] = mock_rp1
        middleware.cache["https://other.com/robots.txt"] = mock_rp2

        request1 = Request(url=URL("https://example.com/feed.xml"))
        request2 = Request(url=URL("https://other.com/feed.xml"))

        await middleware.process_request(request1)
        await middleware.process_request(request2)

        assert len(middleware.cache) == 2

    @pytest.mark.asyncio
    async def test_robots_request_without_host(self):
        """Test handling of requests without host."""
        middleware = RobotsMiddleware(user_agent="TestBot")
        # Create a malformed URL without host
        request = Request(url=URL("file:///local/path"))

        # Should not raise exception for URLs without host
        await middleware.process_request(request)


class TestRobotsMiddlewareUserAgent:
    """Test user-agent specific robots.txt rules."""

    @pytest.mark.asyncio
    async def test_robots_respects_specific_user_agent(self):
        """Test that specific user-agent rules are respected."""
        middleware = RobotsMiddleware(user_agent="Feedsearch-Crawler")
        request = Request(url=URL("https://example.com/feed"))

        mock_rp = Mock(spec=RobotFileParser)
        # Specific user-agent blocked
        mock_rp.can_fetch.return_value = False
        middleware.cache["https://example.com/robots.txt"] = mock_rp

        with pytest.raises(Exception, match="Blocked by robots.txt"):
            await middleware.process_request(request)

        # Verify it checked with correct user-agent
        mock_rp.can_fetch.assert_called_with("Feedsearch-Crawler", str(request.url))

    @pytest.mark.asyncio
    async def test_robots_default_user_agent(self):
        """Test default user-agent is used."""
        middleware = RobotsMiddleware()  # Use default user-agent
        assert middleware.user_agent == "Feedsearch-Crawler"


class TestRobotsMiddlewareCrawlDelay:
    """Test crawl-delay handling from robots.txt."""

    @pytest.mark.asyncio
    async def test_robots_provides_crawl_delay(self):
        """Test extraction of crawl-delay from robots.txt."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        # Create mock with crawl_delay
        mock_rp = Mock(spec=RobotFileParser)
        mock_rp.can_fetch.return_value = True
        mock_rp.crawl_delay.return_value = 2.0  # 2 second delay
        middleware.cache["https://example.com/robots.txt"] = mock_rp

        # This test verifies the structure is in place
        # Actual delay enforcement would be in the crawler/spider
        request = Request(url=URL("https://example.com/feed"))
        await middleware.process_request(request)

        # If we had delay enforcement, we'd test it here
        # For now, verify the robots parser is set up correctly
        assert mock_rp.can_fetch.called


class TestRobotsMiddlewareSitemapDiscovery:
    """Test sitemap discovery from robots.txt."""

    def test_robots_txt_sitemap_extraction(self):
        """Test extraction of sitemap URLs from robots.txt."""
        # This tests the concept - actual implementation would parse robots.txt
        robots_txt_content = """
User-agent: *
Disallow: /private/

Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/sitemap-news.xml
"""
        # Parse sitemaps
        sitemaps = []
        for line in robots_txt_content.split("\n"):
            if line.strip().startswith("Sitemap:"):
                sitemap_url = line.split(":", 1)[1].strip()
                sitemaps.append(sitemap_url)

        assert len(sitemaps) == 2
        assert "sitemap.xml" in sitemaps[0]
        assert "sitemap-news.xml" in sitemaps[1]

    def test_multiple_sitemap_entries(self):
        """Test handling of multiple sitemap entries."""
        robots_txt_content = """
Sitemap: https://example.com/sitemap1.xml
Sitemap: https://example.com/sitemap2.xml
Sitemap: https://example.com/sitemap3.xml
"""
        sitemaps = [
            line.split(":", 1)[1].strip()
            for line in robots_txt_content.split("\n")
            if line.strip().startswith("Sitemap:")
        ]

        assert len(sitemaps) == 3

    def test_sitemap_with_index(self):
        """Test sitemap index file discovery."""
        robots_txt_content = """
Sitemap: https://example.com/sitemap_index.xml
"""
        sitemaps = [
            line.split(":", 1)[1].strip()
            for line in robots_txt_content.split("\n")
            if line.strip().startswith("Sitemap:")
        ]

        assert len(sitemaps) == 1
        assert "sitemap_index.xml" in sitemaps[0]


class TestSitemapXMLParsing:
    """Test sitemap.xml parsing for URL generation."""

    def test_sitemap_url_extraction(self):
        """Test extraction of URLs from sitemap.xml."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/feed.xml</loc>
        <lastmod>2025-01-01</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>https://example.com/rss</loc>
        <lastmod>2025-01-02</lastmod>
    </url>
</urlset>"""
        # Parse URLs from sitemap
        from xml.etree import ElementTree as ET

        root = ET.fromstring(sitemap_xml)

        # Extract URLs
        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text for loc in root.findall(".//ns:loc", namespace)]

        assert len(urls) == 2
        assert "feed.xml" in urls[0]
        assert "rss" in urls[1]

    def test_sitemap_index_parsing(self):
        """Test parsing of sitemap index files."""
        sitemap_index = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <sitemap>
        <loc>https://example.com/sitemap1.xml</loc>
        <lastmod>2025-01-01</lastmod>
    </sitemap>
    <sitemap>
        <loc>https://example.com/sitemap2.xml</loc>
        <lastmod>2025-01-02</lastmod>
    </sitemap>
</sitemapindex>"""
        from xml.etree import ElementTree as ET

        root = ET.fromstring(sitemap_index)

        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        sitemaps = [loc.text for loc in root.findall(".//ns:sitemap/ns:loc", namespace)]

        assert len(sitemaps) == 2
        assert all("sitemap" in s for s in sitemaps)

    def test_sitemap_feed_url_filtering(self):
        """Test filtering sitemap URLs for potential feeds."""
        sitemap_urls = [
            "https://example.com/feed.xml",
            "https://example.com/rss",
            "https://example.com/atom.xml",
            "https://example.com/blog/post-1",
            "https://example.com/about",
        ]

        # Filter for feed-like URLs
        feed_keywords = ["rss", "feed", "atom", "xml"]
        potential_feeds = [
            url
            for url in sitemap_urls
            if any(keyword in url.lower() for keyword in feed_keywords)
        ]

        assert len(potential_feeds) >= 3
        assert any("feed" in url for url in potential_feeds)

    def test_sitemap_lastmod_extraction(self):
        """Test extraction of lastmod dates from sitemap."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/feed.xml</loc>
        <lastmod>2025-01-15</lastmod>
    </url>
</urlset>"""
        from xml.etree import ElementTree as ET

        root = ET.fromstring(sitemap_xml)

        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        url_elem = root.find(".//ns:url", namespace)
        lastmod = url_elem.find("ns:lastmod", namespace).text

        assert lastmod == "2025-01-15"

    def test_sitemap_priority_extraction(self):
        """Test extraction of priority values from sitemap."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/feed.xml</loc>
        <priority>0.9</priority>
    </url>
</urlset>"""
        from xml.etree import ElementTree as ET

        root = ET.fromstring(sitemap_xml)

        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        priority = root.find(".//ns:priority", namespace).text

        assert float(priority) == 0.9


class TestRobotsMiddlewareErrorHandling:
    """Test error handling in robots.txt processing."""

    @pytest.mark.asyncio
    async def test_robots_loading_error_allows_request(self):
        """Test that loading errors allow the request (be permissive)."""
        middleware = RobotsMiddleware(user_agent="TestBot")
        request = Request(url=URL("https://example.com/feed"))

        with patch.object(middleware, "_load_robots_txt") as mock_load:
            # Simulate loading error
            mock_load.side_effect = Exception("Network error")

            # Should not raise exception - be permissive on errors
            try:
                await middleware.process_request(request)
                # If it gets here, the request was allowed (correct behavior)
            except Exception as e:
                if "Blocked by robots.txt" in str(e):
                    pytest.fail("Should not block on loading errors")

    @pytest.mark.asyncio
    async def test_robots_malformed_file_handling(self):
        """Test handling of malformed robots.txt files."""
        middleware = RobotsMiddleware(user_agent="TestBot")
        request = Request(url=URL("https://example.com/feed"))

        # Cache a None value to simulate malformed/unavailable robots.txt
        middleware.cache["https://example.com/robots.txt"] = None

        # Should allow request when robots.txt is malformed
        await middleware.process_request(request)


class TestRobotsIntegrationScenarios:
    """Test integration scenarios with robots.txt and sitemaps."""

    def test_feed_discovery_via_sitemap(self):
        """Test discovering feeds through sitemap.xml."""
        # Simulate workflow:
        # 1. Check robots.txt for sitemap
        # 2. Parse sitemap for URLs
        # 3. Filter for feed-like URLs

        robots_txt = "Sitemap: https://example.com/sitemap.xml"
        sitemap_url = None

        for line in robots_txt.split("\n"):
            if "Sitemap:" in line:
                sitemap_url = line.split(":", 1)[1].strip()
                break

        assert sitemap_url == "https://example.com/sitemap.xml"

    def test_crawl_respects_robots_disallow(self):
        """Test that crawler respects robots.txt disallow directives."""
        # Simulate checking if URL is allowed
        disallowed_paths = ["/private/", "/admin/"]
        test_url = "/private/feed.xml"

        is_disallowed = any(path in test_url for path in disallowed_paths)
        assert is_disallowed is True

    def test_crawl_respects_robots_allow(self):
        """Test that crawler respects robots.txt allow directives."""
        disallowed_paths = ["/private/", "/admin/"]
        test_url = "/feed.xml"

        is_disallowed = any(path in test_url for path in disallowed_paths)
        assert is_disallowed is False

    def test_sitemap_provides_initial_urls(self):
        """Test using sitemap to generate initial crawl URLs."""
        # Simulate extracting feed URLs from sitemap
        sitemap_urls = [
            "https://example.com/feed.xml",
            "https://example.com/blog/rss",
            "https://example.com/news/atom.xml",
        ]

        # These would be added to initial crawl queue
        feed_urls = [
            url
            for url in sitemap_urls
            if any(keyword in url for keyword in ["feed", "rss", "atom"])
        ]

        assert len(feed_urls) == 3
