# Feed Specifications: Date Handling Guidelines

**Created:** 2025-01-22
**Updated:** 2025-01-22

---

## Summary

This document summarizes how RSS, Atom, and JSON Feed specifications define date formats and handle invalid dates, based on their official specifications.

## RSS 2.0 Specification

### Date Format Requirements

**Element:** `<pubDate>` (publication date)

**Format:** RFC 822 date/time format

**Key Requirements:**
- Must conform to RFC 822 Date and Time Specification
- Year may be expressed with 2 or 4 characters (4 preferred)
- Example: `<pubDate>Sun, 19 May 2002 15:21:36 GMT</pubDate>`

### Invalid Date Handling

**Specification Guidance:** Minimal

The RSS 2.0 specification provides limited guidance on invalid dates:
- **Future dates:** "If it's a date in the future, aggregators may choose to not display the item until that date."
- **Malformed dates:** No explicit guidance provided

**Implication:** Feed consumers have discretion in how to handle invalid or malformed dates. The specification focuses on producer requirements rather than consumer error handling.

**Reference:** [RSS 2.0 Specification](https://www.rssboard.org/rss-specification)

---

## Atom Specification (RFC 4287)

### Date Format Requirements

**Elements:** `atom:updated` (required), `atom:published` (optional)

**Format:** RFC 3339 date-time format (strict)

**Key Requirements:**
- Content MUST conform to RFC 3339 `date-time` production
- Uppercase 'T' MUST separate date and time
- Uppercase 'Z' MUST be present if no numeric timezone offset
- Examples:
  - `2003-12-13T18:30:02Z`
  - `2003-12-13T18:30:02+01:00`

**Semantics:**
- `atom:updated`: Most recent instant when entry/feed was significantly modified
- `atom:published`: Instant associated with early life cycle event (creation/first availability)

### Invalid Date Handling

**Specification Guidance:** None provided

The RFC 4287 specification:
- Defines strict producer requirements
- Does not address consumer error-handling procedures
- Leaves implementation decisions to individual processors

**Implication:** Feed processors must decide their own error recovery strategies.

**Reference:** [RFC 4287 - The Atom Syndication Format](https://datatracker.ietf.org/doc/html/rfc4287)

---

## JSON Feed Specification (v1.1)

### Date Format Requirements

**Fields:** `date_published`, `date_modified` (both optional)

**Format:** RFC 3339 format

**Key Requirements:**
- Must use RFC 3339 format when present
- Timezone information included in timestamp
- Example: `2010-02-07T14:04:00-05:00`

**Note:** Both date fields are optional; only `id` is required for items.

### Invalid Date Handling

**Specification Guidance:** Pragmatic recovery recommended

The JSON Feed specification explicitly addresses invalid dates:

> "you might substitute the date the reader parsed it" when encountering unparseable timestamps.

**Philosophy:**
> "if an error can be recovered from without significantly harming that experience, then it's better than just refusing to use the feed."

**Key Points:**
- Feed readers should employ pragmatic recovery strategies
- User experience takes priority over strict validation
- Unparseable dates can be substituted with current time/date
- Missing dates are valid (fields are optional)

**Reference:** [JSON Feed Version 1.1](https://jsonfeed.org/version/1.1)

---

## Comparison Summary

| Aspect | RSS 2.0 | Atom (RFC 4287) | JSON Feed |
|--------|---------|-----------------|-----------|
| **Date Format** | RFC 822 | RFC 3339 (strict) | RFC 3339 |
| **Required?** | Optional | `updated` required | Optional |
| **Invalid Date Guidance** | Minimal | None | Pragmatic recovery |
| **Error Philosophy** | Not specified | Not specified | User experience first |
| **Future Dates** | May hide until date | Not specified | Not specified |
| **Timezone** | Optional (GMT common) | Required (Z or offset) | Required (offset) |

---

## Implications for feedsearch-crawler

### Current Implementation Alignment

Our implementation in `parse_date_with_comparison()` aligns well with all specifications:

1. **Graceful Degradation:** Returns `None` for unparseable dates rather than failing
2. **Multi-Strategy Parsing:** Tries RFC 3339 → RFC 822 → dateutil fallback
3. **Comparison Logic:** Validates feedparser results against dateutil for accuracy
4. **Future Date Filtering:** `entry_dates()` filters out future dates per RSS guidance

### Best Practices

Based on specifications and `parse_date_with_comparison()` implementation:

**✅ DO:**
- Accept multiple date formats (RSS, Atom, JSON feeds use different standards)
- Return `None` for unparseable dates (allows feed processing to continue)
- Log invalid dates for debugging (`logger.debug()`)
- Filter future dates from feed entry lists
- Prefer stricter parsers (ISO 8601/RFC 3339) before flexible parsers (dateutil)
- Compare multiple parsing results when available

**❌ DON'T:**
- Reject entire feed due to invalid date in one entry
- Throw exceptions for unparseable dates (breaks feed processing)
- Use unparseable dates as "now" (can skew velocity calculations)
- Ignore timezone information
- Trust only one parsing method (feedparser can differ from dateutil)

### Error Recovery Strategy

Current implementation (`entry_dates()` in feed_info_parser.py:455-475):

```python
try:
    entry_date = parse_date_with_comparison(
        date_string, parsed_tuple, locale
    )

    if entry_date and entry_date.date() <= current_date:
        yield entry_date
except (KeyError, ValueError, AttributeError):
    pass  # Skip entries with invalid dates
```

This approach:
- Continues processing remaining entries if one fails
- Filters out unparseable and future dates
- Maintains feed velocity and last_updated accuracy
- Aligns with JSON Feed's pragmatic philosophy

---

## References

1. **RSS 2.0:** https://www.rssboard.org/rss-specification
2. **Atom (RFC 4287):** https://datatracker.ietf.org/doc/html/rfc4287
3. **JSON Feed v1.1:** https://jsonfeed.org/version/1.1
4. **RFC 822 (Date/Time):** https://www.rfc-editor.org/rfc/rfc822
5. **RFC 3339 (Date/Time):** https://www.rfc-editor.org/rfc/rfc3339

---

## Implementation Files

- `src/feedsearch_crawler/feed_spider/lib.py:152-209` - `parse_date_with_comparison()`
- `src/feedsearch_crawler/feed_spider/feed_info_parser.py:455-475` - `entry_dates()`
- `tests/feed_spider/test_date_comparison.py` - Date comparison tests
