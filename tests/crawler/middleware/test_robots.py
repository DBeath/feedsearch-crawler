"""Tests for RobotsMiddleware."""

import pytest
from yarl import URL

from feedsearch_crawler.crawler.middleware.robots import RobotsMiddleware
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
from feedsearch_crawler.exceptions import RobotsBlockedError

DISALLOW_PRIVATE = "User-agent: *\nDisallow: /private"


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
        middleware.register_robots_txt(
            URL("https://example.com/robots.txt"), DISALLOW_PRIVATE
        )

        request = Request(url=URL("https://example.com/allowed-path"))

        # Should not raise exception
        await middleware.pre_request(request)
        # process_request is a no-op after the request has been sent
        await middleware.process_request(request)

    @pytest.mark.asyncio
    async def test_robots_txt_blocks_request(self):
        """Test that requests are blocked when robots.txt disallows."""
        middleware = RobotsMiddleware(user_agent="TestBot")
        middleware.register_robots_txt(
            URL("https://example.com/robots.txt"), DISALLOW_PRIVATE
        )

        request = Request(url=URL("https://example.com/private/secret"))

        # Should raise RobotsBlockedError for blocked requests
        with pytest.raises(RobotsBlockedError) as exc_info:
            await middleware.pre_request(request)

        assert "Blocked by robots.txt" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_robots_txt_caching(self):
        """Test that robots.txt is cached per host."""
        middleware = RobotsMiddleware(user_agent="TestBot")
        middleware.register_robots_txt(
            URL("https://example.com/robots.txt"), DISALLOW_PRIVATE
        )

        # Multiple requests to the same host reuse the single cached parser
        await middleware.pre_request(Request(url=URL("https://example.com/page1")))
        await middleware.pre_request(Request(url=URL("https://example.com/page2")))

        assert len(middleware.cache) == 1
        assert "https://example.com/robots.txt" in middleware.cache
        assert middleware.cache["https://example.com/robots.txt"] is not None

    @pytest.mark.asyncio
    async def test_different_hosts_separate_robots(self):
        """Test that different hosts have separate robots.txt handling."""
        middleware = RobotsMiddleware(user_agent="TestBot")
        middleware.register_robots_txt(
            URL("https://example.com/robots.txt"), DISALLOW_PRIVATE
        )
        middleware.register_robots_txt(
            URL("https://different.com/robots.txt"), "User-agent: *\nAllow: /"
        )

        assert len(middleware.cache) == 2

        # example.com blocks /private, different.com does not
        with pytest.raises(RobotsBlockedError):
            await middleware.pre_request(
                Request(url=URL("https://example.com/private/page"))
            )
        await middleware.pre_request(
            Request(url=URL("https://different.com/private/page"))
        )

    @pytest.mark.asyncio
    async def test_cache_keys_include_port(self):
        """Test that hosts on different ports have separate robots.txt rules."""
        middleware = RobotsMiddleware(user_agent="TestBot")
        middleware.register_robots_txt(
            URL("https://example.com:8080/robots.txt"), "User-agent: *\nDisallow: /"
        )

        # The port-specific rules block requests on that port only
        with pytest.raises(RobotsBlockedError):
            await middleware.pre_request(
                Request(url=URL("https://example.com:8080/page"))
            )
        # Default port has no registered robots.txt, so requests are allowed
        await middleware.pre_request(Request(url=URL("https://example.com/page")))

    @pytest.mark.asyncio
    async def test_robots_txt_request_never_blocked(self):
        """Test that the robots.txt request itself is never blocked."""
        middleware = RobotsMiddleware(user_agent="TestBot")
        middleware.register_robots_txt(
            URL("https://example.com/robots.txt"), "User-agent: *\nDisallow: /"
        )

        # Even with a disallow-all rule, /robots.txt must be fetchable
        await middleware.pre_request(Request(url=URL("https://example.com/robots.txt")))

    @pytest.mark.asyncio
    async def test_robots_txt_fetch_failure_allows_request(self):
        """Test that requests are allowed when robots.txt cannot be fetched."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        # The crawler registers None when robots.txt could not be fetched
        middleware.register_robots_txt(URL("https://unreachable.com/robots.txt"), None)
        assert middleware.cache["https://unreachable.com/robots.txt"] is None

        request = Request(url=URL("https://unreachable.com/page"))

        # Should not raise exception - should allow request by default
        await middleware.pre_request(request)

    @pytest.mark.asyncio
    async def test_unregistered_host_allows_request(self):
        """Test that requests to hosts with no registered robots.txt are allowed."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        request = Request(url=URL("https://unknown-host.com/page"))

        # No robots.txt registered for this host - permissive by default
        await middleware.pre_request(request)

    @pytest.mark.asyncio
    async def test_user_agent_specific_rules(self):
        """Test that user-agent specific rules are respected."""
        robots_txt = (
            "User-agent: SpecificBot\n"
            "Allow: /special/\n"
            "Disallow: /\n"
            "\n"
            "User-agent: *\n"
            "Allow: /\n"
        )

        middleware = RobotsMiddleware(user_agent="SpecificBot")
        middleware.register_robots_txt(
            URL("https://example.com/robots.txt"), robots_txt
        )

        # SpecificBot can access /special/ but nothing else
        await middleware.pre_request(
            Request(url=URL("https://example.com/special/page"))
        )
        with pytest.raises(RobotsBlockedError):
            await middleware.pre_request(Request(url=URL("https://example.com/other")))

        # Other user agents are unaffected by the SpecificBot rules
        other_middleware = RobotsMiddleware(user_agent="OtherBot")
        other_middleware.register_robots_txt(
            URL("https://example.com/robots.txt"), robots_txt
        )
        await other_middleware.pre_request(
            Request(url=URL("https://example.com/other"))
        )

    @pytest.mark.asyncio
    async def test_crawl_delay_respected(self):
        """Test that crawl-delay from robots.txt is parsed."""
        middleware = RobotsMiddleware(user_agent="TestBot")
        middleware.register_robots_txt(
            URL("https://example.com/robots.txt"),
            "User-agent: *\nCrawl-delay: 2\nDisallow: /private",
        )

        # Crawl-delay does not block the request
        await middleware.pre_request(Request(url=URL("https://example.com/page")))

        # The parsed crawl-delay is available on the cached parser
        rp = middleware.cache["https://example.com/robots.txt"]
        assert rp.crawl_delay("TestBot") == 2

    @pytest.mark.asyncio
    async def test_robots_txt_with_sitemap(self):
        """Test handling of sitemap directives in robots.txt."""
        middleware = RobotsMiddleware(user_agent="TestBot")
        middleware.register_robots_txt(
            URL("https://example.com/robots.txt"),
            "User-agent: *\nAllow: /\n\nSitemap: https://example.com/sitemap.xml",
        )

        # Sitemap URLs are extracted and available per host
        sitemaps = middleware.get_sitemaps_for_host("https://example.com")
        assert sitemaps == ["https://example.com/sitemap.xml"]

        # And normal requests still pass through
        await middleware.pre_request(Request(url=URL("https://example.com/page")))

    @pytest.mark.asyncio
    async def test_process_response_method(self):
        """Test that process_response method doesn't interfere."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        response = Response(
            url=URL("https://example.com/test"),
            method="GET",
            headers={},
            status_code=200,
            history=[],
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

        # Registering garbage content must not crash
        middleware.register_robots_txt(
            URL("https://malformed.com/robots.txt"), "\x00\x01<<<not robots txt>>>"
        )

        request = Request(url=URL("https://malformed.com/page"))

        # Should handle gracefully and allow the request
        await middleware.pre_request(request)

    @pytest.mark.asyncio
    async def test_empty_robots_txt(self):
        """Test handling of empty robots.txt files."""
        middleware = RobotsMiddleware(user_agent="TestBot")

        # Empty content is cached as None (permissive)
        middleware.register_robots_txt(URL("https://empty-robots.com/robots.txt"), "")
        assert middleware.cache["https://empty-robots.com/robots.txt"] is None

        request = Request(url=URL("https://empty-robots.com/page"))

        # Should allow all requests when robots.txt is empty
        await middleware.pre_request(request)
