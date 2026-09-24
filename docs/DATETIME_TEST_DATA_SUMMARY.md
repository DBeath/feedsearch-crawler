# DateTime Test Data Structure - Summary

**Created:** 2025-10-20
**Updated:** 2025-10-20

---

## Overview

A comprehensive, extensible test data structure for datetime parsing across 15+ languages and multiple date formats.

## Files Created

| File | Purpose | Lines |
| ------ | --------- | ------- |
| `tests/feed_spider/datetime_test_data.py` | Core data structure with 53 test cases | ~700 |
| `tests/feed_spider/test_datetime_with_fixtures.py` | Example usage and integration tests | ~300 |
| `docs/DATETIME_TEST_DATA_GUIDE.md` | Complete documentation | ~600 |
| `docs/DATETIME_TEST_DATA_QUICKSTART.md` | Quick reference guide | ~300 |

## Test Coverage

```text
Total Test Cases: 53
Categories: 6
Languages: 15

By Behavior:
  ✅ parse_success: 25 tests (should pass)
  ❌ parse_fail: 8 tests (should return None)
  ⏭️  parse_xfail: 18 tests (expected to fail - not yet supported)
  ⚠️  parse_warn: 2 tests (parses with warnings)

By Format:
  📄 rfc3339: 15 tests (Atom, JSON Feed)
  📄 rfc822: 10 tests (RSS 2.0)
  📄 iso8601: 1 test
  📄 custom: 1 test
  🌍 localized: 18 tests (non-English)
  ❌ invalid: 8 tests (error handling)
```

## Languages Covered

### Western European (7)

- 🇫🇷 French (fr)
- 🇩🇪 German (de)
- 🇪🇸 Spanish (es)
- 🇮🇹 Italian (it)
- 🇵🇹 Portuguese (pt)
- 🇳🇱 Dutch (nl)
- 🇸🇪 Swedish (sv)

### Eastern European (2)

- 🇷🇺 Russian (ru) - Cyrillic
- 🇵🇱 Polish (pl)

### Asian (3)

- 🇯🇵 Japanese (ja) - Kanji
- 🇨🇳 Chinese (zh) - Simplified
- 🇰🇷 Korean (ko) - Hangul

### Middle Eastern (1)

- 🇸🇦 Arabic (ar) - Eastern Arabic numerals

### Other (2)

- 🇹🇷 Turkish (tr)
- 🇬🇧 English (en) - default

## Architecture

```text
┌─────────────────────────────────────┐
│     DATETIME_TEST_SUITE (dict)      │
│  Top-level collection of categories │
└─────────────────────────────────────┘
                │
                ├─> RFC3339_DATES (DateTimeTestCategory)
                │   └─> 7 test cases
                │
                ├─> RFC822_DATES (DateTimeTestCategory)
                │   └─> 7 test cases
                │
                ├─> LANGUAGE_SPECIFIC_DATES (DateTimeTestCategory)
                │   └─> 18 test cases (15 languages)
                │
                ├─> EDGE_CASE_DATES (DateTimeTestCategory)
                │   └─> 7 test cases
                │
                ├─> INVALID_DATES (DateTimeTestCategory)
                │   └─> 8 test cases
                │
                └─> REAL_WORLD_DATES (DateTimeTestCategory)
                    └─> 6 test cases


Each DateTimeTestCase contains:
  • input_string: "2025-01-13T14:30:00Z"
  • expected_datetime: datetime(2025, 1, 13, 14, 30, 0, tzinfo=UTC)
  • expected_behavior: PARSE_SUCCESS
  • format_type: RFC3339
  • description: "Basic RFC 3339 with Z suffix"
  • language: "en"
  • tags: ["basic", "utc"]
  • notes: "Additional context..."
```

## Example Test Cases

### RFC 3339 (Atom/JSON Feed)

```python
"2025-01-13T14:30:00Z"              ✅ Basic UTC
"2025-01-13T14:30:00+05:30"         ✅ Positive offset (IST)
"2025-01-13T14:30:00-05:00"         ✅ Negative offset (EST)
"2025-01-13T14:30:00.123456Z"       ✅ Microseconds
```

### RFC 822 (RSS 2.0)

```python
"Mon, 13 Jan 2025 14:30:00 GMT"     ✅ Basic GMT
"13 Jan 2025 14:30:00 +0000"        ✅ Numeric offset
"Mon, 13 Jan 2025 14:30:00 EST"     ⚠️  Timezone warning
```

### Language-Specific

```python
"Lundi 13 janvier 2025 14:30:00"    ⏭️  French
"Montag, 13. Januar 2025 14:30"     ⏭️  German
"13 de enero de 2025 14:30"         ⏭️  Spanish
"2025年1月13日 14時30分"             ⏭️  Japanese
```

### Invalid Dates

```python
""                                   ❌ Empty string
"2025-13-01T12:00:00Z"              ❌ Invalid month
"2025-02-29T12:00:00Z"              ❌ Non-leap year
"not a date"                        ❌ Garbage input
```

## Key Features

### 1. Easy Extension

```python
# Add a new language in 3 lines
from tests.feed_spider.datetime_test_data import (
    LANGUAGE_SPECIFIC_DATES,
    create_language_test_case,
    REFERENCE_DATETIME
)

norwegian = create_language_test_case(
    "no", "Norwegian",
    "Mandag 13. januar 2025 14:30",
    REFERENCE_DATETIME,
    "Norwegian weekday and month"
)
LANGUAGE_SPECIFIC_DATES.add_test(norwegian)
```

### 2. Flexible Filtering

```python
# Get all tests that should succeed
success_tests = get_test_cases_by_behavior(ExpectedBehavior.PARSE_SUCCESS)

# Get all French tests
french_tests = get_test_cases_by_language("fr")

# Get all timezone tests
tz_tests = get_test_cases_by_tags(["timezone"])

# Combine filters
category = DATETIME_TEST_SUITE["rfc822"]
est_tests = category.filter_by_tags(["est"])
```

### 3. pytest Integration

```python
@pytest.mark.parametrize(
    "test_case",
    DATETIME_TEST_SUITE["rfc3339"].test_cases,
    ids=lambda tc: tc.description
)
def test_rfc3339_dates(test_case):
    result = parse_date(test_case.input_string)
    if test_case.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
        assert result == test_case.expected_datetime
```

### 4. Comprehensive Metadata

Each test case includes:

- Input string
- Expected datetime (if should succeed)
- Expected behavior (success/fail/xfail/warn)
- Format type
- Language code
- Descriptive name
- Tags for filtering
- Optional notes

## Usage Patterns

### Testing a New Parser

```python
from tests.feed_spider.datetime_test_data import get_all_test_cases

def test_new_parser():
    for tc in get_all_test_cases():
        result = new_parser(tc.input_string)

        if tc.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
            assert result == tc.expected_datetime
        elif tc.expected_behavior == ExpectedBehavior.PARSE_FAIL:
            assert result is None
        # Handle PARSE_XFAIL and PARSE_WARN...
```

### Benchmarking

```python
import time
from tests.feed_spider.datetime_test_data import DATETIME_TEST_SUITE

for name, category in DATETIME_TEST_SUITE.items():
    start = time.perf_counter()
    for tc in category.test_cases:
        parse_date(tc.input_string)
    duration = time.perf_counter() - start
    print(f"{name}: {duration*1000:.1f}ms")
```

### Reporting Coverage

```python
from tests.feed_spider.datetime_test_data import get_summary_stats

stats = get_summary_stats()
print(f"Total: {stats['total_test_cases']} tests")
print(f"Languages: {', '.join(stats['languages_list'])}")
print(f"Success cases: {stats['by_behavior']['parse_success']}")
```

## Benefits

✅ **Comprehensive**: 53 test cases across 15+ languages
✅ **Extensible**: Easy to add new tests, languages, categories
✅ **Organized**: Clear structure with categories and tags
✅ **Flexible**: Multiple filtering options
✅ **Documented**: Rich metadata for each test
✅ **pytest-Ready**: Direct parametrization support
✅ **Maintainable**: Structured data with clear semantics
✅ **Type-Safe**: Using dataclasses and enums
✅ **Discoverable**: Helper functions for exploration
✅ **Validated**: Post-init validation ensures data integrity

## Comparison: Before vs After

### Before (Manual Test Cases)

```python
def test_rfc3339_with_z():
    result = parse("2025-01-13T14:30:00Z")
    assert result.year == 2025
    # ... repeated for each test

def test_rfc3339_with_offset():
    result = parse("2025-01-13T14:30:00+05:30")
    assert result.hour == 9
    # ... repeated for each test

# Need to manually manage each test
# Hard to add new languages
# No easy way to filter or group tests
```

### After (Structured Data)

```python
@pytest.mark.parametrize(
    "test_case",
    DATETIME_TEST_SUITE["rfc3339"].test_cases,
    ids=lambda tc: tc.description
)
def test_rfc3339_dates(test_case):
    result = parse(test_case.input_string)
    assert result == test_case.expected_datetime

# Data-driven testing
# Easy to add: just append to test_cases list
# Powerful filtering and grouping
# Rich metadata for reporting
```

## Integration Points

### With Existing Tests

The structured data can be used alongside existing tests:

```python
# Old test (still works)
def test_specific_date():
    result = parse("2025-01-13T14:30:00Z")
    assert result is not None

# New test (uses structured data)
@pytest.mark.parametrize("test_case", DATETIME_TEST_SUITE["rfc3339"].test_cases)
def test_rfc3339(test_case):
    result = parse(test_case.input_string)
    assert result == test_case.expected_datetime
```

### With Future Implementation

When implementing improved datetime parsing:

1. Run baseline tests with current implementation
2. Implement improvements
3. Update `expected_behavior` for newly supported cases
4. Re-run tests to verify improvements
5. Add new test cases for edge cases discovered

## Statistics

```text
📊 Coverage Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Categories:        6
Total Tests:       53
Languages:         15
Success Tests:     25 (47%)
Fail Tests:        8 (15%)
Expected Fail:     18 (34%)
Warning Tests:     2 (4%)

📄 By Format
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RFC 3339:          15 tests (Atom, JSON Feed)
RFC 822:           10 tests (RSS 2.0)
ISO 8601:          1 test
Custom:            1 test
Localized:         18 tests (non-English)
Invalid:           8 tests (error cases)

🌍 Language Coverage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Western European:  7 languages
Eastern European:  2 languages
Asian:             3 languages
Middle Eastern:    1 language
Other:             2 languages
```

## Next Steps

1. ✅ Review `DATETIME_TEST_DATA_GUIDE.md` for full documentation
2. ✅ Check `DATETIME_TEST_DATA_QUICKSTART.md` for quick reference
3. ✅ Examine `test_datetime_with_fixtures.py` for usage examples
4. 🔧 Implement improved datetime parser
5. 🔧 Update expected behaviors as parser improves
6. ➕ Add more languages as needed
7. ➕ Add more edge cases as discovered

## Conclusion

The datetime test data structure provides a robust, maintainable foundation for comprehensive datetime parsing tests across multiple languages and formats. It's designed to grow with the project's needs while remaining easy to use and understand.

**Files**: 4 (data, tests, guide, quickstart)
**Test Cases**: 53
**Languages**: 15
**Categories**: 6
**Extensibility**: ⭐⭐⭐⭐⭐
