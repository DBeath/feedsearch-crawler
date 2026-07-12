# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.1] - 2026-07-11

### Fixed
- **Critical: the crawl worker loop was completely broken in all 2.x
  releases.** Workers crashed on their first queue item (an uninitialized
  legacy statistics attribute removed in the 2.0 stats refactor), died
  silently, and every crawl processed zero requests while idling until
  `total_timeout`. Queue metrics are now recorded through `StatsCollector`,
  and the worker loop is hardened so no exception can kill a worker or skip
  queue accounting. An end-to-end crawl test against a local HTTP server now
  guards this path (the previous integration test file was disabled, which
  is how the breakage went unnoticed)
- robots.txt disallow rules are now enforced *before* a request is sent
  (previously the check ran after the response had already been fetched),
  and the rules are parsed from the crawler's own async robots.txt fetch.
  Previously the middleware fetched robots.txt a second time with a
  **blocking urllib call on the event loop, with no timeout**
- Per-host throttling now delays requests *before* they are sent
  (previously it slept after the response arrived, adding latency without
  limiting the actual request rate)
- robots.txt and sitemap.xml URLs no longer drop the port from non-standard
  origins

### Changed
- New `requests_per_host_per_sec` crawler parameter (default 5, 0 disables)
  replaces the previously hardcoded per-host rate of 2
- BeautifulSoup uses the ~1.6x faster lxml parser when lxml is installed
  (`pip install feedsearch-crawler[lxml]`); falls back to html.parser

### Performance
- Response history copies use shallow list copies instead of `deepcopy`
  (~290x faster per request)
- JSON parsing of response bodies is skipped for non-JSON content

## [2.1.0] - 2026-07-10

### Added
- **Feed-declared metadata fields on `FeedInfo`**, extracted from RSS 2.0 channel,
  Atom (RFC 4287) feed, and JSON Feed 1.0/1.1 top-level elements:
  - `link` (*URL*): website link declared by the feed (RSS `<link>`,
    Atom `rel="alternate"` link, JSON Feed `home_page_url`)
  - `language` (*str*): RSS `<language>` / Atom `xml:lang` / JSON Feed `language`
  - `author` (*str*): RSS `managingEditor` / `itunes:author` / Atom `<author><name>` /
    JSON Feed `authors[0].name` (also supports the JSON Feed 1.0 `author` object)
  - `copyright` (*str*): RSS `<copyright>` / Atom `<rights>`
  - `generator` (*str*): `<generator>`
  - `tags` (*List[str]*): unique category terms from RSS/Atom `<category>` and
    `itunes:category`
  - `image` (*URL*): feed artwork from `itunes:image`, RSS `<image><url>`,
    Atom `<logo>`, or JSON Feed `icon`
  - `is_explicit` (*bool | None*): channel-level `itunes:explicit`, None when
    not declared. Values feedparser cannot map (`true`, `false`, `no`,
    `explicit`) are recovered from the channel-level XML
- Atom `<icon>` now populates `favicon` when no favicon was already found
  (JSON Feed `favicon` was already supported)
- `new_feed_url` (*URL*): `itunes:new-feed-url` - the feed has permanently
  moved to this URL
- JSON Feed `feed_url` now populates `self_url` (the canonical self link)
- Video podcasts are now detected: `is_podcast` accepts video as well as
  audio enclosures, and JSON Feeds with audio/video attachments are
  recognized as podcasts
- Relative URLs in feeds (link, image, favicon, etc.) are now resolved
  against the feed's own URL (via feedparser's content-location base)
- All new fields are included in `FeedInfo.serialize()` output and the
  `FEEDINFO_SCHEMA` JSON schema

### Fixed
- Malformed-but-recoverable feeds are now flagged `bozo=1` (previously only
  character-encoding overrides were flagged, so malformed XML escaped the
  bozo scoring penalty). A missing/non-XML HTTP Content-Type alone does not
  count as malformed
- JSON Feeds now require both a hub and a self URL (`feed_url`) for
  `is_push`, matching the XML behavior and the WebSub spec

### Changed
- feedparser HTML sanitization is disabled (`sanitize_html=False`) for a
  ~2x parse speedup; this crawler discards entry content, but feed-level
  `description` values are no longer HTML-sanitized - treat them as
  untrusted text

### Notes
- Fully backward compatible: all new fields are additive with empty/None defaults

## [2.0.0] - 2025-01-17

### Breaking Changes
- **Python 3.12+ required**: Dropped support for Python 3.7-3.11
- **`FeedInfo.serialize()` returns `None` instead of `""`**: URL fields (`url`, `site_url`, `favicon`, `self_url`) and `last_updated` now return `None` when not set, instead of empty string
- **`FeedInfo` validation raises `ValueError`**: Creating `FeedInfo` with invalid values (negative scores, invalid bozo values, etc.) now raises `ValueError`
- **Internal method renames in `FeedsearchSpider`**: `parse()` renamed to `parse_response()`, `parse_xml()` renamed to `parse_response_content()`. Users who subclassed and overrode these methods must update their code
- **Major dependency version bumps**: aiohttp `^3.7.4` → `>3.12.0`, yarl `^1.6.3` → `>=1.22.0`, beautifulsoup4 `^4.9.3` → `>=4.14.2`
- **Removed `cchardet` dependency**

### Added
- **New error handling API**: Added `search_with_info()` and `search_async_with_info()` functions that return detailed error information
  - Returns `SearchResult` object with `feeds`, `root_error`, and optional `stats` fields
  - Provides structured error information via `SearchError` dataclass
  - Supports error type classification: DNS failures, SSL errors, HTTP errors, timeouts, etc.
  - Optional crawl statistics via `include_stats=True` parameter
- Added `SearchResult` class that wraps feed lists with error information
  - Fully iterable (supports `for feed in result`)
  - List-like access (supports `result[0]`, `len(result)`, `bool(result)`)
- Added `SearchError` dataclass with structured error information
  - `url`: The URL that failed
  - `error_type`: Error classification (ErrorType enum)
  - `message`: Human-readable error message
  - `status_code`: HTTP status code (if applicable)
  - `original_exception`: Original exception details
- Added `ErrorType` enum with error classifications:
  - `DNS_FAILURE`: Domain resolution failures
  - `SSL_ERROR`: SSL/TLS certificate errors
  - `CONNECTION_ERROR`: Network connection errors
  - `HTTP_ERROR`: HTTP error responses (4xx, 5xx)
  - `TIMEOUT`: Request timeout errors
  - `INVALID_URL`: Malformed URL errors
  - `OTHER`: Other error types
- Added error tracking in `FeedsearchSpider`:
  - Tracks root URL errors (user-provided URLs that fail)
  - Distinguishes between root URL failures and discovered URL failures
  - Provides `get_root_error()` method to retrieve root errors
- Added 15 contract tests in `test_api_contract.py` to enforce API guarantees:
  - Ensures `search()` always returns `List[FeedInfo]` (never `SearchResult`)
  - Ensures `search_with_info()` always returns `SearchResult` (never plain list)
  - Verifies type annotations match actual return types
  - Protects backward compatibility for v1.x releases
- Added comprehensive error handling documentation in README.md
- Added `py.typed` marker file for PEP 561 type checking support
- Added pytest warning filters for AsyncMock and feedparser deprecation warnings
- Added CHANGELOG.md to track project changes
- Added CONTRIBUTING.md with contribution guidelines
- Added comprehensive integration tests for FeedsearchSpider (14 new tests)
- Improved test coverage from 79% to 80% overall
- Improved spider.py coverage from 36% to 56% (+20 percentage points)
- Enhanced CLAUDE.md with comprehensive testing guidelines and workflow instructions

### Changed
- **100% Backward Compatible**: Original `search()` and `search_async()` functions unchanged
  - Still return `List[FeedInfo]` exactly as before
  - Empty list on error (unchanged behavior)
  - Type signatures unchanged
  - No code changes required for existing users
- Moved `pytest-xdist` from runtime dependencies to dev dependencies
- Optimized test suite performance (30s → 2.6s for crawler tests)
- Updated MockCrawler to use shorter default timeout (0.5s) for faster tests
- Updated GitHub Actions CodeQL workflow to use latest versions (v4/v3)
- Total test count increased from 340 to 582 tests (+242 tests)

### Fixed
- Fixed `datetime.utcnow()` deprecation warnings by using `datetime.now(timezone.utc)`
- Fixed unawaited coroutine in `SiteMetaParser.parse_item()` by awaiting `self.follow()`
- Fixed unawaited coroutine in test mocks by using `AsyncMock` properly
- Removed unused imports and variables flagged by ruff linter

### Documentation
- Created `docs/API_DESIGN_OPTIONS.md` analyzing 8 API design patterns for error handling
- Created `docs/OPTION3_IMPLEMENTATION_SUMMARY.md` documenting the implementation approach
- Updated README.md with error handling examples and usage patterns
- Added migration examples for users who want to adopt new error handling API

## [1.0.3] - 2024-08-21

### Changed
- Migrated package management and build tools to uv
- Updated dependencies to latest versions
- Added stricter type hints throughout codebase

### Fixed
- Improved queue handling in crawler
- Updated download handling with additional tests
- Fixed typing errors in lib.py

## [1.0.2] - Earlier releases

See git history for changes prior to 1.0.3.

## [0.2.7] - Earlier releases

Historical version. See git history for details.

---

[Unreleased]: https://github.com/DBeath/feedsearch-crawler/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/DBeath/feedsearch-crawler/compare/v1.0.3...v2.0.0
[1.0.3]: https://github.com/DBeath/feedsearch-crawler/releases/tag/v1.0.3
[0.2.7]: https://github.com/DBeath/feedsearch-crawler/releases/tag/0.2.7
