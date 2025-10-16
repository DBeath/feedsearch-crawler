# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Type: Python Library

**feedsearch-crawler** is a **library package** designed to be consumed by other Python projects. It is NOT an end-user application.

### Key Implications

1. **Stability is Critical**: Breaking changes affect downstream users
2. **API Surface Matters**: All public APIs must be well-documented and tested
3. **Dependencies Must Be Minimal**: Keep dependency tree small to avoid conflicts
4. **Backward Compatibility**: Use semantic versioning and deprecation warnings
5. **Build Size Matters**: Distributed via PyPI, keep package lean

### Target Audience

- Python developers integrating feed discovery into their applications
- Web scraping and content aggregation tools
- RSS/Atom feed readers and aggregators
- API services that discover feeds (like feedsearch.dev)

### Public API Surface

The library exposes these public APIs in `__init__.py`:
- `search(url, ...)` - Synchronous feed search
- `search_async(url, ...)` - Async feed search
- `output_opml(feeds)` - Convert feeds to OPML format
- `FeedInfo` - Feed metadata class with `serialize()` method
- `FeedsearchSpider` - Main spider class (advanced usage)

**Changes to these must maintain backward compatibility.**

## Commands

### Development with uv

This project uses [uv](https://docs.astral.sh/uv/) for package management and development:

- `uv sync` - Install dependencies and sync the environment
- `uv run ruff check` - Run linting checks
- `uv run ruff format` - Format code
- `uv run pytest` - Run all tests
- `uv run pytest --durations=20` - Show 20 slowest tests
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

### Publishing to PyPI

**Prerequisites:**
- Maintainer access to feedsearch-crawler on PyPI
- PyPI API token configured

**Publishing workflow:**

```bash
# 1. Update version in pyproject.toml
# Follow semantic versioning: MAJOR.MINOR.PATCH

# 2. Update CHANGELOG.md with release notes

# 3. Run full test suite
uv run pytest

# 4. Build the package
uv build

# 5. Check build artifacts
ls dist/
# Should see: feedsearch_crawler-X.Y.Z-py3-none-any.whl
#             feedsearch_crawler-X.Y.Z.tar.gz

# 6. Upload to TestPyPI (optional but recommended)
uv publish --token $TEST_PYPI_TOKEN --publish-url https://test.pypi.org/legacy/

# 7. Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ feedsearch-crawler

# 8. Upload to PyPI
uv publish --token $PYPI_TOKEN

# 9. Create git tag
git tag v1.0.3
git push origin v1.0.3

# 10. Create GitHub release with CHANGELOG notes
```

**Semantic versioning guidelines:**
- **MAJOR** (1.0.0 → 2.0.0): Breaking API changes
- **MINOR** (1.0.0 → 1.1.0): New features, backward compatible
- **PATCH** (1.0.0 → 1.0.1): Bug fixes, backward compatible

**Before publishing checklist:**
- [ ] All tests pass
- [ ] CHANGELOG.md updated
- [ ] Version bumped in pyproject.toml
- [ ] README.md examples still work
- [ ] No debug code or print statements
- [ ] Dependencies properly specified

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

## Development Workflow

### Before Starting Any Work

**ALWAYS do these steps first:**

1. **Run existing tests** to establish baseline:
   ```bash
   uv run pytest
   ```

2. **Check git status** to understand current state:
   ```bash
   git status
   ```

3. **For test work, check performance**:
   ```bash
   uv run pytest --durations=20
   ```

4. **Search for existing patterns** before creating new code/tests

### Making Changes

**Validate incrementally - DO NOT batch changes:**

1. Make a small, logical change
2. Run tests immediately: `uv run pytest`
3. Fix any warnings or errors BEFORE proceeding
4. Repeat for next change

**Never create multiple new tests without validating they pass first.**

### Before Completing Work

**Run these checks - ALL must pass with NO warnings:**

1. Full test suite: `uv run pytest`
2. Linting: `uv run ruff check`
3. Check for warnings in test output
4. Verify git status shows only intended changes
5. Update CHANGELOG.md for user-visible changes

## Testing Guidelines

### Critical Rules - MUST Follow

1. **Check existing tests FIRST** - Search tests/ directory before creating new ones
2. **Read actual code** - Don't guess API signatures, read the implementation
3. **Start with 2-3 simple tests** - Validate they pass, THEN expand
4. **Run tests after EACH addition** - Never create 10+ tests without validation
5. **Fix ALL warnings** - Zero tolerance for warnings in test output

### Test Performance Requirements

**Strict requirements - tests that violate these must be fixed:**

- Individual tests: Must complete in **< 1 second**
- Test files: Must complete in **< 5 seconds**
- Full test suite: Must complete in **< 10 seconds**

**Common performance pitfalls:**

- Using production timeout defaults in tests (e.g., 30s)
- MockCrawler inherits `total_timeout=30.0` - override with `total_timeout=0.1-1.0`
- Awaiting real network calls instead of mocking
- Creating actual crawler instances that run full workflows

**Always use short timeouts in tests:**

```python
# ✅ CORRECT - Fast test timeout
spider = FeedsearchSpider(concurrency=1, total_timeout=0.5)
crawler = MockCrawler(total_timeout=0.1)

# ❌ WRONG - Will wait 30 seconds
spider = FeedsearchSpider(concurrency=1)  # Uses default 30s timeout
```

### Test Creation Workflow

**Follow this exact order:**

1. Search for similar tests in `tests/` directory
2. Read the actual implementation to understand:
   - Function signatures and return types
   - Whether functions are sync or async
   - Whether functions return values or are generators
   - Required vs optional parameters
3. Create 2-3 simple tests
4. Run tests: `uv run pytest path/to/test_file.py`
5. Fix any errors or warnings
6. Only after tests pass, add more tests
7. Repeat steps 4-6 for each addition

### Common Test Anti-Patterns

**DO NOT do these - they cause failures:**

❌ Creating 10+ tests before running any
❌ Guessing that a function returns a value when it yields
❌ Guessing that a function is async when it's sync
❌ Using `async for` on functions that aren't async generators
❌ Creating string URLs when code expects URL objects
❌ Using production defaults (timeouts, settings) in tests
❌ Extensive mocking when simple integration tests work better

**DO these instead:**

✅ Create 2-3 tests, run them, validate, then continue
✅ Read the actual code to see return types and signatures
✅ Check if similar tests exist and copy their patterns
✅ Use appropriate test fixtures (MockCrawler, etc.)
✅ Use test-specific timeouts and settings
✅ Simple integration tests over complex mocking

### Understanding Async Code

**Before creating async tests, verify:**

```python
# Is it async?
async def foo():  # YES - use 'await foo()'

# Is it an async generator?
async def foo():
    yield item  # YES - use 'async for item in foo()'

# Check actual return type:
async def parse_item(self, ...):
    return item  # Returns single item, NOT a generator

async def parse_response(self, ...):
    yield item1
    yield item2  # Is async generator
```

**Correct usage patterns:**

```python
# Async function returning value
result = await spider.process_item(item)

# Async generator
async for item in spider.parse_response(request, response):
    items.append(item)

# Regular function
result = spider.add_favicon(favicon)  # No await
```

### Coverage Improvement Strategy

**Realistic expectations:**

- Aim for 10-15 percentage point improvements per component
- Some code (async orchestration, network I/O) is hard to unit test
- Don't chase 100% coverage on integration workflows
- Simple integration tests often beat complex mocks

**Prioritization:**

1. Low-coverage critical components first (spider.py, downloader.py)
2. Test error paths and edge cases
3. Stop at diminishing returns (over-mocking, fragile tests)

## Code Quality Standards

### Zero Tolerance Items

**These MUST be fixed before completing work:**

- ❌ Failing tests
- ❌ Warnings in test output (deprecation, unawaited coroutines, etc.)
- ❌ Linting errors from ruff
- ❌ Unused imports or variables
- ❌ Tests slower than performance requirements

### Type Hints

- All functions must have type hints for parameters and return values
- Use `URL` from yarl, not `str` for URLs
- Use proper async return types: `AsyncGenerator`, `Awaitable`, etc.
- Check existing code for type patterns before creating new types

### Code Style

- Follow existing patterns in the codebase
- Use ruff for formatting (automatically applied)
- Maximum line length: 88 characters
- Descriptive names for variables and functions

## Documentation Organization

### Documentation Files

**All planning and summary documents MUST be placed in the `docs/` folder.**

**Required format for all documentation:**

```markdown
# Document Title

**Created:** YYYY-MM-DD
**Updated:** YYYY-MM-DD

---

[Document content starts here]
```

**When to create documentation:**

- Implementation plans for complex features
- Implementation summaries after completing features
- Architecture decision records (ADRs)
- Migration guides for breaking changes
- Performance analysis and comparisons

**When updating existing documentation:**

- Update the **Updated:** date to the current date
- Leave the **Created:** date unchanged
- Add change notes if the update is significant

**Example documentation files:**

- `docs/ROBOTS_SITEMAP_IMPLEMENTATION_PLAN.md` - Planning document with options analysis
- `docs/ROBOTS_SITEMAP_IMPLEMENTATION_SUMMARY.md` - Implementation summary with results
- `docs/BUILD_SIZE_COMPARISON.md` - Dependency size comparison analysis

**Documentation standards:**

- Use clear, descriptive titles
- Include table of contents for documents >200 lines
- Use code examples where helpful
- Include performance metrics if relevant
- Link to related files and documentation

## Common Pitfalls and Solutions

### Pitfall: Slow Tests

**Problem:** Test takes 30 seconds to run
**Cause:** Using production `total_timeout=30.0` default
**Solution:** Always set `total_timeout=0.1-1.0` in test instances

### Pitfall: Unawaited Coroutine Warnings

**Problem:** `RuntimeWarning: coroutine 'foo' was never awaited`
**Cause:** Async function not awaited, or using wrong pattern
**Solution:**
- Check if function is async: `async def` → use `await`
- Check if it's a generator: `yield` → use `async for`
- Use `AsyncMock` for mock async functions

### Pitfall: TypeError with URL Objects

**Problem:** `TypeError: Constructor parameter should be str`
**Cause:** Passing `None` or wrong type to `URL()` constructor
**Solution:**
- Check FeedInfo/SiteMeta URL fields - they should be URL objects
- Use `URL("https://example.com")` not `"https://example.com"`
- Handle None values before passing to URL()

### Pitfall: All Tests Fail After Bulk Creation

**Problem:** Created 10 tests, all fail with different errors
**Cause:** Didn't validate incrementally, guessed at API behavior
**Solution:**
- DELETE the failing tests
- Read the actual implementation code
- Create 2 simple tests that you're confident about
- Run and fix until they pass
- Then add more tests one at a time

## Compact Mode Instructions

When using compact mode:

- Focus output on test results and code changes only
- Minimize explanatory text
- Show only failures, warnings, and actionable errors
- Use TodoWrite for multi-step tasks to track progress silently
- Provide concise summaries at completion

## Summary

**The Golden Rules:**

1. ✅ ALWAYS run tests before AND after changes
2. ✅ ALWAYS read code before creating tests
3. ✅ ALWAYS validate incrementally (not in batches)
4. ✅ ALWAYS fix warnings (zero tolerance)
5. ✅ ALWAYS use test-appropriate timeouts
6. ✅ NEVER create >3 tests without validating they pass
7. ✅ NEVER guess at API signatures - read the code
8. ✅ NEVER ignore warnings - they become errors later

**Result:** Clean code, passing tests, no warnings, fast test suite.
