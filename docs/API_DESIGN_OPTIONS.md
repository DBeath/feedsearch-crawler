# API Design Options for Error Handling

**Created:** 2025-01-28

---

## Problem Statement

The current API returns `List[FeedInfo]`, which cannot easily accommodate additional return values (errors, statistics). We need to add error information without breaking existing code.

**Current API:**
```python
feeds = search("https://example.com")  # Returns List[FeedInfo]
```

**Desired capability:**
- Return error information when root URL fails
- Optionally return statistics
- Maintain backward compatibility

---

## Option 1: Conditional Return Type (Current Implementation) ❌

**Implementation:**
```python
def search(url, include_errors=False) -> Union[List[FeedInfo], SearchResult]:
    if include_errors:
        return SearchResult(feeds=[...], root_error=...)
    return [...]  # List[FeedInfo]
```

**Usage:**
```python
# Default
feeds = search("https://example.com")  # List[FeedInfo]

# With errors
result = search("https://example.com", include_errors=True)  # SearchResult
if isinstance(result, SearchResult):
    ...
```

**Pros:**
- Backward compatible (default returns list)
- No code changes required for existing users

**Cons:**
- ❌ **Type ambiguity**: Return type depends on parameter
- ❌ **Runtime type checking**: Must use `isinstance()` or type guards
- ❌ **Poor type safety**: Static type checkers struggle with this pattern
- ❌ **API confusion**: Different return types from same function
- ❌ **Documentation complexity**: Must explain both return types

**Verdict:** Poor design pattern, confusing API

---

## Option 2: Always Return SearchResult (Breaking Change) ❌

**Implementation:**
```python
def search(url) -> SearchResult:
    return SearchResult(feeds=[...], root_error=None)
```

**Usage:**
```python
result = search("https://example.com")
for feed in result.feeds:  # Must use .feeds attribute
    print(feed.url)
```

**Pros:**
- Clean, single return type
- Type-safe
- Extensible (can add more fields)

**Cons:**
- ❌ **BREAKING CHANGE**: Requires major version bump (2.0.0)
- ❌ **Code changes required**: All users must update `.feeds`
- ❌ **Not backward compatible**: Existing code breaks

**Verdict:** Clean design but breaks production code

---

## Option 3: New Function Name (Recommended) ✅

**Implementation:**
```python
def search(url) -> List[FeedInfo]:
    """Original function, unchanged."""
    return [...]

def search_with_info(url) -> SearchResult:
    """New function with error handling."""
    return SearchResult(feeds=[...], root_error=None, stats=None)
```

**Usage:**
```python
# Existing code unchanged
feeds = search("https://example.com")

# New code uses new function
result = search_with_info("https://example.com")
if result.root_error:
    print(f"Error: {result.root_error.message}")
for feed in result.feeds:
    print(feed.url)
```

**Pros:**
- ✅ **100% backward compatible**: Original function unchanged
- ✅ **Type-safe**: Each function has single, clear return type
- ✅ **No confusion**: Different functions for different use cases
- ✅ **Self-documenting**: Function name indicates richer return
- ✅ **Gradual migration**: Users can migrate at their own pace
- ✅ **Easy to deprecate**: Can deprecate `search()` in future

**Cons:**
- Two functions with similar purposes (minor API duplication)
- Existing function name doesn't hint at limited functionality

**Verdict:** Best balance of compatibility and clarity

---

## Option 4: SearchResult with List Subclassing ⚠️

**Implementation:**
```python
class SearchResult(list):
    """List subclass that adds error information."""

    def __init__(self, feeds, root_error=None, stats=None):
        super().__init__(feeds)
        self.root_error = root_error
        self.stats = stats

def search(url) -> SearchResult:
    return SearchResult([...], root_error=None)
```

**Usage:**
```python
# Works as list (backward compatible)
feeds = search("https://example.com")
for feed in feeds:
    print(feed.url)

# Can also access error info
if feeds.root_error:
    print(f"Error: {feeds.root_error.message}")
```

**Pros:**
- ✅ **Mostly backward compatible**: Works as list
- ✅ **Single return type**: Always `SearchResult`
- ✅ **`isinstance(result, list)` works**: True list subclass
- ✅ **Extensible**: Can add more attributes

**Cons:**
- ⚠️ **Conceptual confusion**: "A list that has errors" is semantically odd
- ⚠️ **Mutation issues**: Users can `.append()`, `.remove()` etc.
- ⚠️ **Type annotation changes**: Still breaks strict type checking
- ⚠️ **Serialization complexity**: How to serialize the extra attributes?
- ⚠️ **Unexpected behavior**: List operations might not preserve attributes

**Verdict:** Clever but conceptually problematic

---

## Option 5: Context Manager / Wrapper ⚠️

**Implementation:**
```python
class SearchContext:
    def __init__(self, url):
        self.url = url
        self.feeds = []
        self.root_error = None
        self.stats = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

def search(url) -> List[FeedInfo]:
    """Original function."""
    return [...]

def search_context(url) -> SearchContext:
    """Context manager for detailed results."""
    ctx = SearchContext(url)
    # perform search
    return ctx
```

**Usage:**
```python
# Original API
feeds = search("https://example.com")

# New API with context
with search_context("https://example.com") as ctx:
    if ctx.root_error:
        print(f"Error: {ctx.root_error.message}")
    for feed in ctx.feeds:
        print(feed.url)
```

**Pros:**
- Backward compatible
- Explicit different API

**Cons:**
- Context manager doesn't add value here (no cleanup needed)
- Overcomplicated for simple data return
- Unusual pattern for data retrieval

**Verdict:** Overengineered for this use case

---

## Option 6: Exception for Errors (Pythonic) ⚠️

**Implementation:**
```python
class SearchError(Exception):
    def __init__(self, url, error_type, message, status_code=None):
        self.url = url
        self.error_type = error_type
        self.message = message
        self.status_code = status_code
        super().__init__(message)

def search(url) -> List[FeedInfo]:
    """Raises SearchError if root URL fails."""
    feeds = [...]
    if root_url_failed:
        raise SearchError(url, ErrorType.DNS_FAILURE, "Domain not found")
    return feeds
```

**Usage:**
```python
try:
    feeds = search("https://nonexistent.com")
    for feed in feeds:
        print(feed.url)
except SearchError as e:
    print(f"Search failed: {e.message}")
    print(f"Error type: {e.error_type}")
```

**Pros:**
- ✅ **Pythonic**: Errors as exceptions is idiomatic Python
- ✅ **Backward compatible**: Can be added without breaking changes
- ✅ **Clear semantics**: Exception = exceptional condition
- ✅ **Type-safe**: Return type always `List[FeedInfo]`
- ✅ **Opt-in**: Users can choose to catch or let it propagate

**Cons:**
- ⚠️ **Philosophy change**: Currently returns empty list on failure
- ⚠️ **Requires try/except**: More boilerplate for error checking
- ⚠️ **Partial results issue**: What if some feeds found but root failed?

**Verdict:** Pythonic but changes error handling philosophy

---

## Option 7: Separate Error Query Function ⚠️

**Implementation:**
```python
_last_search_error = None  # Module-level state

def search(url) -> List[FeedInfo]:
    """Original function."""
    global _last_search_error
    _last_search_error = None
    feeds = [...]
    if root_failed:
        _last_search_error = SearchError(...)
    return feeds

def get_last_error() -> Optional[SearchError]:
    """Get error from last search."""
    return _last_search_error
```

**Usage:**
```python
feeds = search("https://example.com")
if not feeds:
    error = get_last_error()
    if error:
        print(f"Search failed: {error.message}")
```

**Pros:**
- Backward compatible
- Simple API

**Cons:**
- ❌ **Global state**: Thread-unsafe, error-prone
- ❌ **Implicit coupling**: Error tied to last call
- ❌ **Testing difficulty**: Hard to mock and test
- ❌ **Not thread-safe**: Multiple concurrent calls interfere

**Verdict:** Anti-pattern, avoid global state

---

## Option 8: Callback Pattern ⚠️

**Implementation:**
```python
def search(url, on_error=None) -> List[FeedInfo]:
    """Original function with optional error callback."""
    feeds = [...]
    if root_failed and on_error:
        on_error(SearchError(...))
    return feeds
```

**Usage:**
```python
error_info = []

def handle_error(err):
    error_info.append(err)

feeds = search("https://example.com", on_error=handle_error)
if error_info:
    print(f"Error: {error_info[0].message}")
```

**Pros:**
- Backward compatible (callback optional)

**Cons:**
- ❌ **Awkward in Python**: Callbacks more common in async JS
- ❌ **Requires closure**: Need to capture error externally
- ❌ **Not intuitive**: Doesn't match Python idioms

**Verdict:** Doesn't fit Python patterns

---

## Comparison Matrix

| Option | Backward Compatible | Type Safe | Pythonic | Complexity | Recommended |
|--------|-------------------|-----------|----------|------------|-------------|
| 1. Conditional Return | ✅ | ❌ | ❌ | Medium | ❌ |
| 2. Always SearchResult | ❌ | ✅ | ✅ | Low | ❌ |
| 3. New Function | ✅ | ✅ | ✅ | Low | ✅ |
| 4. List Subclass | ⚠️ | ⚠️ | ⚠️ | Medium | ⚠️ |
| 5. Context Manager | ✅ | ✅ | ❌ | High | ❌ |
| 6. Exceptions | ✅ | ✅ | ✅ | Low | ⚠️ |
| 7. Separate Query | ✅ | ✅ | ❌ | Medium | ❌ |
| 8. Callbacks | ✅ | ✅ | ❌ | Medium | ❌ |

---

## Recommended Approach: Option 3 (New Function)

### Implementation

```python
def search(url, **kwargs) -> List[FeedInfo]:
    """
    Search for feeds at the given URL(s).

    Returns:
        List[FeedInfo]: List of discovered feeds

    Note:
        This function returns an empty list if the root URL fails.
        Use search_with_info() to get detailed error information.
    """
    result = search_with_info(url, **kwargs)
    return result.feeds


def search_with_info(url, include_stats=False, **kwargs) -> SearchResult:
    """
    Search for feeds with detailed error and statistics information.

    Returns:
        SearchResult: Object containing:
            - feeds: List of discovered feeds
            - root_error: Error info if root URL failed (None if successful)
            - stats: Crawl statistics (if include_stats=True)

    Examples:
        >>> result = search_with_info("https://example.com")
        >>> if result.root_error:
        ...     print(f"Error: {result.root_error.message}")
        >>> for feed in result.feeds:
        ...     print(feed.url)
    """
    crawler = FeedsearchSpider(**kwargs)
    await crawler.crawl(url)

    feeds = sort_urls(list(crawler.items))
    root_error = crawler.get_root_error()
    stats = crawler.get_stats() if include_stats else None

    return SearchResult(feeds=feeds, root_error=root_error, stats=stats)
```

### Benefits

1. **Perfect Backward Compatibility**: `search()` unchanged, returns `List[FeedInfo]`
2. **Type Safe**: Each function has single, clear return type
3. **Progressive Disclosure**: Simple use case (no errors) uses simple API
4. **Self-Documenting**: Function names clearly indicate capabilities
5. **Easy Migration**: Users can switch when they need error handling
6. **Future-Proof**: Can deprecate `search()` in v3.0 if desired

### Migration Path

**Phase 1 (v1.1.0):**
- Add `search_with_info()`
- Keep `search()` unchanged
- Document both functions

**Phase 2 (v1.x):**
- Encourage `search_with_info()` in documentation
- `search()` remains supported

**Phase 3 (v2.0.0 - optional):**
- Add deprecation warning to `search()`
- Document migration path

**Phase 4 (v3.0.0 - optional):**
- Remove `search()` or make it alias to `search_with_info()`

---

## Alternative: Option 6 (Exceptions) - Also Valid

If we want to embrace Python's error handling philosophy:

```python
def search(url, **kwargs) -> List[FeedInfo]:
    """
    Search for feeds at the given URL(s).

    Returns:
        List[FeedInfo]: List of discovered feeds

    Raises:
        SearchError: If the root URL cannot be accessed (DNS failure,
            SSL error, HTTP error, timeout, etc.)

    Note:
        This function only raises for root URL failures. Discovered
        URLs that fail are silently skipped.
    """
    crawler = FeedsearchSpider(**kwargs)
    await crawler.crawl(url)

    feeds = sort_urls(list(crawler.items))
    root_error = crawler.get_root_error()

    if root_error:
        raise SearchError(
            url=root_error.url,
            error_type=root_error.error_type,
            message=root_error.message,
            status_code=root_error.status_code
        )

    return feeds
```

**Usage:**
```python
try:
    feeds = search("https://nonexistent.com")
    for feed in feeds:
        print(feed.url)
except SearchError as e:
    print(f"Search failed: {e.message}")
    print(f"Error type: {e.error_type}")
```

This is more Pythonic but changes the error handling contract.

---

## Recommendation

**Primary: Option 3 (New Function Name)**
- Implement `search_with_info()` that returns `SearchResult`
- Keep `search()` returning `List[FeedInfo]`
- Version: 1.1.0 (MINOR bump)

**Secondary: Option 6 (Exceptions)**
- Make `search()` raise `SearchError` on root URL failure
- Version: 2.0.0 (MAJOR bump - breaking change)
- Consider for next major version

Both are valid, but Option 3 provides the safest migration path.
