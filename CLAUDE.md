# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development with uv
This project uses [uv](https://docs.astral.sh/uv/) for package management and development:

- `uv sync` - Install dependencies and sync the environment
- `uv run ruff check` - Run linting checks
- `uv run ruff format` - Format code
- `uv run pytest` - Run all tests
- `uv run pytest tests/crawler/test_request.py` - Run a specific test file
- `uv run pytest tests/crawler/test_request.py::TestRequest::test_method_name` - Run a specific test

### Running the Application
- `uv run main.py` - Run with default URLs from file
- `uv run main.py https://example.com` - Crawl single URL
- `uv run main.py example.com` - Crawl single URL with domain only
- `uv run main.py https://site1.com https://site2.com` - Crawl multiple URLs
- `uv run main.py --urls "https://site1.com,https://site2.com"` - Use comma-separated format
- `uv run main.py --help` - Get help

### Package Installation
The library is available on PyPI: `pip install feedsearch-crawler`

## Architecture Overview

### Core Components

**feedsearch-crawler** is an asyncio-based RSS/Atom/JSON feed discovery crawler built on two main architectural layers:

#### 1. Crawler Framework (`src/feedsearch_crawler/crawler/`)
A generic asynchronous web crawler framework providing:

- **Crawler**: Base class for web crawlers with request/response handling, middleware support, and concurrent processing
- **Request/Response**: HTTP request and response objects with proper typing
- **Downloader**: HTTP client wrapper using aiohttp with connection pooling and error handling
- **Middleware**: Pipeline-based request/response processing (robots.txt, throttling, retry logic, cookies, content-type handling, monitoring)
- **DuplicateFilter**: URL deduplication to avoid crawling the same resource multiple times
- **Item/ItemParser**: Structured data extraction and processing

#### 2. Feed Spider (`src/feedsearch_crawler/feed_spider/`)
Specialized crawler for feed discovery built on the crawler framework:

- **FeedsearchSpider**: Main spider class that orchestrates feed discovery
- **FeedInfo**: Data class representing discovered feeds with metadata (title, description, score, etc.)
- **FeedInfoParser**: Parses and validates feed content (RSS, Atom, JSON feeds)
- **SiteMeta/SiteMetaParser**: Extracts website metadata and favicon information
- **LinkFilter**: Filters and prioritizes potential feed URLs
- **Favicon**: Handles favicon discovery and data URI conversion

### Key Design Patterns

**Middleware Pipeline**: Request/response processing uses a middleware pattern allowing modular functionality like robots.txt compliance, throttling, and retry logic.

**Async Generator Pattern**: The `parse_response` method yields requests and items asynchronously, enabling efficient concurrent processing.

**Scoring System**: Discovered feeds are scored based on relevance indicators (URL patterns, content analysis) and sorted by score.

**Duplicate Filtering**: Uses `NoQueryDupeFilter` to avoid processing the same URLs multiple times while ignoring query parameters.

### Entry Points

- **Public API**: `search()` and `search_async()` functions in `__init__.py`
- **CLI Interface**: `main.py` provides command-line access with URL parsing and output formatting

### Dependencies

Key dependencies include:
- `aiohttp` for async HTTP operations
- `beautifulsoup4` for HTML parsing
- `feedparser` for feed validation and parsing
- `yarl` for URL handling
- `uvloop` for enhanced asyncio performance

The architecture separates concerns between generic web crawling capabilities and feed-specific discovery logic, making the system both modular and extensible.