import asyncio
import json
from typing import List

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from yarl import URL

from feedsearch_crawler.crawler.downloader import Downloader
from feedsearch_crawler.crawler.middleware import BaseDownloaderMiddleware
from feedsearch_crawler.crawler.request import Request


class _RecorderMiddleware(BaseDownloaderMiddleware):
    def __init__(self) -> None:
        self.pre_requests: List[Request] = []
        self.process_requests: List[Request] = []
        self.process_responses_urls: List[URL] = []
        self.exceptions: List[Exception] = []

    async def pre_request(self, request: Request) -> None:
        self.pre_requests.append(request)

    async def process_request(self, request: Request) -> None:
        self.process_requests.append(request)

    async def process_response(self, response):  # type: ignore[override]
        self.process_responses_urls.append(response.url)

    async def process_exception(self, request: Request, exception: Exception) -> None:
        self.exceptions.append(exception)


async def _create_test_server() -> TestServer:
    app = web.Application()

    async def ok_handler(request: web.Request) -> web.Response:
        payload = {"message": "hello", "path": request.path}
        text = json.dumps(payload)
        return web.Response(text=text, content_type="application/json")

    async def large_handler(request: web.Request) -> web.Response:
        body = b"x" * 2048
        return web.Response(body=body, content_type="application/octet-stream")

    async def slow_handler(request: web.Request) -> web.Response:
        await asyncio.sleep(0.2)
        return web.Response(text="slow")

    async def server_error_handler(request: web.Request) -> web.Response:
        return web.Response(status=500, text="error")

    app.router.add_get("/ok", ok_handler)
    app.router.add_get("/large", large_handler)
    app.router.add_get("/slow", slow_handler)
    app.router.add_get("/error", server_error_handler)

    server = TestServer(app)
    await server.start_server()
    return server


@pytest.mark.asyncio
async def test_downloader_success_and_middleware_calls() -> None:
    server = await _create_test_server()
    try:
        async with aiohttp.ClientSession() as session:
            middleware = _RecorderMiddleware()
            downloader = Downloader(request_session=session, middlewares=[middleware])

            url = URL(str(server.make_url("/ok")))
            req = Request(url=url)

            resp = await downloader.fetch(req)

            assert resp.status_code == 200
            assert resp.ok
            assert resp.url == url
            assert resp.json == {"message": "hello", "path": "/ok"}
            assert isinstance(resp.content_length, int) and resp.content_length > 0
            assert resp.history[-1] == url

            # Middleware assertions
            assert middleware.pre_requests and middleware.pre_requests[0] is req
            assert middleware.process_requests and middleware.process_requests[0] is req
            assert middleware.process_responses_urls and middleware.process_responses_urls[0] == url
    finally:
        await server.close()


@pytest.mark.asyncio
async def test_downloader_content_length_overflow_returns_413() -> None:
    server = await _create_test_server()
    try:
        async with aiohttp.ClientSession() as session:
            downloader = Downloader(request_session=session)

            url = URL(str(server.make_url("/large")))
            req = Request(url=url, max_content_length=100)  # force overflow

            resp = await downloader.fetch(req)

            assert resp.status_code == 413
            assert not resp.ok
            assert resp.url == url
            assert not req.should_retry  # 413 is not auto-retried
    finally:
        await server.close()


@pytest.mark.asyncio
async def test_downloader_timeout_sets_408_and_marks_retry() -> None:
    server = await _create_test_server()
    try:
        async with aiohttp.ClientSession() as session:
            downloader = Downloader(request_session=session)

            url = URL(str(server.make_url("/slow")))
            req = Request(url=url, timeout=0.05, retries=3)

            resp = await downloader.fetch(req)

            assert resp.status_code == 408
            assert not resp.ok
            assert req.should_retry is True
            assert req.delay > 0
    finally:
        await server.close()


@pytest.mark.asyncio
async def test_downloader_process_exception_called_on_unexpected_error(monkeypatch) -> None:
    server = await _create_test_server()
    try:
        async with aiohttp.ClientSession() as session:
            middleware = _RecorderMiddleware()
            downloader = Downloader(request_session=session, middlewares=[middleware])

            # Force an unexpected error inside _read_response to trigger process_exception
            async def boom(*args, **kwargs):
                raise RuntimeError("boom")

            monkeypatch.setattr(Downloader, "_read_response", boom)

            url = URL(str(server.make_url("/ok")))
            req = Request(url=url)

            resp = await downloader.fetch(req)

            assert resp.status_code == 500
            assert middleware.exceptions and isinstance(middleware.exceptions[0], RuntimeError)
    finally:
        await server.close()
