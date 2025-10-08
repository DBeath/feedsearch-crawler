"""Tests for the core Crawler class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from yarl import URL

from feedsearch_crawler.crawler.item import Item
from feedsearch_crawler.crawler.lib import Stats
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
from tests.conftest import MockCrawler


class MockItem(Item):
    def __init__(self, data: str):
        self.data = data


class TestCrawlerInitialization:
    """Test crawler initialization and configuration."""

    def test_default_initialization(self):
        crawler = MockCrawler()
        assert crawler.concurrency == 10
        assert crawler.max_depth == 10
        assert crawler.delay == 0.5
        assert crawler.max_content_length == 1024 * 1024 * 10
        assert len(crawler.middlewares) == 6  # Default middleware count

    def test_custom_initialization(self):
        crawler = MockCrawler(
            concurrency=5,
            max_depth=3,
            delay=1.0,
            user_agent="CustomBot/1.0",
            allowed_domains=["example.com", "test.com"]
        )
        assert crawler.concurrency == 5
        assert crawler.max_depth == 3
        assert crawler.delay == 1.0
        assert crawler.user_agent == "CustomBot/1.0"
        assert crawler.allowed_domains == ["example.com", "test.com"]

    def test_headers_configuration(self):
        custom_headers = {"X-Custom": "test-value"}
        crawler = MockCrawler(headers=custom_headers)

        assert "User-Agent" in crawler.headers
        assert "X-Custom" in crawler.headers
        assert crawler.headers["X-Custom"] == "test-value"

    def test_middleware_initialization(self):
        crawler = MockCrawler()

        # Check that default middlewares are loaded
        middleware_types = [type(m).__name__ for m in crawler.middlewares]
        expected_middlewares = [
            "RobotsMiddleware", "ThrottleMiddleware", "RetryMiddleware",
            "CookieMiddleware", "ContentTypeMiddleware", "MonitoringMiddleware"
        ]

        for expected in expected_middlewares:
            assert expected in middleware_types


class TestCrawlerDomainFiltering:
    """Test domain filtering functionality."""

    def test_no_domain_restrictions(self):
        crawler = MockCrawler()
        assert crawler.is_allowed_domain(URL("https://example.com"))
        assert crawler.is_allowed_domain(URL("https://any-domain.com"))

    def test_exact_domain_match(self):
        crawler = MockCrawler(allowed_domains=["example.com"])
        assert crawler.is_allowed_domain(URL("https://example.com"))
        assert crawler.is_allowed_domain(URL("https://example.com/path"))
        assert not crawler.is_allowed_domain(URL("https://other.com"))

    def test_wildcard_domain_patterns(self):
        crawler = MockCrawler(allowed_domains=["*.example.com", "test.org"])
        assert crawler.is_allowed_domain(URL("https://sub.example.com"))
        assert crawler.is_allowed_domain(URL("https://any.example.com"))
        assert crawler.is_allowed_domain(URL("https://test.org"))
        assert not crawler.is_allowed_domain(URL("https://example.com"))  # No wildcard match
        assert not crawler.is_allowed_domain(URL("https://other.org"))

    def test_invalid_url_domain_check(self):
        crawler = MockCrawler(allowed_domains=["example.com"])
        # URL with no host should return False
        assert not crawler.is_allowed_domain(URL("file:///local/path"))


class TestCrawlerStartUrls:
    """Test start URL creation and validation."""

    def test_create_start_urls_from_strings(self):
        crawler = MockCrawler()
        urls = crawler.create_start_urls(["example.com", "test.org/path"])

        assert len(urls) == 2
        assert URL("http://example.com") in urls
        assert URL("http://test.org/path") in urls

    def test_create_start_urls_with_schemes(self):
        crawler = MockCrawler()
        urls = crawler.create_start_urls([
            "https://example.com",
            "http://test.org",
            "ftp://files.com"  # Should be converted to http
        ])

        assert URL("https://example.com") in urls
        assert URL("http://test.org") in urls
        assert URL("http://files.com") in urls

    def test_create_start_urls_deduplication(self):
        crawler = MockCrawler()
        urls = crawler.create_start_urls([
            "example.com",
            "http://example.com",
            "https://example.com"
        ])

        # Should deduplicate to unique URLs
        url_strings = [str(u) for u in urls]
        assert len(set(url_strings)) == len(urls)


@pytest.mark.asyncio
class TestCrawlerFollowMethod:
    """Test the follow method for creating requests."""

    async def test_follow_absolute_url(self):
        crawler = MockCrawler()

        async def dummy_callback(request, response):
            pass

        request = await crawler.follow(
            URL("https://example.com/test"),
            dummy_callback
        )

        assert request is not None
        assert request.url == URL("https://example.com/test")
        assert request.callback == dummy_callback

    async def test_follow_relative_url_with_response(self):
        crawler = MockCrawler()

        # Create a mock response
        base_response = Response(
            url=URL("https://example.com/base"),
            method="GET",
            headers={},
            status_code=200,
            history=[URL("https://example.com")]
        )

        async def dummy_callback(request, response):
            pass

        request = await crawler.follow(
            "/relative/path",
            dummy_callback,
            response=base_response
        )

        assert request is not None
        assert request.url == URL("https://example.com/relative/path")

    async def test_follow_blocked_by_domain_filter(self):
        crawler = MockCrawler(allowed_domains=["allowed.com"])

        async def dummy_callback(request, response):
            pass

        request = await crawler.follow(
            URL("https://blocked.com/test"),
            dummy_callback
        )

        assert request is None  # Should be blocked

    async def test_follow_blocked_by_depth_limit(self):
        crawler = MockCrawler(max_depth=2)

        # Create a response with history at max depth
        base_response = Response(
            url=URL("https://example.com/deep"),
            method="GET",
            headers={},
            status_code=200,
            history=[URL("https://example.com"), URL("https://example.com/level1")]
        )

        async def dummy_callback(request, response):
            pass

        request = await crawler.follow(
            URL("https://example.com/too-deep"),
            dummy_callback,
            response=base_response
        )

        assert request is None  # Should be blocked by depth

    async def test_follow_with_custom_priority(self):
        crawler = MockCrawler()

        async def dummy_callback(request, response):
            pass

        request = await crawler.follow(
            URL("https://example.com/priority"),
            dummy_callback,
            priority=50
        )

        assert request is not None
        assert request.priority == 50


@pytest.mark.asyncio
class TestCrawlerWorkflow:
    """Test the complete crawler workflow."""

    async def test_crawler_initialization_creates_semaphores(self):
        # Use a very short timeout since we're just testing initialization
        crawler = MockCrawler(total_timeout=0.1)

        # Mock the session creation to avoid actual network setup
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session.closed = False

            with patch('aiohttp.TCPConnector'):
                await crawler.crawl(["https://example.com"])

        # Check that semaphores were created
        assert hasattr(crawler, '_download_semaphore')
        assert hasattr(crawler, '_parse_semaphore')
        assert crawler._download_semaphore._value == crawler.concurrency
        assert crawler._parse_semaphore._value == crawler.concurrency * 2

    async def test_worker_count_optimization(self):
        # Test different concurrency levels
        test_cases = [
            (1, 1),    # min(1 * 1.5, 20) = 1, max(1, 1) = 1
            (5, 7),    # min(5 * 1.5, 20) = 7, max(5, 7) = 7
            (10, 15),  # min(10 * 1.5, 20) = 15, max(10, 15) = 15
            (20, 20),  # min(20 * 1.5, 20) = 20, max(20, 20) = 20
        ]

        for concurrency, expected_workers in test_cases:
            crawler = MockCrawler(concurrency=concurrency)

            # Mock the session and connector
            with patch('aiohttp.ClientSession') as mock_session_class:
                with patch('aiohttp.TCPConnector'):
                    mock_session = AsyncMock()
                    mock_session_class.return_value = mock_session
                    mock_session.__aenter__.return_value = mock_session
                    mock_session.__aexit__.return_value = None
                    mock_session.closed = False

                    # Create a mock request queue
                    from feedsearch_crawler.crawler.lib import CrawlerPriorityQueue
                    mock_queue = AsyncMock(spec=CrawlerPriorityQueue)
                    mock_queue.join = AsyncMock()
                    crawler._request_queue = mock_queue

                    await crawler.crawl(["https://example.com"])

                    # Check worker count
                    assert len(crawler._workers) == expected_workers

    async def test_tcp_connector_configuration(self):
        crawler = MockCrawler(concurrency=5)

        with patch('aiohttp.TCPConnector') as mock_connector_class:
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_connector = MagicMock()
                mock_connector_class.return_value = mock_connector

                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                mock_session.__aenter__.return_value = mock_session
                mock_session.__aexit__.return_value = None
                mock_session.closed = False

                # Create a mock request queue
                from feedsearch_crawler.crawler.lib import CrawlerPriorityQueue
                mock_queue = AsyncMock(spec=CrawlerPriorityQueue)
                mock_queue.join = AsyncMock()
                crawler._request_queue = mock_queue

                await crawler.crawl(["https://example.com"])

                # Verify TCPConnector was called with optimization parameters
                mock_connector_class.assert_called_once()
                call_kwargs = mock_connector_class.call_args[1]

                assert call_kwargs['limit'] == 100
                assert call_kwargs['limit_per_host'] == 5  # matches concurrency
                assert call_kwargs['enable_cleanup_closed'] is True
                assert call_kwargs['keepalive_timeout'] == 30
                assert call_kwargs['force_close'] is False
                assert call_kwargs['use_dns_cache'] is True


@pytest.mark.asyncio
class TestCrawlerStatistics:
    """Test statistics collection and recording."""

    async def test_statistics_initialization(self):
        crawler = MockCrawler()

        # Check that all stat keys are initialized
        from feedsearch_crawler.crawler.lib import Stats
        for stat in Stats:
            assert stat in crawler.stats

        # Check initial values
        assert crawler.stats[Stats.REQUESTS_QUEUED] == 0
        assert crawler.stats[Stats.REQUESTS_SUCCESSFUL] == 0
        assert crawler.stats[Stats.REQUESTS_FAILED] == 0

    async def test_statistics_recording(self):
        crawler = MockCrawler()
        crawler.stats_collector.start()

        # Add some mock data using new stats collector
        await crawler.stats_collector.record_request_successful(
            status_code=200, duration_ms=100.0, latency_ms=50.0, content_length=1000
        )
        await crawler.stats_collector.record_request_successful(
            status_code=200, duration_ms=200.0, latency_ms=75.0, content_length=2000
        )
        await crawler.stats_collector.record_request_successful(
            status_code=200, duration_ms=300.0, latency_ms=60.0, content_length=1500
        )

        await crawler.stats_collector.stop()
        crawler.record_statistics()

        from feedsearch_crawler.crawler.lib import Stats

        # Check that statistics were calculated
        assert crawler.stats[Stats.CONTENT_LENGTH_TOTAL] == 4500
        assert crawler.stats[Stats.REQUESTS_SUCCESSFUL] == 3

        # Check that get_stats returns a grouped dictionary
        stats_dict = crawler.get_stats()
        assert isinstance(stats_dict, dict)
        assert "summary" in stats_dict
        assert "requests" in stats_dict


class TestCrawlerRequestProcessing:
    """Test request processing and queueing."""

    def test_process_request_adds_to_queue(self):
        crawler = MockCrawler()

        # Mock the queue
        with patch.object(crawler, '_put_queue') as mock_put_queue:
            request = Request(url=URL("https://example.com"))
            crawler._process_request(request)

            mock_put_queue.assert_called_once_with(request)
            crawler.record_statistics()
            assert crawler.stats[Stats.REQUESTS_QUEUED] == 1

    def test_process_request_handles_none(self):
        crawler = MockCrawler()

        # Should not crash with None request
        with patch.object(crawler, '_put_queue') as mock_put_queue:
            crawler._process_request(None)
            mock_put_queue.assert_not_called()


@pytest.mark.asyncio
class TestCrawlerCallbackHandling:
    """Test callback result processing."""

    async def test_process_callback_result_with_item(self):
        crawler = MockCrawler()
        item = MockItem("test-data")

        await crawler._process_request_callback_result(item)

        assert len(crawler.processed_items) == 1
        assert crawler.processed_items[0] == item
        crawler.record_statistics()
        assert crawler.stats[Stats.ITEMS_PROCESSED] == 1

    async def test_process_callback_result_with_request(self):
        crawler = MockCrawler()
        request = Request(url=URL("https://example.com"))

        with patch.object(crawler, '_process_request') as mock_process:
            await crawler._process_request_callback_result(request)
            mock_process.assert_called_once_with(request)

    async def test_callback_recursion_limit(self):
        crawler = MockCrawler()

        # Create a deeply nested callback result that would cause recursion
        from feedsearch_crawler.crawler.queueable import CallbackResult
        deep_result = CallbackResult(MockItem("test"), callback_recursion=20)

        # Should handle gracefully without infinite recursion
        await crawler._process_request_callback_result(deep_result)

        # Item should not be processed due to recursion limit
        assert len(crawler.processed_items) == 0