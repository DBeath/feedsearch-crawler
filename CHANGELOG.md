# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2025-12-30

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

[Unreleased]: https://github.com/DBeath/feedsearch-crawler/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/DBeath/feedsearch-crawler/compare/v1.0.3...v1.1.0
[1.0.3]: https://github.com/DBeath/feedsearch-crawler/releases/tag/v1.0.3
[0.2.7]: https://github.com/DBeath/feedsearch-crawler/releases/tag/0.2.7
