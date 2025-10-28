# DateTime Test Data - Quick Start Guide

**Created:** 2025-10-20

---

## TL;DR

```python
from tests.feed_spider.datetime_test_data import DATETIME_TEST_SUITE

# Use in tests
@pytest.mark.parametrize("test_case", DATETIME_TEST_SUITE["rfc3339"].test_cases)
def test_dates(test_case):
    result = parse_date(test_case.input_string)
    if test_case.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
        assert result == test_case.expected_datetime
```

## What's Included

**53 Test Cases** across **6 Categories** covering **15 Languages**:

- ✅ **RFC 3339** (Atom/JSON Feed): 7 tests
- ✅ **RFC 822** (RSS 2.0): 7 tests
- ✅ **15 Languages**: French, German, Spanish, Italian, Portuguese, Dutch, Russian, Japanese, Chinese, Korean, Arabic, Polish, Swedish, Turkish
- ✅ **Edge Cases**: Leap years, DST, epochs
- ✅ **Invalid Dates**: Error handling tests
- ✅ **Real-World**: WordPress, Medium, FeedBurner, etc.

## Common Operations

### Get All Tests for a Category

```python
from tests.feed_spider.datetime_test_data import DATETIME_TEST_SUITE

rfc3339_tests = DATETIME_TEST_SUITE["rfc3339"].test_cases
rfc822_tests = DATETIME_TEST_SUITE["rfc822"].test_cases
language_tests = DATETIME_TEST_SUITE["language_specific"].test_cases
```

### Filter by Criteria

```python
from tests.feed_spider.datetime_test_data import (
    get_test_cases_by_behavior,
    get_test_cases_by_language,
    get_test_cases_by_tags,
    ExpectedBehavior
)

# All cases that should parse successfully
success = get_test_cases_by_behavior(ExpectedBehavior.PARSE_SUCCESS)

# All French test cases
french = get_test_cases_by_language("fr")

# All timezone-related tests
timezones = get_test_cases_by_tags(["timezone"])
```

### Add New Test Case

```python
from datetime import datetime, timezone
from tests.feed_spider.datetime_test_data import (
    DateTimeTestCase,
    DateTimeFormat,
    ExpectedBehavior,
    RFC3339_DATES
)

new_test = DateTimeTestCase(
    input_string="2025-12-25T00:00:00Z",
    expected_datetime=datetime(2025, 12, 25, 0, 0, 0, tzinfo=timezone.utc),
    expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
    format_type=DateTimeFormat.RFC3339,
    description="Christmas 2025",
    tags=["holiday", "midnight"]
)

RFC3339_DATES.add_test(new_test)
```

### Add New Language

```python
from tests.feed_spider.datetime_test_data import (
    LANGUAGE_SPECIFIC_DATES,
    create_language_test_case,
    REFERENCE_DATETIME  # 2025-01-13 14:30:00 UTC
)

# Add Norwegian
norwegian = create_language_test_case(
    "no", "Norwegian",
    "Mandag 13. januar 2025 14:30",
    REFERENCE_DATETIME,
    "Norwegian weekday and month"
)

LANGUAGE_SPECIFIC_DATES.add_test(norwegian)
```

## File Structure

```
tests/feed_spider/
├── datetime_test_data.py          # Core data structure (53 tests)
├── test_datetime_with_fixtures.py # Example usage in tests
└── test_datetime_parsing.py       # Original comprehensive tests

docs/
├── DATETIME_TEST_DATA_GUIDE.md    # Full documentation
└── DATETIME_TEST_DATA_QUICKSTART.md  # This file
```

## Test Coverage Summary

| Category | Tests | Status |
|----------|-------|--------|
| RFC 3339 | 7 | ✅ All pass |
| RFC 822 | 7 | ✅ All pass (2 warnings) |
| Languages | 18 | ⏭️ Expected to fail |
| Edge Cases | 7 | ✅ All pass |
| Invalid | 8 | ❌ Currently raise exceptions |
| Real-World | 6 | ✅ All pass |

## Expected Behaviors

```python
class ExpectedBehavior(Enum):
    PARSE_SUCCESS = "parse_success"  # Should parse correctly
    PARSE_FAIL = "parse_fail"        # Should return None
    PARSE_XFAIL = "parse_xfail"      # Expected to fail (not yet supported)
    PARSE_WARN = "parse_warn"        # Parses but may warn
```

## Using in Tests

### Basic Parametrization

```python
import pytest
from tests.feed_spider.datetime_test_data import DATETIME_TEST_SUITE

@pytest.mark.parametrize(
    "test_case",
    DATETIME_TEST_SUITE["rfc3339"].test_cases,
    ids=lambda tc: tc.description
)
def test_rfc3339(test_case):
    result = my_parser(test_case.input_string)
    assert result == test_case.expected_datetime
```

### Handle Different Behaviors

```python
from tests.feed_spider.datetime_test_data import ExpectedBehavior

def test_all_cases(test_case):
    result = my_parser(test_case.input_string)

    if test_case.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
        assert result == test_case.expected_datetime
    elif test_case.expected_behavior == ExpectedBehavior.PARSE_FAIL:
        assert result is None
    elif test_case.expected_behavior == ExpectedBehavior.PARSE_XFAIL:
        pytest.xfail(test_case.notes)
```

### Test Only Specific Languages

```python
@pytest.mark.parametrize("language", ["en", "fr", "de"])
def test_language(language):
    cases = get_test_cases_by_language(language)
    for tc in cases:
        # Test logic...
```

## Quick Stats

```python
from tests.feed_spider.datetime_test_data import get_summary_stats

stats = get_summary_stats()
print(f"Total tests: {stats['total_test_cases']}")
print(f"Languages: {stats['languages']}")
print(f"Success cases: {stats['by_behavior']['parse_success']}")
```

## Adding Bulk Data

### From CSV File

```python
import csv
from tests.feed_spider.datetime_test_data import (
    DateTimeTestCase,
    DateTimeFormat,
    ExpectedBehavior
)

with open('dates.csv') as f:
    for row in csv.DictReader(f):
        test = DateTimeTestCase(
            input_string=row['date'],
            expected_datetime=datetime.fromisoformat(row['expected']),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.CUSTOM,
            description=row['description'],
            language=row['lang']
        )
        category.add_test(test)
```

### From Dictionary

```python
test_data = [
    {
        "input": "2025-01-13T14:30:00Z",
        "expected": datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc),
        "description": "Basic ISO 8601"
    },
    # More entries...
]

for data in test_data:
    test = DateTimeTestCase(
        input_string=data["input"],
        expected_datetime=data["expected"],
        expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
        format_type=DateTimeFormat.ISO8601,
        description=data["description"]
    )
    category.add_test(test)
```

## Common Patterns

### Test All Success Cases

```python
from tests.feed_spider.datetime_test_data import get_test_cases_by_behavior

success_cases = get_test_cases_by_behavior(ExpectedBehavior.PARSE_SUCCESS)
for tc in success_cases:
    result = parse_date(tc.input_string)
    assert result == tc.expected_datetime, f"Failed: {tc.description}"
```

### Test Language Coverage

```python
from tests.feed_spider.datetime_test_data import get_languages

for language in get_languages():
    cases = get_test_cases_by_language(language)
    print(f"{language}: {len(cases)} test cases")
```

### Benchmark Performance

```python
import time
from tests.feed_spider.datetime_test_data import DATETIME_TEST_SUITE

for name, category in DATETIME_TEST_SUITE.items():
    start = time.perf_counter()
    for tc in category.test_cases:
        parse_date(tc.input_string)
    duration = time.perf_counter() - start
    print(f"{name}: {duration:.3f}s for {len(category.test_cases)} tests")
```

## Next Steps

1. **Read Full Guide**: See `DATETIME_TEST_DATA_GUIDE.md` for complete documentation
2. **View Examples**: Check `test_datetime_with_fixtures.py` for usage patterns
3. **Add Data**: Contribute new languages or edge cases
4. **Run Tests**: Use in your datetime parser tests

## Support

The test data is designed to be:
- ✅ Easy to extend
- ✅ Well-documented
- ✅ Flexible for filtering
- ✅ Compatible with pytest
- ✅ Comprehensive (50+ tests, 15+ languages)

Happy testing! 🚀
