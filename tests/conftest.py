"""Shared test fixtures and configuration for feedsearch-crawler tests."""

import asyncio
import json
from typing import Dict, Optional
from unittest.mock import AsyncMock

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from yarl import URL

from feedsearch_crawler.crawler.crawler import Crawler
from feedsearch_crawler.feed_spider.spider import FeedsearchSpider


@pytest.fixture
def sample_rss_feed() -> str:
    """Sample RSS 2.0 feed for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test RSS Feed</title>
        <link>https://example.com</link>
        <description>A test RSS feed</description>
        <item>
            <title>Test Item 1</title>
            <link>https://example.com/item1</link>
            <description>First test item</description>
            <pubDate>Wed, 01 Jan 2025 12:00:00 GMT</pubDate>
        </item>
        <item>
            <title>Test Item 2</title>
            <link>https://example.com/item2</link>
            <description>Second test item</description>
            <pubDate>Thu, 02 Jan 2025 12:00:00 GMT</pubDate>
        </item>
    </channel>
</rss>"""


@pytest.fixture
def sample_atom_feed() -> str:
    """Sample Atom 1.0 feed for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>Test Atom Feed</title>
    <link href="https://example.com"/>
    <updated>2025-01-01T12:00:00Z</updated>
    <author><name>Test Author</name></author>
    <id>urn:uuid:12345678-1234-1234-1234-123456789abc</id>
    <entry>
        <title>Test Entry 1</title>
        <link href="https://example.com/entry1"/>
        <id>urn:uuid:87654321-4321-4321-4321-cba987654321</id>
        <updated>2025-01-01T12:00:00Z</updated>
        <summary>First test entry</summary>
    </entry>
</feed>"""


@pytest.fixture
def sample_json_feed() -> str:
    """Sample JSON Feed for testing."""
    return json.dumps({
        "version": "https://jsonfeed.org/version/1",
        "title": "Test JSON Feed",
        "home_page_url": "https://example.com",
        "feed_url": "https://example.com/feed.json",
        "items": [
            {
                "id": "1",
                "title": "Test JSON Item",
                "url": "https://example.com/json-item1",
                "summary": "First JSON test item",
                "date_published": "2025-01-01T12:00:00Z"
            }
        ]
    })


@pytest.fixture
def sample_html_with_feeds() -> str:
    """Sample HTML page with feed links."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Test Site</title>
    <link rel="alternate" type="application/rss+xml" title="RSS Feed" href="/rss.xml">
    <link rel="alternate" type="application/atom+xml" title="Atom Feed" href="/atom.xml">
    <link rel="alternate" type="application/json" title="JSON Feed" href="/feed.json">
    <link rel="icon" href="/favicon.ico">
</head>
<body>
    <h1>Test Website</h1>
    <p>This is a test website with feed links.</p>
</body>
</html>"""


@pytest.fixture
def sample_robots_txt() -> str:
    """Sample robots.txt for testing."""
    return """User-agent: *
Disallow: /private/
Disallow: /admin/
Allow: /

User-agent: Feedsearch-Crawler
Allow: /
Crawl-delay: 1
"""


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(
        self,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        text: str = "",
        json_data: Optional[Dict] = None,
        url: str = "https://example.com",
        content_type: str = "text/html",
    ):
        self.status = status
        self.headers = headers or {"Content-Type": content_type}
        self._text = text
        self._json = json_data or {}
        self.url = URL(url)
        self.method = "GET"
        self._body = text.encode() if text else b""
        self.cookies = {}
        self.history = []
        self.closed = False

    async def text(self, encoding: str = "utf-8") -> str:
        return self._text

    async def json(self) -> Dict:
        return self._json

    def get_encoding(self) -> str:
        return "utf-8"

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=aiohttp.RequestInfo(
                    url=self.url, method=self.method, headers={}, real_url=self.url
                ),
                history=(),
                status=self.status,
                message=f"HTTP {self.status}",
                headers=self.headers,
            )

    def close(self) -> None:
        self.closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()


@pytest.fixture
async def mock_test_server():
    """Create a mock test server for HTTP testing."""
    app = web.Application()

    async def html_handler(request: web.Request) -> web.Response:
        html = """<!DOCTYPE html>
<html><head><title>Test</title>
<link rel="alternate" type="application/rss+xml" href="/rss.xml">
</head><body>Test</body></html>"""
        return web.Response(text=html, content_type="text/html")

    async def rss_handler(request: web.Request) -> web.Response:
        rss = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Test Feed</title><link>https://example.com</link>
<item><title>Test Item</title></item>
</channel></rss>"""
        return web.Response(text=rss, content_type="application/rss+xml")

    async def json_handler(request: web.Request) -> web.Response:
        return web.json_response({"message": "test"})

    async def error_handler(request: web.Request) -> web.Response:
        return web.Response(status=500, text="Server Error")

    async def slow_handler(request: web.Request) -> web.Response:
        await asyncio.sleep(0.5)
        return web.Response(text="slow")

    app.router.add_get("/", html_handler)
    app.router.add_get("/rss.xml", rss_handler)
    app.router.add_get("/api/test", json_handler)
    app.router.add_get("/error", error_handler)
    app.router.add_get("/slow", slow_handler)

    server = TestServer(app)
    await server.start_server()
    yield server
    await server.close()


@pytest.fixture
def mock_session():
    """Create a mock aiohttp ClientSession."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.closed = False

    async def mock_get(*args, **kwargs):
        return MockResponse()

    session.get = AsyncMock(side_effect=mock_get)
    session.post = AsyncMock(side_effect=mock_get)
    session.put = AsyncMock(side_effect=mock_get)
    session.delete = AsyncMock(side_effect=mock_get)
    session.close = AsyncMock()

    return session


class MockCrawler(Crawler):
    """Reusable mock implementation of abstract Crawler for testing."""

    def __init__(self, **kwargs):
        # Set default test timeout if not specified
        if 'total_timeout' not in kwargs:
            kwargs['total_timeout'] = 0.5
        super().__init__(**kwargs)
        self.processed_items = []
        self.parsed_responses = []

    async def process_item(self, item):
        self.processed_items.append(item)

    async def parse_xml(self, response_text: str):
        return {"parsed": True, "content": response_text[:100]}

    async def parse_response(self, request, response):
        self.parsed_responses.append((request, response))
        if response.ok:
            yield f"Item from {response.url}"


@pytest.fixture
async def crawler_instance():
    """Create a test crawler instance."""
    return MockCrawler(
        concurrency=2,
        total_timeout=5.0,
        request_timeout=2.0
    )


@pytest.fixture
async def feedsearch_spider():
    """Create a test FeedsearchSpider instance."""
    spider = FeedsearchSpider(
        concurrency=2,
        total_timeout=5.0,
        request_timeout=2.0
    )
    return spider


@pytest.fixture
def mock_dns_resolution():
    """Mock DNS resolution to avoid network calls."""
    import socket

    def mock_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        # Return localhost for all domains
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', port))]

    original = socket.getaddrinfo
    socket.getaddrinfo = mock_getaddrinfo
    yield
    socket.getaddrinfo = original


@pytest.fixture(autouse=True)
def no_network_calls(monkeypatch):
    """Prevent any real network calls during testing, except to localhost."""
    original_request = aiohttp.ClientSession._request

    async def mock_request(self, method, url, **kwargs):
        # Allow requests to localhost and 127.0.0.1 for test servers
        if hasattr(url, 'host') and url.host in ('localhost', '127.0.0.1'):
            return await original_request(self, method, url, **kwargs)
        elif isinstance(url, str) and ('localhost' in url or '127.0.0.1' in url):
            return await original_request(self, method, url, **kwargs)
        else:
            raise RuntimeError("Real network calls are not allowed in tests!")

    monkeypatch.setattr(aiohttp.ClientSession, "_request", mock_request)