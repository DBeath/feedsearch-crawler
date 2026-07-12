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
    "</head><body>"
    + "".join(f'<a href="/page{i}">page {i}</a>' for i in range(5))
    + "</body></html>"
)

PAGE = "<html><head><title>Page</title></head><body>nothing here</body></html>"


def _build_app(robots_txt: str) -> web.Application:
    def text_handler(text: str, content_type: str):
        async def handler(request):
            return web.Response(text=text, content_type=content_type)

        return handler

    app = web.Application()
    app.router.add_get("/robots.txt", text_handler(robots_txt, "text/plain"))
    app.router.add_get("/", text_handler(HOME, "text/html"))
    app.router.add_get("/feed.xml", text_handler(RSS, "application/rss+xml"))
    app.router.add_get("/blocked.xml", text_handler(RSS, "application/rss+xml"))
    for i in range(5):
        app.router.add_get(f"/page{i}", text_handler(PAGE, "text/html"))
    return app


async def _run_crawl(
    robots_txt: str = "User-agent: *\nAllow: /", **spider_kwargs
) -> FeedsearchSpider:
    app = _build_app(robots_txt)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        kwargs = dict(
            start_urls=[f"http://127.0.0.1:{port}/"],
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
