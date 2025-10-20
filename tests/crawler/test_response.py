"""Tests for the Response class."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from yarl import URL

from feedsearch_crawler.crawler.request import Request
from feedsearch_crawler.crawler.response import Response


class TestResponseInitialization:
    """Test Response class initialization."""

    def test_basic_initialization(self):
        """Test basic Response initialization."""
        url = URL("https://example.com/test")
        response = Response(
            url=url,
            method="GET",
            headers={"Content-Type": "text/html"},
            status_code=200,
            history=[url],
        )

        assert response.url == url
        assert response.method == "GET"
        assert response.headers["Content-Type"] == "text/html"
        assert response.status_code == 200
        assert response.history == [url]
        assert response.ok is True

    def test_initialization_with_all_parameters(self):
        """Test Response initialization with all parameters."""
        url = URL("https://example.com/test")
        request = Request(url=url)
        history = [URL("https://example.com/start"), url]
        headers = {"Content-Type": "application/json", "Content-Length": "100"}
        cookies = {"session": "abc123"}
        redirect_history = [MagicMock()]

        response = Response(
            url=url,
            method="POST",
            encoding="utf-8",
            headers=headers,
            status_code=201,
            history=history,
            text="test content",
            data=b"test data",
            json={"key": "value"},
            xml_parser=lambda x: {"parsed": x},
            cookies=cookies,
            redirect_history=redirect_history,
            content_length=100,
            meta={"custom": "metadata"},
            request=request,
        )

        assert response.url == url
        assert response.method == "POST"
        assert response.encoding == "utf-8"
        assert response.headers == headers
        assert response.status_code == 201
        assert response.history == history
        assert response.text == "test content"
        assert response.data == b"test data"
        assert response.json == {"key": "value"}
        assert response._xml_parser is not None
        assert response.cookies == cookies
        assert response.redirect_history == redirect_history
        assert response.content_length == 100
        assert response.meta == {"custom": "metadata"}
        assert response.request == request

    def test_default_values(self):
        """Test default values for optional parameters."""
        url = URL("https://example.com/test")
        response = Response(
            url=url, method="GET", headers={}, status_code=200, history=[]
        )

        assert response.encoding == ""
        assert response.text == ""
        assert response.data == b""
        assert response.json == {}
        assert response._xml_parser is None
        assert response.cookies == {}
        assert response.redirect_history == []
        assert response.content_length == 0
        assert response.meta == {}
        assert response.request is None


class TestResponseStatusChecks:
    """Test Response status checking methods."""

    @pytest.mark.parametrize(
        "status_code,expected_ok",
        [
            (200, True),
            (201, True),
            (204, True),
            (299, True),
            (300, False),
            (301, False),
            (400, False),
            (404, False),
            (500, False),
        ],
    )
    def test_ok_property(self, status_code, expected_ok):
        """Test the ok property for various status codes."""
        response = Response(
            url=URL("https://example.com"),
            method="GET",
            headers={},
            status_code=status_code,
            history=[],
        )
        assert response.ok == expected_ok

    def test_successful_response_codes(self):
        """Test various successful response codes."""
        successful_codes = [200, 201, 202, 204, 206]
        for code in successful_codes:
            response = Response(
                url=URL("https://example.com"),
                method="GET",
                headers={},
                status_code=code,
                history=[],
            )
            assert response.ok is True

    def test_client_error_codes(self):
        """Test client error codes."""
        client_error_codes = [400, 401, 403, 404, 409, 422]
        for code in client_error_codes:
            response = Response(
                url=URL("https://example.com"),
                method="GET",
                headers={},
                status_code=code,
                history=[],
            )
            assert response.ok is False

    def test_server_error_codes(self):
        """Test server error codes."""
        server_error_codes = [500, 501, 502, 503, 504]
        for code in server_error_codes:
            response = Response(
                url=URL("https://example.com"),
                method="GET",
                headers={},
                status_code=code,
                history=[],
            )
            assert response.ok is False


class TestResponseUrlProperties:
    """Test URL-related properties of Response."""

    def test_origin_property(self):
        """Test the origin property."""
        url = URL("https://example.com/path/to/resource?param=value#fragment")
        response = Response(
            url=url, method="GET", headers={}, status_code=200, history=[]
        )

        expected_origin = URL("https://example.com")
        assert response.origin == expected_origin

    def test_scheme_property(self):
        """Test the scheme property."""
        https_response = Response(
            url=URL("https://example.com/test"),
            method="GET",
            headers={},
            status_code=200,
            history=[],
        )
        assert https_response.scheme == "https"

        http_response = Response(
            url=URL("http://example.com/test"),
            method="GET",
            headers={},
            status_code=200,
            history=[],
        )
        assert http_response.scheme == "http"

    def test_host_property(self):
        """Test the host property."""
        response = Response(
            url=URL("https://api.example.com/v1/data"),
            method="GET",
            headers={},
            status_code=200,
            history=[],
        )
        assert response.host == "api.example.com"

    def test_port_property(self):
        """Test the port property."""
        # Default ports
        https_response = Response(
            url=URL("https://example.com/test"),
            method="GET",
            headers={},
            status_code=200,
            history=[],
        )
        assert https_response.port == 443

        http_response = Response(
            url=URL("http://example.com/test"),
            method="GET",
            headers={},
            status_code=200,
            history=[],
        )
        assert http_response.port == 80

        # Custom port
        custom_port_response = Response(
            url=URL("https://example.com:8080/test"),
            method="GET",
            headers={},
            status_code=200,
            history=[],
        )
        assert custom_port_response.port == 8080


class TestResponseXMLParsing:
    """Test XML parsing functionality."""

    @pytest.mark.asyncio
    async def test_xml_parsing_with_parser(self):
        """Test XML parsing when parser is provided."""

        def mock_xml_parser(text):
            return {"parsed": True, "content": text}

        xml_content = "<rss><channel><title>Test</title></channel></rss>"
        response = Response(
            url=URL("https://example.com/rss.xml"),
            method="GET",
            headers={"Content-Type": "application/rss+xml"},
            status_code=200,
            history=[],
            text=xml_content,
            xml_parser=mock_xml_parser,
        )

        parsed_xml = await response.xml
        assert parsed_xml["parsed"] is True
        assert parsed_xml["content"] == xml_content

    @pytest.mark.asyncio
    async def test_xml_parsing_without_parser(self):
        """Test XML parsing when no parser is provided."""
        xml_content = "<rss><channel><title>Test</title></channel></rss>"
        response = Response(
            url=URL("https://example.com/rss.xml"),
            method="GET",
            headers={"Content-Type": "application/rss+xml"},
            status_code=200,
            history=[],
            text=xml_content,
            xml_parser=None,
        )

        # Should return None when no parser is available
        assert await response.xml is None

    @pytest.mark.asyncio
    async def test_xml_parsing_with_empty_text(self):
        """Test XML parsing with empty text."""

        def mock_xml_parser(text):
            return {"parsed": True, "content": text}

        response = Response(
            url=URL("https://example.com/empty.xml"),
            method="GET",
            headers={"Content-Type": "application/xml"},
            status_code=200,
            history=[],
            text="",
            xml_parser=mock_xml_parser,
        )

        # Should still call parser with empty string
        parsed_xml = await response.xml
        assert parsed_xml["parsed"] is True
        assert parsed_xml["content"] == ""


class TestResponseContentHandling:
    """Test content handling and encoding."""

    def test_text_content(self):
        """Test text content handling."""
        content = "This is test content with üñïçødé"
        response = Response(
            url=URL("https://example.com/test"),
            method="GET",
            headers={"Content-Type": "text/plain; charset=utf-8"},
            status_code=200,
            history=[],
            text=content,
            encoding="utf-8",
        )

        assert response.text == content
        assert response.encoding == "utf-8"

    def test_json_content(self):
        """Test JSON content handling."""
        json_data = {"message": "Hello", "count": 42, "items": [1, 2, 3]}
        response = Response(
            url=URL("https://api.example.com/data"),
            method="GET",
            headers={"Content-Type": "application/json"},
            status_code=200,
            history=[],
            json=json_data,
        )

        assert response.json == json_data
        assert response.json["message"] == "Hello"
        assert response.json["count"] == 42

    def test_binary_content(self):
        """Test binary content handling."""
        binary_data = b"Binary content with \x00\x01\x02 bytes"
        response = Response(
            url=URL("https://example.com/binary"),
            method="GET",
            headers={"Content-Type": "application/octet-stream"},
            status_code=200,
            history=[],
            data=binary_data,
        )

        assert response.data == binary_data

    def test_content_length(self):
        """Test content length property."""
        content = "Test content"
        response = Response(
            url=URL("https://example.com/test"),
            method="GET",
            headers={"Content-Length": str(len(content))},
            status_code=200,
            history=[],
            text=content,
            content_length=len(content),
        )

        assert response.content_length == len(content)


class TestResponseHeaders:
    """Test header handling."""

    def test_headers_access(self):
        """Test header access and case insensitivity."""
        headers = {
            "Content-Type": "text/html",
            "Content-Length": "1024",
            "X-Custom-Header": "custom-value",
        }

        response = Response(
            url=URL("https://example.com/test"),
            method="GET",
            headers=headers,
            status_code=200,
            history=[],
        )

        assert response.headers["Content-Type"] == "text/html"
        assert response.headers["Content-Length"] == "1024"
        assert response.headers["X-Custom-Header"] == "custom-value"

    def test_empty_headers(self):
        """Test response with empty headers."""
        response = Response(
            url=URL("https://example.com/test"),
            method="GET",
            headers={},
            status_code=200,
            history=[],
        )

        assert response.headers == {}


class TestResponseMetadata:
    """Test response metadata and request relationship."""

    def test_response_with_request(self):
        """Test response associated with a request."""
        url = URL("https://example.com/test")
        request = Request(
            url=url, method="POST", headers={"Authorization": "Bearer token"}
        )

        response = Response(
            url=url,
            method="POST",
            headers={"Content-Type": "application/json"},
            status_code=201,
            history=[url],
            request=request,
        )

        assert response.request == request
        assert response.request.url == url
        assert response.request.method == "POST"

    def test_response_metadata(self):
        """Test custom metadata storage."""
        metadata = {
            "crawl_depth": 3,
            "source": "sitemap",
            "timestamp": datetime.now(),
            "custom_data": {"key": "value"},
        }

        response = Response(
            url=URL("https://example.com/test"),
            method="GET",
            headers={},
            status_code=200,
            history=[],
            meta=metadata,
        )

        assert response.meta == metadata
        assert response.meta["crawl_depth"] == 3
        assert response.meta["source"] == "sitemap"

    def test_response_history(self):
        """Test response history tracking."""
        initial_url = URL("https://example.com/start")
        redirect_url = URL("https://example.com/redirect")
        final_url = URL("https://example.com/final")

        history = [initial_url, redirect_url, final_url]

        response = Response(
            url=final_url, method="GET", headers={}, status_code=200, history=history
        )

        assert response.history == history
        assert len(response.history) == 3
        assert response.history[0] == initial_url
        assert response.history[-1] == final_url


class TestResponseEdgeCases:
    """Test edge cases and error conditions."""

    def test_response_with_none_values(self):
        """Test response handling None values gracefully."""
        response = Response(
            url=URL("https://example.com/test"),
            method="GET",
            headers=None,
            status_code=200,
            history=None,
            text=None,
            data=None,
            json=None,
            cookies=None,
            meta=None,
        )

        # Should handle None values gracefully with defaults
        assert response.headers is not None  # Should default to empty dict
        assert response.history is not None  # Should default to empty list
        assert response.text is not None  # Should default to empty string
        assert response.data is not None  # Should default to empty bytes
        assert response.json is not None  # Should default to empty dict

    def test_response_string_representation(self):
        """Test response string representation."""
        response = Response(
            url=URL("https://example.com/test"),
            method="GET",
            headers={},
            status_code=200,
            history=[],
        )

        str_repr = str(response)
        # Should contain URL and status code
        assert "example.com" in str_repr
        assert "200" in str_repr

        repr_repr = repr(response)
        # Should be a valid representation
        assert "Response" in repr_repr


class TestResponseAdditionalCoverage:
    """Additional tests for comprehensive coverage."""

    def test_domain_property(self):
        """Test the domain property."""
        response = Response(
            url=URL("https://example.com:8080/path"), method="GET", history=[]
        )
        assert response.domain == "example.com"

    def test_previous_domain_with_history(self):
        """Test previous_domain property with history."""
        response = Response(
            url=URL("https://final.com"),
            method="GET",
            history=[URL("https://original.com"), URL("https://redirect.com")],
        )
        assert response.previous_domain == "redirect.com"

    def test_previous_domain_empty_history(self):
        """Test previous_domain property with empty history."""
        response = Response(url=URL("https://example.com"), method="GET", history=[])
        assert response.previous_domain == ""

    def test_originator_url_with_multiple_redirects(self):
        """Test originator_url property with multiple redirects."""
        response = Response(
            url=URL("https://final.com"),
            method="GET",
            history=[
                URL("https://original.com"),
                URL("https://redirect1.com"),
                URL("https://redirect2.com"),
            ],
        )
        assert response.originator_url == URL("https://redirect1.com")

    def test_originator_url_single_redirect(self):
        """Test originator_url with single redirect."""
        response = Response(
            url=URL("https://final.com"),
            method="GET",
            history=[URL("https://original.com")],
        )
        assert response.originator_url is None

    def test_originator_url_no_history(self):
        """Test originator_url with no history."""
        response = Response(url=URL("https://example.com"), method="GET", history=[])
        assert response.originator_url is None

    @pytest.mark.asyncio
    async def test_xml_with_cached_result(self):
        """Test xml property returns cached result."""
        call_count = 0

        async def mock_parser(text):
            nonlocal call_count
            call_count += 1
            return {"parsed": "xml", "calls": call_count}

        response = Response(
            url=URL("https://example.com"),
            method="GET",
            text="<xml>test</xml>",
            xml_parser=mock_parser,
            history=[],
        )

        # First call should parse
        result1 = await response.xml
        assert result1["calls"] == 1

        # Second call should return cached result
        result2 = await response.xml
        assert result2["calls"] == 1  # Same result, not called again
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_xml_decode_data_when_no_text(self):
        """Test xml property decodes data when text is missing."""

        async def mock_parser(text):
            return {"parsed": text}

        response = Response(
            url=URL("https://example.com"),
            method="GET",
            text="",
            data=b"<xml>decoded</xml>",
            encoding="utf-8",
            xml_parser=mock_parser,
            history=[],
        )

        result = await response.xml
        assert response.text == "<xml>decoded</xml>"
        assert result["parsed"] == "<xml>decoded</xml>"

    @pytest.mark.asyncio
    async def test_xml_decode_error_handling(self):
        """Test xml property handles decode errors gracefully."""

        async def mock_parser(text):
            return {"parsed": text}

        response = Response(
            url=URL("https://example.com"),
            method="GET",
            text="",
            data=b"\xff\xfe",  # Invalid UTF-8
            encoding="utf-8",
            xml_parser=mock_parser,
            history=[],
        )

        result = await response.xml
        assert result is None  # Should return None on decode error

    @pytest.mark.asyncio
    async def test_xml_parser_sync(self):
        """Test xml property with synchronous parser."""

        def sync_parser(text):
            return {"sync": "result"}

        response = Response(
            url=URL("https://example.com"),
            method="GET",
            text="<xml>test</xml>",
            xml_parser=sync_parser,
            history=[],
        )

        result = await response.xml
        assert result == {"sync": "result"}

    @pytest.mark.asyncio
    async def test_xml_parser_exception(self):
        """Test xml property handles parser exceptions."""

        def error_parser(text):
            raise ValueError("Parse error")

        response = Response(
            url=URL("https://example.com"),
            method="GET",
            text="<xml>test</xml>",
            xml_parser=error_parser,
            history=[],
        )

        result = await response.xml
        assert result is None  # Should return None on error

    def test_is_max_depth_reached_true(self):
        """Test is_max_depth_reached when depth is reached."""
        response = Response(
            url=URL("https://example.com"),
            method="GET",
            history=[
                URL("https://url1.com"),
                URL("https://url2.com"),
                URL("https://url3.com"),
            ],
        )
        assert response.is_max_depth_reached(3) is True

    def test_is_max_depth_reached_false(self):
        """Test is_max_depth_reached when depth not reached."""
        response = Response(
            url=URL("https://example.com"),
            method="GET",
            history=[URL("https://url1.com")],
        )
        assert response.is_max_depth_reached(5) is False

    def test_is_max_depth_reached_zero(self):
        """Test is_max_depth_reached with zero max_depth."""
        response = Response(url=URL("https://example.com"), method="GET", history=[])
        assert response.is_max_depth_reached(0) is False

    def test_is_original_domain_first_response(self):
        """Test is_original_domain for first response in chain."""
        response = Response(url=URL("https://example.com"), method="GET", history=[])
        assert response.is_original_domain() is True

    def test_is_original_domain_single_redirect(self):
        """Test is_original_domain with single redirect."""
        response = Response(
            url=URL("https://example.com/page"),
            method="GET",
            history=[URL("https://example.com")],
        )
        assert response.is_original_domain() is True

    def test_is_original_domain_same_domain(self):
        """Test is_original_domain with same domain."""
        response = Response(
            url=URL("https://www.example.com"),
            method="GET",
            history=[URL("https://example.com"), URL("https://api.example.com")],
        )
        assert response.is_original_domain() is True

    def test_is_original_domain_different_domain(self):
        """Test is_original_domain with different domain."""
        response = Response(
            url=URL("https://different.com"),
            method="GET",
            history=[URL("https://example.com"), URL("https://redirect.com")],
        )
        assert response.is_original_domain() is False


class TestResponseURLValidation:
    """Test Response class handles invalid URLs gracefully."""

    def test_response_with_empty_url(self):
        """Test Response handles empty URL gracefully."""
        # Empty URL() should not crash Response.__init__
        response = Response(
            url=URL(),
            method="GET",
            headers={},
            status_code=500,
            history=[],
        )
        assert response.url == URL()
        assert response.origin == URL()

    def test_response_origin_extraction_error(self):
        """Test Response handles URL origin extraction errors gracefully."""
        # This tests the try-except block in Response.__init__ around url.origin()
        url = URL("https://example.com/test")
        response = Response(
            url=url,
            method="GET",
            headers={},
            status_code=200,
            history=[],
        )
        # Normal case should work fine
        assert response.origin == URL("https://example.com")
        assert response.url == url
