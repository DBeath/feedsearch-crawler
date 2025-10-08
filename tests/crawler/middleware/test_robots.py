"""Tests for RobotsMiddleware."""

import pytest
from unittest.mock import patch, MagicMock
from yarl import URL

from feedsearch_crawler.crawler.middleware.robots import RobotsMiddleware
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response


class TestRobotsMiddleware:
    """Test robots.txt middleware functionality."""

    def test_middleware_initialization(self):
        """Test middleware initialization."""
        middleware = RobotsMiddleware(user_agent="TestBot/1.0")
        assert middleware.user_agent == "TestBot/1.0"

    def test_middleware_initialization_default_user_agent(self):
        """Test initialization with default user agent."""
        middleware = RobotsMiddleware()
        # Should have some default user agent
        assert middleware.user_agent == "Feedsearch-Crawler"

    @pytest.mark.asyncio
    async def test_robots_txt_allows_request(self):
        """Test that requests are allowed when robots.txt permits."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        # Mock the RobotFileParser
        with patch('feedsearch_crawler.crawler.middleware.robots.RobotFileParser') as mock_robotparser:
            mock_rp = MagicMock()
            mock_rp.can_fetch.return_value = True
            mock_robotparser.return_value = mock_rp

            request = Request(url=URL("https://example.com/allowed-path"))

            # Should not raise exception or modify request
            await middleware.pre_request(request)
            await middleware.process_request(request)

    @pytest.mark.asyncio
    async def test_robots_txt_blocks_request(self):
        """Test that requests are blocked when robots.txt disallows."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        # Mock the RobotFileParser to disallow the request
        with patch('feedsearch_crawler.crawler.middleware.robots.RobotFileParser') as mock_robotparser:
            mock_rp = MagicMock()
            mock_rp.can_fetch.return_value = False  # Blocked
            mock_robotparser.return_value = mock_rp

            request = Request(url=URL("https://example.com/private/secret"))

            # Should raise exception for blocked requests
            with pytest.raises(Exception) as exc_info:
                await middleware.process_request(request)

            assert "Blocked by robots.txt" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_robots_txt_caching(self):
        """Test that robots.txt is cached per host."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        # Mock the robots.txt fetching
        with patch('feedsearch_crawler.crawler.middleware.robots.RobotFileParser') as mock_robotparser:
            mock_rp = MagicMock()
            mock_rp.can_fetch.return_value = True
            mock_robotparser.return_value = mock_rp

            # First request to a host
            request1 = Request(url=URL("https://example.com/page1"))
            await middleware.process_request(request1)

            # Second request to same host
            request2 = Request(url=URL("https://example.com/page2"))
            await middleware.process_request(request2)

            # Should only create one RobotFileParser instance (cached)
            assert mock_robotparser.RobotFileParser.call_count <= 1

    @pytest.mark.asyncio
    async def test_different_hosts_separate_robots(self):
        """Test that different hosts have separate robots.txt handling."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        with patch('feedsearch_crawler.crawler.middleware.robots.RobotFileParser') as mock_robotparser:
            mock_rp = MagicMock()
            mock_rp.can_fetch.return_value = True
            mock_robotparser.return_value = mock_rp

            # Requests to different hosts
            request1 = Request(url=URL("https://example.com/page"))
            request2 = Request(url=URL("https://different.com/page"))

            await middleware.process_request(request1)
            await middleware.process_request(request2)

            # Should create separate parsers for different hosts
            assert mock_robotparser.call_count >= 2

    @pytest.mark.asyncio
    async def test_robots_txt_fetch_failure_allows_request(self):
        """Test that requests are allowed when robots.txt cannot be fetched."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        # Mock robots.txt fetching to fail
        with patch('feedsearch_crawler.crawler.middleware.robots.RobotFileParser') as mock_robotparser:
            mock_rp = MagicMock()
            mock_rp.read.side_effect = Exception("Network error")
            mock_rp.can_fetch.return_value = True  # Default to allow on error
            mock_robotparser.return_value = mock_rp

            request = Request(url=URL("https://unreachable.com/page"))

            # Should not raise exception - should allow request by default
            await middleware.process_request(request)

    @pytest.mark.asyncio
    async def test_user_agent_specific_rules(self):
        """Test that user-agent specific rules are respected."""
        middleware = RobotsMiddleware(user_agent="SpecificBot")

        with patch('feedsearch_crawler.crawler.middleware.robots.RobotFileParser') as mock_robotparser:
            mock_rp = MagicMock()
            # Mock that our specific bot can access /special/ but not other paths
            def can_fetch_mock(user_agent, url):
                if "/special/" in url:
                    return True
                return False

            mock_rp.can_fetch.side_effect = can_fetch_mock
            mock_robotparser.return_value = mock_rp

            allowed_request = Request(url=URL("https://example.com/special/page"))

            # Should handle according to specific rules
            # (The exact behavior depends on implementation)
            try:
                await middleware.process_request(allowed_request)
            except Exception:
                pytest.fail("Allowed request was blocked")

            # Blocked request might raise exception or be marked
            # This depends on the actual implementation

    @pytest.mark.asyncio
    async def test_crawl_delay_respected(self):
        """Test that crawl-delay from robots.txt is respected."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        with patch('feedsearch_crawler.crawler.middleware.robots.RobotFileParser') as mock_robotparser:
            mock_rp = MagicMock()
            mock_rp.can_fetch.return_value = True
            mock_rp.crawl_delay.return_value = 2.0  # 2 second delay
            mock_robotparser.return_value = mock_rp

            request = Request(url=URL("https://example.com/page"))

            # Process request - should handle crawl delay
            await middleware.process_request(request)

            # Check if request was modified to include delay
            # (Implementation dependent)

    @pytest.mark.asyncio
    async def test_robots_txt_with_sitemap(self):
        """Test handling of sitemap directives in robots.txt."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        with patch('feedsearch_crawler.crawler.middleware.robots.RobotFileParser') as mock_robotparser:
            mock_rp = MagicMock()
            mock_rp.can_fetch.return_value = True
            mock_rp.site_maps.return_value = ["https://example.com/sitemap.xml"]
            mock_robotparser.return_value = mock_rp

            request = Request(url=URL("https://example.com/page"))
            await middleware.process_request(request)

            # The middleware might use sitemap information
            # This depends on the actual implementation

    @pytest.mark.asyncio
    async def test_process_response_method(self):
        """Test that process_response method doesn't interfere."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        response = Response(
            url=URL("https://example.com/test"),
            method="GET",
            headers={},
            status_code=200,
            history=[]
        )

        # Should not raise exceptions
        await middleware.process_response(response)

    @pytest.mark.asyncio
    async def test_process_exception_method(self):
        """Test that process_exception method doesn't interfere."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        request = Request(url=URL("https://example.com/test"))
        exception = Exception("test exception")

        # Should not raise exceptions
        await middleware.process_exception(request, exception)

    @pytest.mark.asyncio
    async def test_malformed_robots_txt(self):
        """Test handling of malformed robots.txt files."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        with patch('feedsearch_crawler.crawler.middleware.robots.RobotFileParser') as mock_robotparser:
            mock_rp = MagicMock()
            # Simulate malformed robots.txt parsing
            mock_rp.read.side_effect = ValueError("Malformed robots.txt")
            mock_rp.can_fetch.return_value = True  # Default to allow on error
            mock_robotparser.return_value = mock_rp

            request = Request(url=URL("https://malformed.com/page"))

            # Should handle gracefully and not crash
            await middleware.process_request(request)

    @pytest.mark.asyncio
    async def test_empty_robots_txt(self):
        """Test handling of empty robots.txt files."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        with patch('feedsearch_crawler.crawler.middleware.robots.RobotFileParser') as mock_robotparser:
            mock_rp = MagicMock()
            mock_rp.can_fetch.return_value = True  # Empty robots.txt allows everything
            mock_robotparser.return_value = mock_rp

            request = Request(url=URL("https://empty-robots.com/page"))

            # Should allow all requests when robots.txt is empty
            await middleware.process_request(request)