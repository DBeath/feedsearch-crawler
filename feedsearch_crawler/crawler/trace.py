import asyncio
import aiohttp
import logging

logger = logging.getLogger("feedsearch_crawler")


async def on_request_start(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    trace_config_ctx.start = loop.time()
    logger.debug("Request Start: %s", params.url)


async def on_request_end(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("Request END: %s %s %dms", params.url, params.response.url, elapsed)


async def on_connection_create_start(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("Connection create Start: %dms", elapsed)


async def on_connection_create_end(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("Connection create END: %dms", elapsed)


async def on_dns_resolvehost_start(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("DNS Resolve Host Start: %s %dms", params.host, elapsed)


async def on_dns_resolvehost_end(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("DNS Resolve Host END: %s %dms", params.host, elapsed)


async def on_dns_cache_hit(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("DNS Cache Hit: %s %dms", params.host, elapsed)


async def on_dns_cache_miss(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug("DNS Cache Miss: %s %dms", params.host, elapsed)


async def on_request_redirect(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    logger.debug(
        "Request redirect: %s %s %dms", params.url, params.response.url, elapsed
    )


def add_trace_config():
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
