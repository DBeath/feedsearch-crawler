"""Tests for RetryMiddleware."""

import pytest

from feedsearch_crawler.crawler.middleware.retry import RetryMiddleware
from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response
from feedsearch_crawler.crawler.exceptions import RetryRequestException
from yarl import URL


class TestRetryMiddleware:
    """Test retry middleware functionality."""

    def test_middleware_initialization_default(self):
        """Test default initialization."""
        middleware = RetryMiddleware()
        assert middleware.max_retries == 3
        assert middleware.retry_statuses == [429, 500, 502, 503, 504]

    def test_middleware_initialization_custom(self):
        """Test custom initialization."""
        middleware = RetryMiddleware(max_retries=5, retry_statuses=[429, 503])
        assert middleware.max_retries == 5
        assert middleware.retry_statuses == [429, 503]

    @pytest.mark.asyncio
    async def test_retry_on_retriable_status_codes(self):
        """Test that retry is triggered for retriable status codes."""
        middleware = RetryMiddleware(max_retries=3)

        request = Request(url=URL("https://example.com"))
        request.retries = 0

        retriable_codes = [429, 500, 502, 503, 504]

        for status_code in retriable_codes:
            # Create fresh request for each test
            fresh_request = Request(url=URL("https://example.com"))
            fresh_request.retries = 0

            response = Response(
                url=URL("https://example.com"),
                method="GET",
                headers={},
                status_code=status_code,
                history=[],
                request=fresh_request,
            )

            with pytest.raises(RetryRequestException):
                await middleware.process_response(response)

            assert fresh_request.retries == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retriable_status_codes(self):
        """Test that retry is not triggered for non-retriable status codes."""
        middleware = RetryMiddleware()

        request = Request(url=URL("https://example.com"))
        request.retries = 0

        non_retriable_codes = [200, 201, 301, 302, 400, 401, 403, 404, 410]

        for status_code in non_retriable_codes:
            fresh_request = Request(url=URL("https://example.com"))
            fresh_request.retries = 0

            response = Response(
                url=URL("https://example.com"),
                method="GET",
                headers={},
                status_code=status_code,
                history=[],
                request=fresh_request,
            )

            # Should not raise exception
            await middleware.process_response(response)
            assert fresh_request.retries == 0

    @pytest.mark.asyncio
    async def test_no_retry_when_max_retries_reached(self):
        """Test that retry is not attempted when max retries is reached."""
        middleware = RetryMiddleware(max_retries=2)

        request = Request(url=URL("https://example.com"))
        request.retries = 2  # Already at max

        response = Response(
            url=URL("https://example.com"),
            method="GET",
            headers={},
            status_code=503,  # Normally retriable
            history=[],
            request=request,
        )

        # Should not raise RetryRequestException
        await middleware.process_response(response)
        assert request.retries == 2  # Should not increment

    @pytest.mark.asyncio
    async def test_retry_increments_counter(self):
        """Test that retry attempts increment the retry counter."""
        middleware = RetryMiddleware(max_retries=3)

        request = Request(url=URL("https://example.com"))
        request.retries = 1

        response = Response(
            url=URL("https://example.com"),
            method="GET",
            headers={},
            status_code=429,
            history=[],
            request=request,
        )

        with pytest.raises(RetryRequestException) as exc_info:
            await middleware.process_response(response)

        assert request.retries == 2
        assert exc_info.value.request == request

    @pytest.mark.asyncio
    async def test_custom_retry_status_codes(self):
        """Test custom retry status codes configuration."""
        # Only retry on 429 (rate limit)
        middleware = RetryMiddleware(max_retries=2, retry_statuses=[429])

        request = Request(url=URL("https://example.com"))
        request.retries = 0

        # Should retry on 429
        response_429 = Response(
            url=URL("https://example.com"),
            method="GET",
            headers={},
            status_code=429,
            history=[],
            request=request,
        )

        with pytest.raises(RetryRequestException):
            await middleware.process_response(response_429)

        # Should NOT retry on 503 (not in custom list)
        fresh_request = Request(url=URL("https://example.com"))
        fresh_request.retries = 0

        response_503 = Response(
            url=URL("https://example.com"),
            method="GET",
            headers={},
            status_code=503,
            history=[],
            request=fresh_request,
        )

        # Should not raise exception
        await middleware.process_response(response_503)
        assert fresh_request.retries == 0

    @pytest.mark.asyncio
    async def test_retry_exception_contains_request(self):
        """Test that RetryRequestException contains the correct request."""
        middleware = RetryMiddleware()

        request = Request(url=URL("https://example.com/special"))
        request.retries = 0

        response = Response(
            url=URL("https://example.com/special"),
            method="GET",
            headers={},
            status_code=503,
            history=[],
            request=request,
        )

        with pytest.raises(RetryRequestException) as exc_info:
            await middleware.process_response(response)

        exception = exc_info.value
        assert exception.request == request
        assert exception.request.url == URL("https://example.com/special")

    @pytest.mark.asyncio
    async def test_multiple_retry_attempts(self):
        """Test multiple retry attempts until max is reached."""
        middleware = RetryMiddleware(max_retries=3)

        request = Request(url=URL("https://example.com"))
        request.retries = 0

        # Simulate multiple retry attempts
        for expected_retries in range(1, 4):  # 1, 2, 3
            response = Response(
                url=URL("https://example.com"),
                method="GET",
                headers={},
                status_code=503,
                history=[],
                request=request,
            )

            with pytest.raises(RetryRequestException):
                await middleware.process_response(response)

            assert request.retries == expected_retries

        # Fourth attempt should not retry (max reached)
        final_response = Response(
            url=URL("https://example.com"),
            method="GET",
            headers={},
            status_code=503,
            history=[],
            request=request,
        )

        # Should not raise exception
        await middleware.process_response(final_response)
        assert request.retries == 3  # Should not increment further

    @pytest.mark.asyncio
    async def test_pre_request_method(self):
        """Test that pre_request method doesn't interfere."""
        middleware = RetryMiddleware()
        request = Request(url=URL("https://example.com"))

        # Should not raise exceptions
        await middleware.pre_request(request)

    @pytest.mark.asyncio
    async def test_process_request_method(self):
        """Test that process_request method doesn't interfere."""
        middleware = RetryMiddleware()
        request = Request(url=URL("https://example.com"))

        # Should not raise exceptions
        await middleware.process_request(request)

    @pytest.mark.asyncio
    async def test_process_exception_method(self):
        """Test that process_exception method doesn't interfere."""
        middleware = RetryMiddleware()
        request = Request(url=URL("https://example.com"))
        exception = Exception("test exception")

        # Should not raise exceptions
        await middleware.process_exception(request, exception)

    @pytest.mark.asyncio
    async def test_edge_case_zero_retries_allowed(self):
        """Test edge case where no retries are allowed."""
        middleware = RetryMiddleware(max_retries=0)

        request = Request(url=URL("https://example.com"))
        request.retries = 0

        response = Response(
            url=URL("https://example.com"),
            method="GET",
            headers={},
            status_code=503,
            history=[],
            request=request,
        )

        # Should not retry even on retriable status
        await middleware.process_response(response)
        assert request.retries == 0

    @pytest.mark.asyncio
    async def test_edge_case_negative_retries(self):
        """Test edge case with negative retry count (shouldn't happen but test for robustness)."""
        middleware = RetryMiddleware(max_retries=3)

        request = Request(url=URL("https://example.com"))
        request.retries = -1  # Edge case

        response = Response(
            url=URL("https://example.com"),
            method="GET",
            headers={},
            status_code=503,
            history=[],
            request=request,
        )

        with pytest.raises(RetryRequestException):
            await middleware.process_response(response)

        assert request.retries == 0  # Should increment to 0
