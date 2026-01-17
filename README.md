# Feedsearch Crawler

[![PyPI](https://img.shields.io/pypi/v/feedsearch-crawler.svg)](https://pypi.org/project/feedsearch-crawler/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/feedsearch-crawler.svg)
![PyPI - License](https://img.shields.io/pypi/l/feedsearch-crawler.svg)

**feedsearch-crawler** is a Python library for discovering [RSS](https://en.wikipedia.org/wiki/RSS), [Atom](https://en.wikipedia.org/wiki/Atom_(Web_standard)), and [JSON](https://jsonfeed.org/) feeds on websites.

## About

This is a **library package** designed to be integrated into other Python applications. It provides a simple API for feed discovery that can be embedded into web scrapers, content aggregators, RSS readers, or API services.

It is a continuation of my work on [Feedsearch](https://github.com/DBeath/feedsearch), which is itself a continuation of the work done by [Dan Foreman-Mackey](http://dfm.io/) on [Feedfinder2](https://github.com/dfm/feedfinder2), which in turn is based on [feedfinder](http://www.aaronsw.com/2002/feedfinder/) - originally written by [Mark Pilgrim](http://en.wikipedia.org/wiki/Mark_Pilgrim_(software_developer)) and subsequently maintained by
[Aaron Swartz](http://en.wikipedia.org/wiki/Aaron_Swartz) until his untimely death.

Feedsearch Crawler differs from previous versions in that it is now built as an asynchronous [Web crawler](https://en.wikipedia.org/wiki/Web_crawler) using [asyncio](https://docs.python.org/3/library/asyncio.html) and [aiohttp](https://aiohttp.readthedocs.io/en/stable/), allowing much more rapid scanning of potential feed URLs.

## Real-World Usage

An implementation using this library to provide a public Feed Search API is available at <https://feedsearch.dev>

Pull requests and suggestions are welcome.

## Installation

The library is available on [PyPI](https://pypi.org/project/feedsearch-crawler/):

```shell
pip install feedsearch-crawler
```

**Requirements:**
- Python 3.12 or higher
- No additional system dependencies

## Usage

Feedsearch Crawler is called with the single function ``search``:

``` python
>>> from feedsearch_crawler import search
>>> feeds = search('xkcd.com')
>>> feeds
[FeedInfo('https://xkcd.com/rss.xml'), FeedInfo('https://xkcd.com/atom.xml')]
>>> feeds[0].url
URL('https://xkcd.com/rss.xml')
>>> str(feeds[0].url)
'https://xkcd.com/rss.xml'
>>> feeds[0].serialize()
{'url': 'https://xkcd.com/rss.xml', 'title': 'xkcd.com', 'version': 'rss20', 'score': 24, 'hubs': [], 'description': 'xkcd.com: A webcomic of romance and math humor.', 'is_push': False, 'self_url': '', 'favicon': 'https://xkcd.com/s/919f27.ico', 'content_type': 'text/xml; charset=UTF-8', 'bozo': 0, 'site_url': 'https://xkcd.com/', 'site_name': 'xkcd: Chernobyl', 'favicon_data_uri': '', 'content_length': 2847}
```

If you are already running in an [asyncio event loop](https://docs.python.org/3/library/asyncio-eventloop.html), then you can import and await ``search_async`` instead. The ``search`` function is only a wrapper that runs ``search_async`` in a new asyncio event loop.

``` python
from feedsearch_crawler import search_async

feeds = await search_async('xkcd.com')
```

A search will always return a list of *FeedInfo* objects, each of which will always have a *url* property, which is a [URL](https://yarl.readthedocs.io/en/latest/api.html) object that can be decoded to a string with ``str(url)``.
The returned *FeedInfo* are sorted by the *score* value from highest to lowest, with a higher score theoretically indicating a more relevant feed compared to the original URL provided. A *FeedInfo* can also be serialized to a JSON compatible dictionary by calling it's ``.serialize()`` method.

## Error Handling

If you need detailed error information when a URL fails to load (DNS errors, SSL errors, HTTP errors, timeouts, etc.), use ``search_with_info`` or ``search_async_with_info`` instead. These functions return a ``SearchResult`` object that includes error details:

``` python
from feedsearch_crawler import search_with_info, ErrorType

result = search_with_info('nonexistent-domain.com')

if result.root_error:
    print(f"Error: {result.root_error.message}")
    print(f"Type: {result.root_error.error_type}")

    # Handle specific error types
    if result.root_error.error_type == ErrorType.DNS_FAILURE:
        print("Domain doesn't exist")
    elif result.root_error.error_type == ErrorType.SSL_ERROR:
        print("SSL certificate problem")
    elif result.root_error.error_type == ErrorType.HTTP_ERROR:
        print(f"HTTP error: {result.root_error.status_code}")
    elif result.root_error.error_type == ErrorType.TIMEOUT:
        print("Request timed out")
else:
    print(f"Found {len(result.feeds)} feeds")
    for feed in result.feeds:
        print(feed.url)
```

You can also retrieve crawl statistics by passing ``include_stats=True``:

``` python
result = search_with_info('xkcd.com', include_stats=True)

if result.stats:
    print(f"Requests: {result.stats.get('requests')}")
    print(f"Responses: {result.stats.get('responses')}")
    print(f"Duration: {result.stats.get('duration')}")
```

The ``SearchResult`` object is iterable, so you can iterate over feeds directly:

``` python
result = search_with_info('xkcd.com')

for feed in result:  # Iterates over result.feeds
    print(feed.url)
```

**Note**: The original ``search()`` and ``search_async()`` functions return an empty list when errors occur. This behavior is maintained for backward compatibility. Use ``search_with_info()`` when you need to distinguish between "no feeds found" and "URL failed to load".

The crawl logs can be accessed with:

``` python
import logging

logger = logging.getLogger("feedsearch_crawler")
```

Feedsearch Crawler also provides a handy function to output the returned feeds as an [OPML](https://en.wikipedia.org/wiki/OPML) subscription list, encoded as a UTF-8 bytestring.

``` python
from feedsearch_crawler import output_opml

output_opml(feeds).decode()
```

## Search Arguments

``search`` and ``search_async`` take the following arguments:

``` python
search(
    url: Union[URL, str, List[Union[URL, str]]],
    crawl_hosts: bool=True,
    try_urls: Union[List[str], bool]=False,
    concurrency: int=10,
    total_timeout: Union[float, aiohttp.ClientTimeout]=10,
    request_timeout: Union[float, aiohttp.ClientTimeout]=3,
    user_agent: str="Feedsearch Bot",
    max_content_length: int=1024 * 1024 * 10,
    max_depth: int=10,
    headers: dict={"X-Custom-Header": "Custom Header"},
    favicon_data_uri: bool=True,
    delay: float=0
)
```

- **url**: *Union[str, List[str]]*: The initial URL or list of URLs at which to search for feeds. You may also provide [URL](https://yarl.readthedocs.io/en/latest/api.html) objects.
- **crawl_hosts**: *bool*: (default True): An optional argument to add the site host origin URL to the list of initial crawl URLs. (e.g. add "example.com" if crawling "example.com/path/rss.xml"). If **False**, site metadata and favicon data may not be found.
- **try_urls**: *Union[List[str], bool]*: (default False): An optional list of URL paths to query for feeds. Takes the origins of the *url* parameter and appends the provided paths. If no list is provided, but *try_urls* is **True**, then a list of common feed locations will be used.
- **concurrency**: *int*: (default 10): An optional argument to specify the maximum number of concurrent HTTP requests.
- **total_timeout**: *float*: (default 30.0): An optional argument to specify the time this function may run before timing out.
- **request_timeout**: *float*: (default 3.0): An optional argument that controls how long before each individual HTTP request times out.
- **user_agent**: *str*: An optional argument to override the default User-Agent header.
- **max_content_length**: *int*: (default 10Mb): An optional argument to specify the maximum size in bytes of each HTTP Response.
- **max_depth**: *int*: (default 10): An optional argument to limit the maximum depth of requests while following urls.
- **headers**: *dict*: An optional dictionary of headers to pass to each HTTP request.
- **favicon_data_uri**: *bool*: (default True): Optionally control whether to fetch found favicons and return them as a Data Uri.
- **delay**: *float*: (default 0.0): An optional argument to delay each HTTP request by the specified time in seconds. Used in conjunction with the concurrency setting to avoid overloading sites.

## FeedInfo Values

In addition to the *url*, FeedInfo objects may have the following values:

- **bozo**: *int*: Set to 1 when feed data is not well formed or may not be a feed. Defaults 0.
- **content_length**: *int*: Current length of the feed in bytes.
- **content_type**: *str*: [Content-Type](https://en.wikipedia.org/wiki/Media_type) value of the returned feed.
- **description**: *str*: Feed description.
- **favicon**: *URL*: [URL](https://yarl.readthedocs.io/en/latest/api.html) of feed or site [Favicon](https://en.wikipedia.org/wiki/Favicon).
- **favicon_data_uri**: *str*: [Data Uri](https://en.wikipedia.org/wiki/Data_URI_scheme) of Favicon.
- **hubs**: *List[str]*: List of [Websub](https://en.wikipedia.org/wiki/WebSub) hubs of feed if available.
- **is_podcast**: *bool*: True if the feed contains valid [podcast](https://en.wikipedia.org/wiki/Podcast) elements and enclosures.
- **is_push**: *bool*: True if feed contains valid Websub data.
- **item_count**: *int*: Number of items currently in the feed.
- **last_updated**: *datetime*: Date of the latest published entry.
- **score**: *int*: Computed relevance of feed url value to provided URL. May be safely ignored.
- **self_url**: *URL*: *ref="self"* value returned from feed links. In some cases may be different from feed url.
- **site_name**: *str*: Name of feed's website.
- **site_url**: *URL*: [URL](https://yarl.readthedocs.io/en/latest/api.html) of feed's website.
- **title**: *str*: Feed Title.
- **url**: *URL*: [URL](https://yarl.readthedocs.io/en/latest/api.html) location of feed.
- **velocity**: *float*: Mean number of items per day in the feed at the current time.
- **version**: *str*: Feed version [XML values](https://pythonhosted.org/feedparser/version-detection.html),
  or [JSON feed](https://jsonfeed.org/version/1).

## Development

This project uses [uv](https://docs.astral.sh/uv/) for package management and development.

```shell
uv sync
uv run ruff check
uv run ruff format
uv run pytest
```

```shell
# Use default URLs from file
uv run main.py

# Crawl single URL
uv run main.py https://example.com

# Crawl single URL with domain only
uv run main.py example.com

# Crawl multiple URLs
uv run main.py https://site1.com https://site2.com

# Use comma-separated format
uv run main.py --urls "https://site1.com,https://site2.com"

# Get help
uv run main.py --help
```