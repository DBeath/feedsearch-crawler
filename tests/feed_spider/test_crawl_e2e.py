"""End-to-end crawl tests against a local aiohttp server.

These exercise the full crawl loop (queue -> workers -> downloader ->
middleware -> parser -> items) with real HTTP requests to localhost. They
exist to catch failures that unit tests with mocked internals cannot see,
such as workers dying silently and the crawl idling until total_timeout.
"""

import asyncio
import time

from aiohttp import web

from feedsearch_crawler.feed_spider.spider import FeedsearchSpider

RSS = (
    '<?xml version="1.0"?><rss version="2.0"><channel><title>E2E Feed</title>'
    "<link>/</link><description>D</description>"
    "<item><title>Item 1</title></item></channel></rss>"
)

HOME = (
    "<html><head><title>E2E Site</title>"
    '<link rel="alternate" type="application/rss+xml" href="/feed.xml">'
    '<link rel="icon" href="/favicon.png">'
    "</head><body>"
    + "".join(f'<a href="/page{i}">page {i}</a>' for i in range(5))
    + "</body></html>"
)

PAGE = "<html><head><title>Page</title></head><body>nothing here</body></html>"

JSON_FEED = (
    '{"version": "https://jsonfeed.org/version/1.1", "title": "E2E JSON Feed", '
    '"home_page_url": "/", "feed_url": "/feed.json", '
    '"items": [{"id": "1", "title": "Item 1", "content_text": "hi"}]}'
)

# A home page that declares a JSON Feed and a site icon.
JSON_HOME = (
    "<html><head><title>E2E JSON Site</title>"
    '<link rel="alternate" type="application/feed+json" href="/feed.json">'
    "</head><body></body></html>"
)

# Smallest valid PNG header; the spider only checks the magic bytes.
PNG = bytes.fromhex("89504E470D0A1A0A") + b"\x00" * 16


def _build_app(robots_txt: str) -> web.Application:
    def text_handler(text: str, content_type: str):
        async def handler(request):
            return web.Response(text=text, content_type=content_type)

        return handler

    def brotli_handler(text: str, content_type: str):
        async def handler(request):
            import brotli

            assert "br" in request.headers.get("Accept-Encoding", ""), (
                "client must advertise brotli support"
            )
            return web.Response(
                body=brotli.compress(text.encode()),
                content_type=content_type,
                headers={"Content-Encoding": "br"},
            )

        return handler

    app = web.Application()
    app.router.add_get("/robots.txt", text_handler(robots_txt, "text/plain"))
    app.router.add_get("/", text_handler(HOME, "text/html"))
    app.router.add_get("/feed.xml", text_handler(RSS, "application/rss+xml"))
    app.router.add_get("/br/feed.xml", brotli_handler(RSS, "application/rss+xml"))
    app.router.add_get("/blocked.xml", text_handler(RSS, "application/rss+xml"))
    app.router.add_get("/json/", text_handler(JSON_HOME, "text/html"))
    app.router.add_get("/feed.json", text_handler(JSON_FEED, "application/json"))

    async def png_handler(request):
        return web.Response(body=PNG, content_type="image/png")

    app.router.add_get("/favicon.png", png_handler)
    for i in range(5):
        app.router.add_get(f"/page{i}", text_handler(PAGE, "text/html"))
    return app


async def _run_crawl(
    robots_txt: str = "User-agent: *\nAllow: /",
    start_path: str = "/",
    **spider_kwargs,
) -> FeedsearchSpider:
    app = _build_app(robots_txt)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        kwargs = dict(
            start_urls=[f"http://127.0.0.1:{port}{start_path}"],
            concurrency=10,
            request_timeout=3,
            total_timeout=15,
            max_retries=0,
            delay=0,
            try_urls=False,
            favicon_data_uri=False,
        )
        kwargs.update(spider_kwargs)
        spider = FeedsearchSpider(**kwargs)
        spider._test_port = port
        await spider.crawl()
        return spider
    finally:
        await runner.cleanup()


class TestCrawlEndToEnd:
    """Full crawl against a local server."""

    def test_crawl_discovers_feed(self):
        """The crawl must fetch pages, discover the feed, and finish quickly.

        Regression test: a bug in the worker loop killed every worker on its
        first queue item, so crawls processed nothing and idled until
        total_timeout. Asserting on duration and found items catches any
        recurrence of that failure mode.
        """
        start = time.perf_counter()
        spider = asyncio.run(_run_crawl())
        duration = time.perf_counter() - start

        feeds = list(spider.items)
        assert len(feeds) == 1
        assert feeds[0].title == "E2E Feed"
        assert feeds[0].url.path == "/feed.xml"
        # Well under total_timeout: the crawl must end by draining the queue,
        # not by timing out.
        assert duration < 10

    def test_crawl_fetches_robots_and_sitemap_with_port(self):
        """robots.txt and sitemap requests must keep the URL port."""
        spider = asyncio.run(_run_crawl())

        seen_urls = [str(u) for u in getattr(spider, "_test_seen", [])]
        # The robots middleware cache is keyed by the fetched robots URL;
        # the local port must be part of it (previously the port was dropped).
        robots_keys = list(spider._robots_middleware.cache.keys())
        assert robots_keys, "robots.txt was never registered"
        assert all(f"127.0.0.1:{spider._test_port}" in key for key in robots_keys), (
            robots_keys,
            seen_urls,
        )

    def test_robots_disallow_blocks_feed(self):
        """A robots.txt Disallow rule must prevent fetching the blocked URL."""
        spider = asyncio.run(
            _run_crawl(robots_txt="User-agent: *\nDisallow: /blocked.xml")
        )
        blocked = [f for f in spider.items if "blocked" in str(f.url)]
        assert blocked == []
        # The allowed feed is still found.
        assert any(str(f.url).endswith("/feed.xml") for f in spider.items)

    def test_brotli_encoded_feed_is_fetched(self):
        """A brotli-compressed response must decode and parse.

        Regression test: the abandoned brotlipy package provided a `brotli`
        module whose Decompressor was incompatible with aiohttp, so every
        response from a server that chose br encoding (most Cloudflare
        sites) failed with ContentEncodingError.
        """
        spider = asyncio.run(
            _run_crawl(start_path="/br/feed.xml", requests_per_host_per_sec=0)
        )
        feeds = list(spider.items)
        assert any(f.title == "E2E Feed" for f in feeds), feeds

    def test_json_feed_is_parsed(self):
        """A JSON Feed served as application/json must be discovered.

        Regression test: ContentTypeMiddleware called `response.json()` on
        JSON responses, but the downloader had already parsed the body into
        the `json` dict attribute, so every JSON fetch failed with
        "'dict' object is not callable" and no JSON Feed was ever parsed.
        """
        spider = asyncio.run(
            _run_crawl(start_path="/json/", requests_per_host_per_sec=0)
        )
        feeds = list(spider.items)
        assert any(
            f.url.path == "/feed.json" and f.title == "E2E JSON Feed" for f in feeds
        ), feeds

    def test_favicon_data_uri_is_built(self):
        """With favicon_data_uri enabled the site icon becomes a data URI.

        Regression test for two bugs: requests were built without an
        xml_parser, so the site-meta parser got None from response.xml and
        never yielded site name, URL or icons; and the downloader's early
        content-type filter rejected image responses with 415 before
        parse_favicon_data_uri ran.
        """
        spider = asyncio.run(
            _run_crawl(favicon_data_uri=True, requests_per_host_per_sec=0)
        )
        feeds = [f for f in spider.items if f.url.path == "/feed.xml"]
        assert feeds, list(spider.items)
        # Site metadata comes from the same site-meta parse as the icon.
        assert feeds[0].site_name == "E2E Site"
        assert str(feeds[0].favicon).endswith("/favicon.png")
        assert feeds[0].favicon_data_uri.startswith("data:image/png;base64,")

    def test_throttle_disabled_is_fast(self):
        """With throttling disabled the crawl should complete near-instantly."""
        start = time.perf_counter()
        spider = asyncio.run(_run_crawl(requests_per_host_per_sec=0))
        duration = time.perf_counter() - start
        assert len(spider.items) == 1
        assert duration < 5

    def test_throttle_limits_request_rate(self):
        """The per-host throttle must space out requests."""
        start = time.perf_counter()
        spider = asyncio.run(_run_crawl(requests_per_host_per_sec=4))
        duration = time.perf_counter() - start
        assert len(spider.items) == 1
        # The crawl makes several same-host requests; at 4/sec they cannot
        # all complete in the first quarter second.
        assert duration > 0.5
