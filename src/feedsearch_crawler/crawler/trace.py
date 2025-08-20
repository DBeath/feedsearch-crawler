import asyncio
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


async def on_request_start(session: Any, trace_config_ctx: Any, params: Any) -> None:
    trace_config_ctx.start = asyncio.get_event_loop().time()
    trace_config_ctx.url = params.url
    trace_config_ctx.method = params.method
    logger.debug("Request Start: %s", params.url)


async def on_request_end(session: Any, trace_config_ctx: Any, params: Any) -> None:
    trace_config_ctx.end = asyncio.get_event_loop().time()
    trace_config_ctx.duration = trace_config_ctx.end - trace_config_ctx.start
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("Request END: %s %s %dms", params.url, params.response.url, elapsed)


async def on_connection_create_start(
    session: Any, trace_config_ctx: Any, params: Any
) -> None:
    trace_config_ctx.conn_start = asyncio.get_event_loop().time()
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("Connection create Start: %dms", elapsed)


async def on_connection_create_end(
    session: Any, trace_config_ctx: Any, params: Any
) -> None:
    trace_config_ctx.conn_end = asyncio.get_event_loop().time()
    trace_config_ctx.conn_duration = (
        trace_config_ctx.conn_end - trace_config_ctx.conn_start
    )
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("Connection create END: %dms", elapsed)


async def on_dns_resolvehost_start(
    session: Any, trace_config_ctx: Any, params: Any
) -> None:
    trace_config_ctx.dns_start = asyncio.get_event_loop().time()
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("DNS Resolve Host Start: %s %dms", params.host, elapsed)


async def on_dns_resolvehost_end(
    session: Any, trace_config_ctx: Any, params: Any
) -> None:
    trace_config_ctx.dns_end = asyncio.get_event_loop().time()
    trace_config_ctx.dns_duration = (
        trace_config_ctx.dns_end - trace_config_ctx.dns_start
    )
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("DNS Resolve Host END: %s %dms", params.host, elapsed)


async def on_dns_cache_hit(session: Any, trace_config_ctx: Any, params: Any) -> None:
    trace_config_ctx.dns_cache_hit = True
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("DNS Cache Hit: %s %dms", params.host, elapsed)


async def on_dns_cache_miss(session: Any, trace_config_ctx: Any, params: Any) -> None:
    trace_config_ctx.dns_cache_hit = False
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("DNS Cache Miss: %s %dms", params.host, elapsed)


async def on_request_redirect(session: Any, trace_config_ctx: Any, params: Any) -> None:
    trace_config_ctx.redirect_url = params.url
    trace_config_ctx.redirect_status = params.response.status
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug(
        "Request redirect: %s %s %dms", params.url, params.response.url, elapsed
    )


def add_trace_config() -> Any:
    trace_config = aiohttp.TraceConfig()
    trace_config.on_request_start.append(on_request_start)
    trace_config.on_dns_resolvehost_start.append(on_dns_resolvehost_start)
    trace_config.on_dns_cache_hit.append(on_dns_cache_hit)
    trace_config.on_dns_cache_miss.append(on_dns_cache_miss)
    trace_config.on_dns_resolvehost_end.append(on_dns_resolvehost_end)
    trace_config.on_request_end.append(on_request_end)
    trace_config.on_request_redirect.append(on_request_redirect)
    trace_config.on_connection_create_start.append(on_connection_create_start)
    trace_config.on_connection_create_end.append(on_connection_create_end)
    return trace_config
