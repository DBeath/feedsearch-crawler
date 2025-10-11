# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added `py.typed` marker file for PEP 561 type checking support
- Added pytest warning filters for AsyncMock and feedparser deprecation warnings
- Added CHANGELOG.md to track project changes
- Added CONTRIBUTING.md with contribution guidelines
- Added comprehensive integration tests for FeedsearchSpider (14 new tests)
- Improved test coverage from 79% to 80% overall
- Improved spider.py coverage from 36% to 56% (+20 percentage points)
- Enhanced CLAUDE.md with comprehensive testing guidelines and workflow instructions

### Changed
- Moved `pytest-xdist` from runtime dependencies to dev dependencies
- Optimized test suite performance (30s → 2.6s for crawler tests)
- Updated MockCrawler to use shorter default timeout (0.5s) for faster tests
- Updated GitHub Actions CodeQL workflow to use latest versions (v4/v3)
- Total test count increased from 326 to 340 tests

### Fixed
- Fixed `datetime.utcnow()` deprecation warnings by using `datetime.now(timezone.utc)`
- Fixed unawaited coroutine in `SiteMetaParser.parse_item()` by awaiting `self.follow()`
- Fixed unawaited coroutine in test mocks by using `AsyncMock` properly
- Removed unused imports and variables flagged by ruff linter

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

[Unreleased]: https://github.com/DBeath/feedsearch-crawler/compare/v1.0.3...HEAD
[1.0.3]: https://github.com/DBeath/feedsearch-crawler/releases/tag/v1.0.3
[0.2.7]: https://github.com/DBeath/feedsearch-crawler/releases/tag/0.2.7
