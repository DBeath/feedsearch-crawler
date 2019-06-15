import asyncio
import aiohttp


async def on_request_start(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    trace_config_ctx.start = loop.time()
    print(f"Request Start: {params.url}")


async def on_request_end(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    print(f"Request END: {params.url} {params.response.url} {elapsed}ms")


async def on_connection_create_start(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    print(f"Connection create Start: {elapsed}ms")


async def on_connection_create_end(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    print(f"Connection create END: {elapsed}ms")


async def on_dns_resolvehost_start(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    print(f"DNS Resolve Host Start: {params.host} {elapsed}ms")


async def on_dns_resolvehost_end(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    print(f"DNS Resolve Host END: {params.host} {elapsed}ms")


async def on_dns_cache_hit(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    print(f"DNS Cache Hit: {params.host} {elapsed}ms")


async def on_dns_cache_miss(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    print(f"DNS Cache Miss: {params.host} {elapsed}ms")


async def on_request_redirect(session, trace_config_ctx, params):
    loop = asyncio.get_event_loop()
    elapsed = int((loop.time() - trace_config_ctx.start) * 1000)
    print(f"Request redirect: {params.url} {params.response.url} {elapsed}ms")


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
