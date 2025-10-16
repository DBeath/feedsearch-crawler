# Robots.txt + Sitemap Implementation Plan

**Created:** 2025-01-16
**Updated:** 2025-01-16

---

## Current State

**Completed:**
- ✅ `respect_robots` parameter added to Crawler.__init__
- ✅ RobotsMiddleware is conditionally added based on `respect_robots`
- ✅ RobotsMiddleware extracts sitemap URLs from robots.txt
- ✅ `sitemap_urls` storage and `get_sitemaps_for_host()` method added

## Goals

1. Fetch robots.txt as the **first request** for each domain (highest priority)
2. Extract sitemap URLs from robots.txt
3. Fetch sitemaps as **high priority requests** (after robots.txt, before regular URLs)
4. Parse sitemap XML to extract URLs
5. Filter sitemap URLs for feed-like patterns
6. Add discovered URLs to queue with appropriate priority
7. Maintain **backward compatibility** - existing code should work unchanged

## Priority System

Current priority (lower number = higher priority):
- Default request priority: 100
- Priority 0 is specified in code for certain requests

**Proposed priority levels:**
```
Priority 1:  robots.txt requests (highest)
Priority 5:  sitemap.xml requests
Priority 10: URLs discovered from sitemaps
Priority 100: Regular discovered URLs (default)
```

## Implementation Options

### Option 1: Asynchronous Priority-Based (RECOMMENDED)

**Approach:** Use existing priority queue system without blocking

**How it works:**
1. When `crawl()` starts, for each domain in `start_urls`:
   - Create robots.txt request with priority=1
   - Add to queue immediately
2. When robots.txt response comes back:
   - RobotsMiddleware extracts sitemaps
   - Spider callback creates sitemap requests with priority=5
3. When sitemap response comes back:
   - Parse XML and extract URLs
   - Filter for feed-like URLs
   - Create requests with priority=10
4. Regular page crawling continues with priority=100

**Pros:**
- ✅ Fully backward compatible
- ✅ Non-blocking - doesn't delay crawl start
- ✅ Uses existing priority queue infrastructure
- ✅ Natural async flow
- ✅ Handles multiple domains elegantly

**Cons:**
- ⚠️ Small race condition: first few requests might process before robots.txt (mitigated by priority)
- ⚠️ Requires callback coordination

**Implementation changes needed:**
1. Add `parse_robots_txt()` callback to Crawler
2. Add `parse_sitemap()` callback to Crawler
3. Modify `create_start_urls()` or `crawl()` to inject robots.txt requests
4. Update spider to handle robots/sitemap callbacks

---

### Option 2: Synchronous Robots Fetch (BLOCKING)

**Approach:** Fetch robots.txt synchronously before starting workers

**How it works:**
1. In `crawl()`, before creating workers:
   - For each domain, synchronously fetch robots.txt
   - Wait for all robots.txt to complete
   - Extract sitemaps and add them to initial queue
2. Then start workers as normal

**Pros:**
- ✅ Guarantees robots.txt is fetched first
- ✅ No race conditions
- ✅ Sitemaps can be added to initial queue

**Cons:**
- ❌ Blocks crawl start (delays by 1-3 seconds per domain)
- ❌ Breaks async pattern
- ❌ More complex error handling
- ❌ Harder to test
- ⚠️ Backward compatibility concern if users expect immediate crawl

**Implementation changes needed:**
1. Add `_fetch_robots_txt_sync()` method to Crawler
2. Modify `crawl()` to call it before worker creation
3. Add synchronous HTTP fetch logic
4. Handle timeouts and errors

---

### Option 3: Hybrid Approach

**Approach:** Priority-based but with explicit coordination

**How it works:**
1. Add robots.txt requests with priority=1 to queue
2. Use an asyncio.Event per domain to signal "robots.txt done"
3. Other requests for that domain wait on the event before processing
4. RobotsMiddleware sets the event when robots.txt completes

**Pros:**
- ✅ Guarantees robots.txt first per domain
- ✅ Mostly non-blocking
- ✅ Clear coordination

**Cons:**
- ⚠️ Adds complexity with events
- ⚠️ Requires request-level domain tracking
- ⚠️ Could create deadlocks if not careful

**Implementation changes needed:**
1. Add `_robots_ready_events: Dict[str, asyncio.Event]`
2. Modify `_handle_request()` to wait on event
3. Modify RobotsMiddleware to set events
4. Add domain extraction logic

---

## Recommendation: Option 1 (Asynchronous Priority-Based)

**Why:**
- Best balance of simplicity and effectiveness
- Maintains async patterns throughout
- Backward compatible
- Priority queue already handles ordering
- Small race condition is acceptable (worst case: 1-2 requests before robots.txt)

**The race condition is minimal because:**
- Priority 1 vs 100 means robots.txt will be processed first in almost all cases
- Workers pull from queue in priority order
- Even if 1-2 requests slip through, RobotsMiddleware caches robots.txt for subsequent requests

---

## Detailed Implementation Plan (Option 1)

### Phase 1: Crawler Changes

**File:** `src/feedsearch_crawler/crawler/crawler.py`

1. **Add methods to Crawler base class:**

```python
async def parse_robots_txt(self, request: Request, response: Response) -> AsyncGenerator:
    """Parse robots.txt response and queue sitemap requests.

    This callback is called when a robots.txt file is fetched.
    It extracts sitemap URLs and creates high-priority requests for them.
    """
    if not response.ok or not self._robots_middleware:
        return

    # Get sitemaps from middleware (already extracted)
    host = f"{response.url.scheme}://{response.url.host}"
    sitemaps = self._robots_middleware.get_sitemaps_for_host(host)

    logger.info(f"Found {len(sitemaps)} sitemap(s) for {host}")

    # Queue sitemap requests with priority=5
    for sitemap_url in sitemaps:
        req = await self.follow(
            sitemap_url,
            self.parse_sitemap,
            priority=5,
            allow_domain=True
        )
        if req:
            yield req

async def parse_sitemap(self, request: Request, response: Response) -> AsyncGenerator:
    """Parse sitemap XML and extract URLs.

    This callback parses sitemap.xml files and extracts feed-like URLs.
    Discovered URLs are queued with priority=10.
    """
    if not response.ok or not response.text:
        return

    # Use existing parse_sitemap function from lib
    from feedsearch_crawler.crawler.lib import parse_sitemap
    feed_urls = parse_sitemap(response.text)

    logger.info(f"Found {len(feed_urls)} potential feed URLs in {response.url}")

    # Queue discovered URLs with priority=10
    for url in feed_urls:
        req = await self.follow(
            url,
            self.parse_response,  # Use normal spider callback
            response=response,
            priority=10,
            allow_domain=True
        )
        if req:
            yield req

def _get_robots_txt_url(self, url: URL) -> str:
    """Get robots.txt URL for a given domain URL."""
    return f"{url.scheme}://{url.host}/robots.txt"
```

2. **Modify `crawl()` method to inject robots.txt requests:**

Add this section after initial URLs are created, before adding them to queue:

```python
# If respecting robots.txt, add robots.txt requests first
if self.respect_robots and self._robots_middleware:
    robots_urls_added = set()
    for url in initial_urls:
        robots_url = self._get_robots_txt_url(url)
        if robots_url not in robots_urls_added:
            robots_req = await self.follow(
                robots_url,
                self.parse_robots_txt,
                priority=1,  # Highest priority
                allow_domain=True
            )
            if robots_req:
                self._process_request(robots_req)
                robots_urls_added.add(robots_url)

# Then add regular start URLs (priority=100 default)
for url in initial_urls:
    req = await self.follow(coerce_url(url), self.parse_response, delay=0)
    if req:
        self._process_request(req)
```

### Phase 2: Spider Changes (FeedsearchSpider)

**File:** `src/feedsearch_crawler/feed_spider/spider.py`

**No changes needed** - spider inherits `parse_robots_txt` and `parse_sitemap` from Crawler base class.

Spider's `parse_response` method will handle URLs discovered from sitemaps just like any other URL.

### Phase 3: Improve Sitemap Parsing

**File:** `src/feedsearch_crawler/crawler/lib.py`

**Current `parse_sitemap()` function (lines 348-375):**
- ✅ Extracts `<loc>` elements
- ⚠️ Only matches URLs ending in .rss, .xml, .atom
- ⚠️ Misses URLs like `/feed` or `/rss`

**Enhancement needed:**

```python
def parse_sitemap(sitemap_xml: str) -> List[str]:
    """Parses a sitemap XML file and returns URLs of potential feeds.

    Enhanced to:
    1. Parse both regular sitemaps and sitemap indexes
    2. Filter for feed-like URLs (not just .xml extension)

    Args:
      sitemap_xml: The sitemap XML file, as a string.

    Returns:
      A list of URLs that are likely to be feeds.
    """
    # Create a regex pattern to match the "loc" elements in the sitemap
    loc_pattern = re.compile(r"<loc>(.*?)</loc>")

    # Create a list to store the URLs
    feed_urls: List[str] = []

    # Use the regex pattern to find all the "loc" elements in the sitemap
    for loc_element in loc_pattern.finditer(sitemap_xml):
        url = loc_element.group(1)

        # Filter for feed-like URLs
        url_lower = url.lower()
        if any(keyword in url_lower for keyword in [
            '/rss', '/feed', '/atom', '.rss', '.xml', '.atom',
            'rss.', 'feed.', 'atom.'
        ]):
            feed_urls.append(url)

    return feed_urls
```

### Phase 4: Update Public API

**File:** `src/feedsearch_crawler/__init__.py`

Add `respect_robots` to `search()` and `search_async()` signatures:

```python
def search(
    url: Union[URL, str, List[Union[URL, str]]],
    ...,
    respect_robots: bool = True,  # NEW PARAMETER
    ...
) -> List[FeedInfo]:
```

### Phase 5: Testing Strategy

**Test files to create/update:**

1. **Unit tests for RobotsMiddleware:**
   - `test_extract_sitemaps_from_robots()`
   - `test_get_sitemaps_for_host()`
   - `test_no_sitemaps_in_robots()`

2. **Unit tests for sitemap parsing:**
   - `test_parse_sitemap_extracts_feed_urls()`
   - `test_parse_sitemap_filters_non_feeds()`
   - `test_parse_sitemap_handles_sitemap_index()`

3. **Integration tests:**
   - `test_robots_txt_fetched_first()`
   - `test_sitemap_discovered_and_fetched()`
   - `test_feed_urls_extracted_from_sitemap()`
   - `test_respect_robots_false_skips_robots()`

4. **Priority tests:**
   - `test_robots_txt_priority_1()`
   - `test_sitemap_priority_5()`
   - `test_sitemap_urls_priority_10()`

---

## Migration Path

### For existing users:
```python
# Old code (still works, now respects robots.txt by default)
feeds = search("example.com")

# Opt out of robots.txt checking
feeds = search("example.com", respect_robots=False)
```

### Benefits users get automatically:
1. Robots.txt compliance (can opt out)
2. Sitemap-based feed discovery
3. Better feed URL coverage
4. No code changes needed

---

## Performance Considerations

**Additional requests per domain:**
- +1 request for robots.txt
- +N requests for sitemaps (typically 1-3)
- Total overhead: ~2-4 extra requests per domain

**Time impact:**
- Robots.txt: ~100-300ms per domain
- Sitemap: ~100-500ms per sitemap
- Total: ~200-800ms additional crawl time

**Benefits:**
- Discovers feeds that aren't linked from pages
- More comprehensive feed discovery
- Respects website crawling preferences

---

## Alternative: Sitemap-only Mode

Could add a separate parameter for users who want sitemap discovery without robots.txt blocking:

```python
def search(
    url: str,
    respect_robots: bool = True,     # Check robots.txt and respect disallow
    use_sitemaps: bool = True,        # Discover feeds via sitemaps
):
```

This allows:
- `respect_robots=True, use_sitemaps=True` - Full robots + sitemap (default)
- `respect_robots=True, use_sitemaps=False` - Robots.txt blocking only
- `respect_robots=False, use_sitemaps=True` - Sitemap discovery only
- `respect_robots=False, use_sitemaps=False` - Current behavior

---

## Summary

**Recommended approach:** Option 1 (Asynchronous Priority-Based)

**Key changes:**
1. Add robots.txt request with priority=1 in `crawl()`
2. Add `parse_robots_txt()` callback to queue sitemaps
3. Add `parse_sitemap()` callback to extract feed URLs
4. Enhance `parse_sitemap()` to filter better
5. All changes are backward compatible

**Timeline:**
- Phase 1 (Crawler): 1-2 hours
- Phase 2 (Spider): Minimal (inheritance)
- Phase 3 (Parsing): 30 minutes
- Phase 4 (API): 15 minutes
- Phase 5 (Tests): 2-3 hours

**Total: ~4-6 hours of implementation**

---

## Open Questions

1. Should sitemap discovery be optional separate from `respect_robots`?
2. Should we parse sitemap indexes recursively?
3. What's the maximum depth for sitemap recursion?
4. Should we cache sitemap URLs to avoid re-fetching?
5. How to handle compressed sitemaps (.xml.gz)?

---

## Decision Needed

**Please choose:**
- ✅ **Option 1: Asynchronous Priority-Based** (recommended)
- ⬜ Option 2: Synchronous Robots Fetch
- ⬜ Option 3: Hybrid Approach
- ⬜ Alternative suggestion

**Also decide:**
- Single `respect_robots` parameter (includes sitemaps)?
- Or separate `respect_robots` and `use_sitemaps` parameters?
