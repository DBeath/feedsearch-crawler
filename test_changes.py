#!/usr/bin/env python3
"""
Simple test script to verify that the separation of Request and Downloader is working correctly.
"""

import asyncio
from yarl import URL
import aiohttp

from src.feedsearch_crawler.crawler.request import Request
from src.feedsearch_crawler.crawler.downloader import Downloader


async def test_request_downloader_separation():
    """Test that Request and Downloader are properly separated."""
    
    # Create a Request - it should only contain the request details, no HTTP functionality
    request = Request(
        url=URL("https://httpbin.org/get"),
        method="GET",
        headers={"User-Agent": "Test-Agent"},
        timeout=10.0
    )
    
    print(f"Created request: {request}")
    print(f"Request URL: {request.url}")
    print(f"Request method: {request.method}")
    print(f"Request headers: {request.headers}")
    print(f"Request timeout: {request.timeout}")
    
    # Verify that Request doesn't have HTTP methods anymore
    assert not hasattr(request, 'fetch_callback'), "Request should not have fetch_callback method"
    assert not hasattr(request, '_fetch'), "Request should not have _fetch method"
    
    # Create a ClientSession and Downloader
    async with aiohttp.ClientSession() as session:
        downloader = Downloader(request_session=session)
        
        print(f"Created downloader: {downloader}")
        
        # Use the downloader to fetch the request
        response = await downloader.fetch(request)
        
        print(f"Got response: {response}")
        print(f"Response status: {response.status_code}")
        print(f"Response URL: {response.url}")
        print(f"Response OK: {response.ok}")
        
        # Verify the response contains the request
        assert response.request is request, "Response should contain reference to original request"
        
        print("✅ Test passed! Request and Downloader are properly separated.")


if __name__ == "__main__":
    asyncio.run(test_request_downloader_separation())
