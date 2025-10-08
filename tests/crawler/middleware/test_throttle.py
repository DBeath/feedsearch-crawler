"""Tests for ThrottleMiddleware."""

import asyncio

import pytest
from yarl import URL

from feedsearch_crawler.crawler.middleware.throttle import ThrottleMiddleware
from feedsearch_crawler.crawler.request import Request


class TestThrottleMiddleware:
    """Test throttling middleware functionality."""

    @pytest.mark.asyncio
    async def test_per_host_throttling(self):
        """Test that different hosts are throttled independently."""
        middleware = ThrottleMiddleware(rate_per_sec=10)  # 100ms delay

        # Create requests to different hosts
        request1 = Request(url=URL("https://example.com/page1"))
        request2 = Request(url=URL("https://different.com/page1"))
        request3 = Request(url=URL("https://example.com/page2"))  # Same host as request1

        start_time = asyncio.get_event_loop().time()

        # First request to each host should not be delayed
        await middleware.process_request(request1)
        time_after_first = asyncio.get_event_loop().time()

        await middleware.process_request(request2)
        time_after_second = asyncio.get_event_loop().time()

        # These should be almost immediate (no significant delay)
        assert (time_after_first - start_time) < 0.05
        assert (time_after_second - time_after_first) < 0.05

        # Third request to same host as first should be delayed
        await middleware.process_request(request3)
        time_after_third = asyncio.get_event_loop().time()

        # Should have been delayed by ~100ms (1/10 rate_per_sec)
        delay = time_after_third - time_after_first
        assert delay >= 0.09  # Account for timing variation

    @pytest.mark.asyncio
    async def test_throttling_respects_rate_limit(self):
        """Test that throttling respects the configured rate limit."""
        middleware = ThrottleMiddleware(rate_per_sec=10)  # 100ms delay - faster

        request1 = Request(url=URL("https://example.com/page1"))
        request2 = Request(url=URL("https://example.com/page2"))

        start_time = asyncio.get_event_loop().time()

        await middleware.process_request(request1)
        await middleware.process_request(request2)

        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time

        # Should take at least 100ms for the second request
        assert total_time >= 0.08  # Account for timing variation

    @pytest.mark.asyncio
    async def test_no_throttling_for_first_request_per_host(self):
        """Test that the first request to each host is not throttled."""
        middleware = ThrottleMiddleware(rate_per_sec=1)  # 1 second delay

        request = Request(url=URL("https://example.com/page1"))

        start_time = asyncio.get_event_loop().time()
        await middleware.process_request(request)
        end_time = asyncio.get_event_loop().time()

        # First request should be immediate
        assert (end_time - start_time) < 0.05

    @pytest.mark.asyncio
    async def test_host_timer_tracking(self):
        """Test that host timers are properly tracked."""
        middleware = ThrottleMiddleware(rate_per_sec=10)

        request1 = Request(url=URL("https://example.com/page1"))
        request2 = Request(url=URL("https://test.com/page1"))

        await middleware.process_request(request1)
        await middleware.process_request(request2)

        # Both hosts should be tracked
        assert "example.com" in middleware.host_timers
        assert "test.com" in middleware.host_timers
        assert len(middleware.host_timers) == 2

    @pytest.mark.asyncio
    async def test_handles_url_without_host(self):
        """Test handling of URLs without host (edge case)."""
        middleware = ThrottleMiddleware(rate_per_sec=10)

        # Create a request with a URL that might not have a host
        request = Request(url=URL("file:///local/path"))

        # Should not crash
        await middleware.process_request(request)
        assert "unknown" in middleware.host_timers or None in middleware.host_timers

    @pytest.mark.asyncio
    async def test_multiple_requests_same_host_sequential(self):
        """Test multiple sequential requests to the same host."""
        middleware = ThrottleMiddleware(rate_per_sec=5)  # 200ms delay

        host = "example.com"
        requests = [
            Request(url=URL(f"https://{host}/page{i}"))
            for i in range(3)
        ]

        start_time = asyncio.get_event_loop().time()

        for request in requests:
            await middleware.process_request(request)

        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time

        # Should take at least 400ms for 3 requests (first immediate, then 2 * 200ms)
        expected_min_time = 2 * (1 / 5)  # 2 delays of 200ms each
        assert total_time >= expected_min_time * 0.9  # 10% tolerance

    @pytest.mark.asyncio
    async def test_concurrent_requests_different_hosts(self):
        """Test concurrent requests to different hosts don't interfere."""
        middleware = ThrottleMiddleware(rate_per_sec=2)  # 500ms delay

        async def make_request(host, page):
            request = Request(url=URL(f"https://{host}/page{page}"))
            start = asyncio.get_event_loop().time()
            await middleware.process_request(request)
            end = asyncio.get_event_loop().time()
            return end - start

        # Start concurrent requests to different hosts
        tasks = [
            asyncio.create_task(make_request("host1.com", 1)),
            asyncio.create_task(make_request("host2.com", 1)),
            asyncio.create_task(make_request("host3.com", 1)),
        ]

        start_time = asyncio.get_event_loop().time()
        durations = await asyncio.gather(*tasks)
        total_time = asyncio.get_event_loop().time() - start_time

        # All should complete quickly since they're different hosts
        assert total_time < 0.2  # Should be much faster than sequential
        for duration in durations:
            assert duration < 0.1  # Each individual request should be fast

    def test_middleware_initialization(self):
        """Test middleware initialization with different rates."""
        middleware1 = ThrottleMiddleware(rate_per_sec=1)
        assert middleware1.rate_per_sec == 1
        assert isinstance(middleware1.host_timers, dict)
        assert len(middleware1.host_timers) == 0

        middleware2 = ThrottleMiddleware(rate_per_sec=100)
        assert middleware2.rate_per_sec == 100

    @pytest.mark.asyncio
    async def test_pre_request_and_response_methods(self):
        """Test that pre_request and process_response methods don't interfere."""
        middleware = ThrottleMiddleware(rate_per_sec=10)
        request = Request(url=URL("https://example.com/test"))

        # Mock response object
        class MockResponse:
            def __init__(self):
                self.url = URL("https://example.com/test")
                self.status_code = 200

        response = MockResponse()

        # These methods should not raise exceptions
        await middleware.pre_request(request)
        await middleware.process_response(response)
        await middleware.process_exception(request, Exception("test"))

        # Main functionality should still work
        start_time = asyncio.get_event_loop().time()
        await middleware.process_request(request)
        end_time = asyncio.get_event_loop().time()

        # First request should be immediate
        assert (end_time - start_time) < 0.05