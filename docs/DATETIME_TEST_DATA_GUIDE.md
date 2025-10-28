# DateTime Test Data Guide

**Created:** 2025-10-20
**Updated:** 2025-10-20

---

## Overview

The datetime test data structure (`tests/feed_spider/datetime_test_data.py`) provides a comprehensive, extensible framework for testing datetime parsing across multiple languages, formats, and edge cases.

## Architecture

### Core Components

```
DateTimeTestCase       - Single test case (input → expected output)
    ↓
DateTimeTestCategory   - Group of related test cases
    ↓
DATETIME_TEST_SUITE    - Complete collection of all categories
```

### Data Classes

#### `DateTimeTestCase`

Represents a single datetime parsing test.

```python
@dataclass
class DateTimeTestCase:
    input_string: str                      # Date string to parse
    expected_behavior: ExpectedBehavior    # How parser should behave
    format_type: DateTimeFormat            # Format category
    description: str                       # Human-readable description
    expected_datetime: Optional[datetime]  # Expected result (if success)
    language: str = "en"                   # ISO 639-1 language code
    tags: List[str] = []                   # Categorization tags
    notes: str = ""                        # Additional notes
    skip_reason: str = ""                  # Why to skip (if applicable)
```

#### `DateTimeTestCategory`

Groups related test cases together.

```python
@dataclass
class DateTimeTestCategory:
    name: str                              # Category name
    description: str                       # Category description
    test_cases: List[DateTimeTestCase]     # All test cases
    tags: List[str] = []                   # Category-wide tags
```

### Enums

#### `ExpectedBehavior`

Defines expected parsing outcomes:

- `PARSE_SUCCESS` - Should parse successfully
- `PARSE_FAIL` - Should return None (invalid input)
- `PARSE_XFAIL` - Expected to fail with current implementation
- `PARSE_WARN` - Parses but may produce warnings

#### `DateTimeFormat`

Categorizes date formats:

- `RFC3339` - Atom, JSON Feed (ISO 8601 profile)
- `RFC822` - RSS 2.0 (RFC 2822)
- `ISO8601` - General ISO 8601
- `CUSTOM` - Non-standard formats
- `LOCALIZED` - Language-specific formats
- `INVALID` - Invalid/malformed dates

## Current Test Coverage

### Categories (6 total)

1. **RFC 3339 Dates** - 7 test cases
   - Atom and JSON Feed formats
   - Timezones, microseconds, offsets

2. **RFC 822 Dates** - 7 test cases
   - RSS 2.0 standard formats
   - Timezone abbreviations, numeric offsets

3. **Language-Specific Dates** - 15+ test cases
   - French, German, Spanish, Italian, Portuguese
   - Dutch, Russian, Japanese, Chinese, Korean
   - Arabic, Polish, Swedish, Turkish

4. **Edge Cases** - 7 test cases
   - Leap years, DST transitions
   - Boundary dates (epoch, far future)

5. **Invalid Dates** - 8 test cases
   - Empty strings, malformed dates
   - Out-of-range values

6. **Real-World Examples** - 6 test cases
   - WordPress, FeedBurner, Medium
   - Atom, JSON Feed, Podcast formats

### Statistics

```python
from tests.feed_spider.datetime_test_data import get_summary_stats
stats = get_summary_stats()
# {
#   "total_test_cases": 50+,
#   "categories": 6,
#   "languages": 15+,
#   "by_behavior": {...},
#   "by_format": {...}
# }
```

## Usage Examples

### Basic Usage in Tests

```python
import pytest
from tests.feed_spider.datetime_test_data import DATETIME_TEST_SUITE

@pytest.mark.parametrize(
    "test_case",
    DATETIME_TEST_SUITE["rfc3339"].test_cases,
    ids=lambda tc: tc.description
)
def test_rfc3339_parsing(test_case):
    result = parse_date(test_case.input_string)

    if test_case.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
        assert result == test_case.expected_datetime
    elif test_case.expected_behavior == ExpectedBehavior.PARSE_FAIL:
        assert result is None
```

### Filtering Test Cases

```python
from tests.feed_spider.datetime_test_data import (
    get_test_cases_by_behavior,
    get_test_cases_by_language,
    get_test_cases_by_tags,
    ExpectedBehavior
)

# Get all cases that should succeed
success_cases = get_test_cases_by_behavior(ExpectedBehavior.PARSE_SUCCESS)

# Get all French test cases
french_cases = get_test_cases_by_language("fr")

# Get all timezone-related cases
tz_cases = get_test_cases_by_tags(["timezone"])

# Get cases with multiple tags
dst_tz_cases = get_test_cases_by_tags(["dst", "timezone"])
```

### Using Category Methods

```python
category = DATETIME_TEST_SUITE["language_specific"]

# Filter within category
french_tests = category.filter_by_language("fr")
xfail_tests = category.filter_by_behavior(ExpectedBehavior.PARSE_XFAIL)
localized_tests = category.filter_by_tags(["localized"])
```

## Adding New Test Data

### Adding a New Language

```python
from tests.feed_spider.datetime_test_data import (
    LANGUAGE_SPECIFIC_DATES,
    create_language_test_case,
    REFERENCE_DATETIME
)

# Add Finnish date format
finnish_test = create_language_test_case(
    "fi", "Finnish",
    "Maanantai 13. tammikuuta 2025 klo 14:30",
    REFERENCE_DATETIME,
    "Finnish format with 'klo' time prefix",
    notes="Uses ordinal day and 'klo' for time"
)

LANGUAGE_SPECIFIC_DATES.add_test(finnish_test)
```

### Adding a New Test Case

```python
from datetime import datetime, timezone
from tests.feed_spider.datetime_test_data import (
    DateTimeTestCase,
    DateTimeFormat,
    ExpectedBehavior,
    RFC3339_DATES
)

# Create new test case
new_test = DateTimeTestCase(
    input_string="2025-01-13T14:30:00+12:00",
    expected_datetime=datetime(2025, 1, 13, 2, 30, 0, tzinfo=timezone.utc),
    expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
    format_type=DateTimeFormat.RFC3339,
    description="RFC 3339 with New Zealand timezone (+12:00)",
    language="en",
    tags=["timezone", "offset", "nz", "extreme-tz"],
    notes="Tests positive extreme timezone offset"
)

# Add to appropriate category
RFC3339_DATES.add_test(new_test)
```

### Creating a New Category

```python
from tests.feed_spider.datetime_test_data import (
    DateTimeTestCategory,
    DateTimeTestCase,
    DATETIME_TEST_SUITE
)

# Create category for Unix timestamps
UNIX_TIMESTAMPS = DateTimeTestCategory(
    name="Unix Timestamps",
    description="Numeric Unix timestamps and variations",
    tags=["unix", "timestamp", "numeric"],
    test_cases=[
        DateTimeTestCase(
            input_string="1610546400",
            expected_datetime=datetime(2021, 1, 13, 14, 0, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.CUSTOM,
            description="Unix timestamp (seconds since epoch)",
            tags=["unix", "epoch", "numeric"]
        ),
        # Add more test cases...
    ]
)

# Add to test suite
DATETIME_TEST_SUITE["unix_timestamps"] = UNIX_TIMESTAMPS
```

### Adding Multiple Language Variants

```python
# Helper for adding multiple date strings for same datetime
def add_language_variants(category, base_datetime, variants):
    """Add multiple language variants for the same datetime.

    Args:
        category: DateTimeTestCategory to add to
        base_datetime: Expected datetime for all variants
        variants: List of (language, language_name, date_string, description) tuples
    """
    for lang, lang_name, date_str, desc in variants:
        test = create_language_test_case(
            lang, lang_name, date_str, base_datetime, desc
        )
        category.add_test(test)

# Example usage
variants = [
    ("fr", "French", "13 janvier 2025", "French date"),
    ("de", "German", "13. Januar 2025", "German date"),
    ("es", "Spanish", "13 de enero de 2025", "Spanish date"),
]

add_language_variants(
    LANGUAGE_SPECIFIC_DATES,
    datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc),
    variants
)
```

## Best Practices

### Test Case Design

1. **Clear Descriptions** - Make descriptions unique and descriptive
   ```python
   # Good
   description="RFC 3339 with New Zealand timezone (+12:00)"

   # Bad
   description="Test 1"
   ```

2. **Appropriate Tags** - Use tags for filtering and organization
   ```python
   tags=["timezone", "offset", "extreme-tz", "nz"]
   ```

3. **Complete Metadata** - Fill in all relevant fields
   ```python
   notes="Tests positive extreme timezone offset"
   language="en"
   ```

4. **Expected Behavior** - Set correct expectation
   ```python
   # For current implementation limitations
   expected_behavior=ExpectedBehavior.PARSE_XFAIL

   # For truly invalid dates
   expected_behavior=ExpectedBehavior.PARSE_FAIL
   ```

### Category Organization

1. **Logical Grouping** - Group related test cases
   - By format (RFC 3339, RFC 822)
   - By language (English, French, etc.)
   - By scenario (edge cases, invalid)

2. **Comprehensive Tags** - Add category-level tags
   ```python
   tags=["rfc3339", "iso8601", "standard"]
   ```

3. **Clear Documentation** - Describe what the category tests
   ```python
   description="RFC 3339 format dates used in Atom and JSON Feed"
   ```

### Extending for New Parsers

When implementing a new datetime parser, use the test suite to:

1. **Establish Baseline** - Run all tests to see current support
   ```python
   success_cases = get_test_cases_by_behavior(ExpectedBehavior.PARSE_SUCCESS)
   baseline_passes = sum(1 for tc in success_cases if parser(tc.input_string))
   ```

2. **Update Expected Behaviors** - As parser improves
   ```python
   # If French support is added
   for tc in get_test_cases_by_language("fr"):
       if tc.expected_behavior == ExpectedBehavior.PARSE_XFAIL:
           tc.expected_behavior = ExpectedBehavior.PARSE_SUCCESS
   ```

3. **Add New Test Cases** - For newly supported features
   ```python
   # Parser now supports Hebrew
   hebrew_tests = create_hebrew_test_cases()
   for test in hebrew_tests:
       LANGUAGE_SPECIFIC_DATES.add_test(test)
   ```

## Integration with pytest

### Parametrized Tests

```python
@pytest.mark.parametrize(
    "test_case",
    DATETIME_TEST_SUITE["rfc3339"].test_cases,
    ids=lambda tc: tc.description
)
def test_dates(test_case):
    result = parse_date(test_case.input_string)

    if test_case.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
        assert result == test_case.expected_datetime
    elif test_case.expected_behavior == ExpectedBehavior.PARSE_FAIL:
        assert result is None
    elif test_case.expected_behavior == ExpectedBehavior.PARSE_XFAIL:
        pytest.xfail(test_case.notes)
```

### Conditional Skipping

```python
@pytest.mark.parametrize("test_case", get_all_test_cases())
def test_comprehensive(test_case):
    if test_case.skip_reason:
        pytest.skip(test_case.skip_reason)

    # Test logic...
```

### Custom Fixtures

```python
@pytest.fixture
def success_test_cases():
    """Fixture providing only success cases."""
    return get_test_cases_by_behavior(ExpectedBehavior.PARSE_SUCCESS)

def test_with_fixture(success_test_cases):
    for tc in success_test_cases:
        result = parse_date(tc.input_string)
        assert result is not None
```

## Maintenance

### Updating Expected Behaviors

When parser improves, update test expectations:

```python
# Find all French tests currently marked as xfail
french_xfails = [
    tc for tc in get_test_cases_by_language("fr")
    if tc.expected_behavior == ExpectedBehavior.PARSE_XFAIL
]

# Update to expect success
for tc in french_xfails:
    tc.expected_behavior = ExpectedBehavior.PARSE_SUCCESS
```

### Adding Bulk Test Data

```python
# Generate test cases from data file
import csv

with open('date_samples.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        test = DateTimeTestCase(
            input_string=row['date_string'],
            expected_datetime=datetime.fromisoformat(row['expected']),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.CUSTOM,
            description=row['description'],
            language=row['language'],
            tags=row['tags'].split(',')
        )
        category.add_test(test)
```

### Validating Test Data

```python
def validate_test_suite():
    """Validate test suite integrity."""
    all_cases = get_all_test_cases()

    # Check for duplicates
    descriptions = [tc.description for tc in all_cases]
    assert len(descriptions) == len(set(descriptions)), "Duplicate descriptions"

    # Check for missing expected_datetime
    for tc in all_cases:
        if tc.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
            assert tc.expected_datetime is not None, \
                f"Missing expected_datetime: {tc.description}"

    # Check all languages are valid ISO codes
    valid_langs = {'en', 'fr', 'de', 'es', 'it', ...}  # Add all
    for tc in all_cases:
        assert tc.language in valid_langs, \
            f"Invalid language code: {tc.language}"
```

## Examples by Use Case

### Testing a New Parser

```python
from tests.feed_spider.datetime_test_data import get_all_test_cases

def test_new_parser():
    all_cases = get_all_test_cases()
    results = {
        'passed': 0,
        'failed': 0,
        'xfail': 0,
        'unexpected': 0
    }

    for tc in all_cases:
        result = my_new_parser(tc.input_string)

        if tc.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
            if result == tc.expected_datetime:
                results['passed'] += 1
            else:
                results['failed'] += 1
        elif tc.expected_behavior == ExpectedBehavior.PARSE_XFAIL:
            results['xfail'] += 1
        elif tc.expected_behavior == ExpectedBehavior.PARSE_FAIL:
            if result is None:
                results['passed'] += 1
            else:
                results['unexpected'] += 1

    print(f"Results: {results}")
```

### Benchmarking Parsers

```python
import time

def benchmark_parser(parser_func, category_name):
    """Benchmark parser on a specific category."""
    category = DATETIME_TEST_SUITE[category_name]

    start = time.perf_counter()
    for tc in category.test_cases:
        parser_func(tc.input_string)
    duration = time.perf_counter() - start

    per_case = duration / len(category.test_cases) * 1000
    print(f"{category_name}: {duration:.3f}s total, {per_case:.3f}ms per case")

# Compare multiple parsers
benchmark_parser(dateutil_parser, "rfc3339")
benchmark_parser(custom_parser, "rfc3339")
```

### Generating Test Reports

```python
from tests.feed_spider.datetime_test_data import (
    DATETIME_TEST_SUITE,
    ExpectedBehavior
)

def generate_coverage_report():
    """Generate test coverage report."""
    report = []

    for name, category in DATETIME_TEST_SUITE.items():
        total = len(category.test_cases)
        success = len(category.filter_by_behavior(ExpectedBehavior.PARSE_SUCCESS))
        xfail = len(category.filter_by_behavior(ExpectedBehavior.PARSE_XFAIL))
        fail = len(category.filter_by_behavior(ExpectedBehavior.PARSE_FAIL))

        report.append({
            'category': name,
            'total': total,
            'should_pass': success,
            'expected_fail': xfail,
            'should_reject': fail,
        })

    return report
```

## Summary

The datetime test data structure provides:

✅ **Comprehensive Coverage** - 50+ test cases across 15+ languages
✅ **Easy Extension** - Simple APIs for adding new tests
✅ **Flexible Filtering** - By behavior, language, tags
✅ **pytest Integration** - Direct parametrization support
✅ **Maintainable** - Structured data with clear organization
✅ **Documented** - Clear metadata and descriptions

Use this framework to ensure robust datetime parsing across all feed formats and languages!
