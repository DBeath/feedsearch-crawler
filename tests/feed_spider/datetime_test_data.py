"""Comprehensive test data for datetime parsing across languages and formats.

This module provides a structured, extensible data format for testing datetime
parsing with multiple languages, formats, and edge cases.

Architecture:
- DateTimeTestCase: Single test case with input string and expected output
- DateTimeTestCategory: Group of related test cases (e.g., all RFC 3339 tests)
- DATETIME_TEST_SUITE: Complete test suite with all categories

Adding New Data:
1. For new languages: Add to LANGUAGE_SPECIFIC_DATES
2. For new formats: Add to appropriate category (RFC3339_DATES, RFC822_DATES, etc.)
3. For new edge cases: Add to EDGE_CASE_DATES or INVALID_DATES
4. For new categories: Create new category and add to DATETIME_TEST_SUITE
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, List, Any


class DateTimeFormat(Enum):
    """Standard datetime formats used in feeds."""

    RFC3339 = "rfc3339"  # Atom, JSON Feed (ISO 8601 profile)
    RFC822 = "rfc822"  # RSS 2.0 (RFC 2822)
    ISO8601 = "iso8601"  # General ISO 8601
    CUSTOM = "custom"  # Non-standard formats
    LOCALIZED = "localized"  # Language-specific formats
    INVALID = "invalid"  # Invalid/malformed dates


class ExpectedBehavior(Enum):
    """Expected behavior when parsing."""

    PARSE_SUCCESS = "parse_success"  # Should parse successfully
    PARSE_FAIL = "parse_fail"  # Should return None
    PARSE_XFAIL = "parse_xfail"  # Expected to fail with current implementation
    PARSE_WARN = "parse_warn"  # Parses but with warnings


@dataclass
class DateTimeTestCase:
    """Single datetime parsing test case.

    Attributes:
        input_string: The date string to parse
        expected_datetime: Expected parsed datetime (if successful)
        expected_behavior: How the parser should behave
        format_type: The format category this test belongs to
        description: Human-readable description
        language: ISO 639-1 language code (e.g., 'en', 'fr', 'de')
        tags: Additional categorization tags
        notes: Additional notes about this test case
        skip_reason: Reason to skip this test (if applicable)
    """

    input_string: str
    expected_behavior: ExpectedBehavior
    format_type: DateTimeFormat
    description: str
    expected_datetime: Optional[datetime] = None
    language: str = "en"
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    skip_reason: str = ""

    def __post_init__(self):
        """Validate test case after initialization."""
        if self.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
            if self.expected_datetime is None:
                raise ValueError(
                    f"expected_datetime required for PARSE_SUCCESS: {self.description}"
                )


@dataclass
class DateTimeTestCategory:
    """Category of related datetime test cases.

    Attributes:
        name: Category name
        description: Category description
        test_cases: List of test cases in this category
        tags: Tags for the entire category
    """

    name: str
    description: str
    test_cases: List[DateTimeTestCase] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def add_test(self, test_case: DateTimeTestCase) -> None:
        """Add a test case to this category."""
        self.test_cases.append(test_case)

    def filter_by_behavior(self, behavior: ExpectedBehavior) -> List[DateTimeTestCase]:
        """Filter test cases by expected behavior."""
        return [tc for tc in self.test_cases if tc.expected_behavior == behavior]

    def filter_by_language(self, language: str) -> List[DateTimeTestCase]:
        """Filter test cases by language."""
        return [tc for tc in self.test_cases if tc.language == language]

    def filter_by_tags(self, tags: List[str]) -> List[DateTimeTestCase]:
        """Filter test cases that have all specified tags."""
        return [tc for tc in self.test_cases if all(tag in tc.tags for tag in tags)]


# =============================================================================
# RFC 3339 Dates (Atom, JSON Feed)
# =============================================================================

RFC3339_DATES = DateTimeTestCategory(
    name="RFC 3339 Dates",
    description="RFC 3339 format dates used in Atom and JSON Feed",
    tags=["rfc3339", "iso8601", "atom", "json-feed", "standard"],
    test_cases=[
        DateTimeTestCase(
            input_string="2025-01-13T14:30:00Z",
            expected_datetime=datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="Basic RFC 3339 with Z suffix",
            tags=["basic", "utc"],
        ),
        DateTimeTestCase(
            input_string="2025-01-13T14:30:00+00:00",
            expected_datetime=datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="RFC 3339 with +00:00 offset",
            tags=["utc", "offset"],
        ),
        DateTimeTestCase(
            input_string="2025-01-13T14:30:00+05:30",
            expected_datetime=datetime(2025, 1, 13, 9, 0, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="RFC 3339 with positive offset (IST)",
            tags=["timezone", "offset", "india"],
        ),
        DateTimeTestCase(
            input_string="2025-01-13T14:30:00-05:00",
            expected_datetime=datetime(2025, 1, 13, 19, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="RFC 3339 with negative offset (EST)",
            tags=["timezone", "offset", "est"],
        ),
        DateTimeTestCase(
            input_string="2025-01-13T14:30:00.123456Z",
            expected_datetime=datetime(
                2025, 1, 13, 14, 30, 0, 123456, tzinfo=timezone.utc
            ),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="RFC 3339 with microseconds",
            tags=["microseconds", "precision"],
        ),
        DateTimeTestCase(
            input_string="2025-01-13T14:30:00.123Z",
            expected_datetime=datetime(
                2025, 1, 13, 14, 30, 0, 123000, tzinfo=timezone.utc
            ),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="RFC 3339 with milliseconds",
            tags=["milliseconds", "precision"],
        ),
        DateTimeTestCase(
            input_string="20250113T143000Z",
            expected_datetime=datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.ISO8601,
            description="Compact ISO 8601 format",
            tags=["compact", "iso8601"],
        ),
    ],
)


# =============================================================================
# RFC 822 Dates (RSS 2.0)
# =============================================================================

RFC822_DATES = DateTimeTestCategory(
    name="RFC 822 Dates",
    description="RFC 822/2822 format dates used in RSS 2.0",
    tags=["rfc822", "rfc2822", "rss", "standard"],
    test_cases=[
        DateTimeTestCase(
            input_string="Mon, 13 Jan 2025 14:30:00 GMT",
            expected_datetime=datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC822,
            description="Basic RFC 822 with GMT",
            tags=["basic", "gmt"],
        ),
        DateTimeTestCase(
            input_string="Mon, 13 Jan 2025 14:30:00 +0000",
            expected_datetime=datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC822,
            description="RFC 822 with numeric offset",
            tags=["offset", "numeric"],
        ),
        DateTimeTestCase(
            input_string="Mon, 13 Jan 2025 14:30:00 -0500",
            expected_datetime=datetime(2025, 1, 13, 19, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC822,
            description="RFC 822 with negative offset",
            tags=["offset", "negative"],
        ),
        DateTimeTestCase(
            input_string="13 Jan 2025 14:30:00 GMT",
            expected_datetime=datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC822,
            description="RFC 822 without day name",
            tags=["no-day-name"],
        ),
        DateTimeTestCase(
            input_string="13 Jan 25 14:30:00 GMT",
            expected_datetime=datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC822,
            description="RFC 822 with two-digit year",
            tags=["two-digit-year"],
        ),
        DateTimeTestCase(
            input_string="Mon, 13 Jan 2025 14:30:00 EST",
            expected_datetime=datetime(2025, 1, 13, 19, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_WARN,
            format_type=DateTimeFormat.RFC822,
            description="RFC 822 with EST (may warn about unknown timezone)",
            tags=["timezone", "est", "warning"],
            notes="May produce UnknownTimezoneWarning",
        ),
        DateTimeTestCase(
            input_string="Mon, 13 January 2025 14:30:00 GMT",
            expected_datetime=datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC822,
            description="RFC 822 with full month name",
            tags=["full-month-name"],
        ),
    ],
)


# =============================================================================
# Language-Specific Dates
# =============================================================================


def create_language_test_case(
    language: str,
    language_name: str,
    date_string: str,
    reference_date: datetime,
    format_description: str,
    notes: str = "",
) -> DateTimeTestCase:
    """Helper to create language-specific test cases."""
    return DateTimeTestCase(
        input_string=date_string,
        expected_datetime=reference_date,
        expected_behavior=ExpectedBehavior.PARSE_XFAIL,
        format_type=DateTimeFormat.LOCALIZED,
        description=f"{language_name} date format: {format_description}",
        language=language,
        tags=["localized", "non-english", language],
        notes=notes or f"Current implementation does not support {language_name} dates",
    )


# Reference datetime for all language tests
REFERENCE_DATETIME = datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc)

LANGUAGE_SPECIFIC_DATES = DateTimeTestCategory(
    name="Language-Specific Dates",
    description="Dates with localized month/day names in various languages",
    tags=["localized", "non-english", "i18n", "l10n"],
    test_cases=[
        # French
        create_language_test_case(
            "fr",
            "French",
            "Lundi 13 janvier 2025 14:30:00",
            REFERENCE_DATETIME,
            "Weekday + day + month + year + time",
        ),
        create_language_test_case(
            "fr",
            "French",
            "13 janvier 2025 à 14h30",
            REFERENCE_DATETIME,
            "French time format with 'à' and 'h'",
        ),
        # German
        create_language_test_case(
            "de",
            "German",
            "Montag, 13. Januar 2025 14:30 Uhr",
            REFERENCE_DATETIME,
            "German format with 'Uhr' suffix",
        ),
        create_language_test_case(
            "de",
            "German",
            "13. Januar 2025",
            datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc),
            "German date-only format",
        ),
        # Spanish
        create_language_test_case(
            "es",
            "Spanish",
            "Lunes, 13 de enero de 2025 14:30",
            REFERENCE_DATETIME,
            "Spanish format with 'de' prepositions",
        ),
        create_language_test_case(
            "es",
            "Spanish",
            "13 enero 2025",
            datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc),
            "Shortened Spanish format",
        ),
        # Italian
        create_language_test_case(
            "it",
            "Italian",
            "Lunedì 13 gennaio 2025 14:30",
            REFERENCE_DATETIME,
            "Italian weekday and month",
        ),
        create_language_test_case(
            "it",
            "Italian",
            "13 gen 2025",
            datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc),
            "Italian abbreviated month",
        ),
        # Portuguese
        create_language_test_case(
            "pt",
            "Portuguese",
            "Segunda-feira, 13 de janeiro de 2025 14:30",
            REFERENCE_DATETIME,
            "Portuguese with compound weekday",
        ),
        # Dutch
        create_language_test_case(
            "nl",
            "Dutch",
            "Maandag 13 januari 2025 14:30",
            REFERENCE_DATETIME,
            "Dutch weekday and month",
        ),
        # Russian
        create_language_test_case(
            "ru",
            "Russian",
            "13 января 2025 14:30",
            REFERENCE_DATETIME,
            "Russian Cyrillic month name",
            notes="Uses Cyrillic characters",
        ),
        # Japanese
        create_language_test_case(
            "ja",
            "Japanese",
            "2025年1月13日 14時30分",
            REFERENCE_DATETIME,
            "Japanese with kanji date markers",
            notes="Year年 Month月 Day日 Hour時 Minute分",
        ),
        # Chinese (Simplified)
        create_language_test_case(
            "zh",
            "Chinese",
            "2025年1月13日 14:30",
            REFERENCE_DATETIME,
            "Chinese simplified format",
            notes="Uses Chinese characters for date units",
        ),
        # Korean
        create_language_test_case(
            "ko",
            "Korean",
            "2025년 1월 13일 14:30",
            REFERENCE_DATETIME,
            "Korean with Hangul date markers",
            notes="Year년 Month월 Day일",
        ),
        # Arabic
        create_language_test_case(
            "ar",
            "Arabic",
            "٢٠٢٥/٠١/١٣ ١٤:٣٠",
            REFERENCE_DATETIME,
            "Arabic with Eastern Arabic numerals",
            notes="Uses Eastern Arabic numerals (٠-٩)",
        ),
        # Polish
        create_language_test_case(
            "pl",
            "Polish",
            "13 stycznia 2025 14:30",
            REFERENCE_DATETIME,
            "Polish month name (genitive case)",
        ),
        # Swedish
        create_language_test_case(
            "sv",
            "Swedish",
            "Måndag 13 januari 2025 14:30",
            REFERENCE_DATETIME,
            "Swedish weekday and month",
        ),
        # Turkish
        create_language_test_case(
            "tr",
            "Turkish",
            "13 Ocak 2025 14:30",
            REFERENCE_DATETIME,
            "Turkish month name",
        ),
    ],
)


# =============================================================================
# Edge Cases
# =============================================================================

EDGE_CASE_DATES = DateTimeTestCategory(
    name="Edge Cases",
    description="Edge cases and boundary conditions",
    tags=["edge-case", "boundary"],
    test_cases=[
        DateTimeTestCase(
            input_string="2024-02-29T12:00:00Z",
            expected_datetime=datetime(2024, 2, 29, 12, 0, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="Leap year February 29th",
            tags=["leap-year"],
        ),
        DateTimeTestCase(
            input_string="2025-12-31T23:59:59Z",
            expected_datetime=datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="End of year",
            tags=["boundary", "year-end"],
        ),
        DateTimeTestCase(
            input_string="2025-01-01T00:00:00Z",
            expected_datetime=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="Start of year",
            tags=["boundary", "year-start"],
        ),
        DateTimeTestCase(
            input_string="1970-01-01T00:00:00Z",
            expected_datetime=datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="Unix epoch",
            tags=["epoch", "historic"],
        ),
        DateTimeTestCase(
            input_string="2099-12-31T23:59:59Z",
            expected_datetime=datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="Far future date",
            tags=["future"],
        ),
        DateTimeTestCase(
            input_string="2025-03-09T02:30:00-05:00",
            expected_datetime=datetime(2025, 3, 9, 7, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="DST transition (spring forward)",
            tags=["dst", "timezone"],
        ),
        DateTimeTestCase(
            input_string="2025-11-02T01:30:00-04:00",
            expected_datetime=datetime(2025, 11, 2, 5, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="DST transition (fall back)",
            tags=["dst", "timezone"],
        ),
    ],
)


# =============================================================================
# Invalid Dates
# =============================================================================

INVALID_DATES = DateTimeTestCategory(
    name="Invalid Dates",
    description="Invalid, malformed, or unparseable dates",
    tags=["invalid", "error-handling"],
    test_cases=[
        DateTimeTestCase(
            input_string="",
            expected_behavior=ExpectedBehavior.PARSE_FAIL,
            format_type=DateTimeFormat.INVALID,
            description="Empty string",
            tags=["empty"],
        ),
        DateTimeTestCase(
            input_string="   ",
            expected_behavior=ExpectedBehavior.PARSE_FAIL,
            format_type=DateTimeFormat.INVALID,
            description="Whitespace only",
            tags=["whitespace"],
        ),
        DateTimeTestCase(
            input_string="not a date at all",
            expected_behavior=ExpectedBehavior.PARSE_FAIL,
            format_type=DateTimeFormat.INVALID,
            description="Completely invalid string",
            tags=["garbage"],
        ),
        DateTimeTestCase(
            input_string="2025-13-01T12:00:00Z",
            expected_behavior=ExpectedBehavior.PARSE_FAIL,
            format_type=DateTimeFormat.INVALID,
            description="Invalid month (13)",
            tags=["out-of-range", "month"],
        ),
        DateTimeTestCase(
            input_string="2025-01-32T12:00:00Z",
            expected_behavior=ExpectedBehavior.PARSE_FAIL,
            format_type=DateTimeFormat.INVALID,
            description="Invalid day (32)",
            tags=["out-of-range", "day"],
        ),
        DateTimeTestCase(
            input_string="2025-02-29T12:00:00Z",
            expected_behavior=ExpectedBehavior.PARSE_FAIL,
            format_type=DateTimeFormat.INVALID,
            description="Feb 29 in non-leap year",
            tags=["leap-year", "invalid"],
        ),
        DateTimeTestCase(
            input_string="2025-01-13T25:00:00Z",
            expected_behavior=ExpectedBehavior.PARSE_FAIL,
            format_type=DateTimeFormat.INVALID,
            description="Invalid hour (25)",
            tags=["out-of-range", "hour"],
        ),
        DateTimeTestCase(
            input_string="2025-01-13T12:60:00Z",
            expected_behavior=ExpectedBehavior.PARSE_FAIL,
            format_type=DateTimeFormat.INVALID,
            description="Invalid minute (60)",
            tags=["out-of-range", "minute"],
        ),
    ],
)


# =============================================================================
# Real-World Feed Examples
# =============================================================================

REAL_WORLD_DATES = DateTimeTestCategory(
    name="Real-World Feed Examples",
    description="Actual date formats found in real RSS/Atom/JSON feeds",
    tags=["real-world", "production"],
    test_cases=[
        DateTimeTestCase(
            input_string="Mon, 13 Jan 2025 14:30:45 +0000",
            expected_datetime=datetime(2025, 1, 13, 14, 30, 45, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC822,
            description="WordPress RSS date",
            tags=["wordpress", "rss"],
        ),
        DateTimeTestCase(
            input_string="2025-01-13T14:30:45.123Z",
            expected_datetime=datetime(
                2025, 1, 13, 14, 30, 45, 123000, tzinfo=timezone.utc
            ),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="Atom feed date with milliseconds",
            tags=["atom", "milliseconds"],
        ),
        DateTimeTestCase(
            input_string="2025-01-13T14:30:45-05:00",
            expected_datetime=datetime(2025, 1, 13, 19, 30, 45, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC3339,
            description="JSON Feed date",
            tags=["json-feed"],
        ),
        DateTimeTestCase(
            input_string="2025-01-13 14:30:45",
            expected_datetime=datetime(2025, 1, 13, 14, 30, 45, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.CUSTOM,
            description="Medium-style RSS date",
            tags=["medium", "custom"],
        ),
        DateTimeTestCase(
            input_string="Mon, 13 Jan 2025 14:30:45 GMT",
            expected_datetime=datetime(2025, 1, 13, 14, 30, 45, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
            format_type=DateTimeFormat.RFC822,
            description="FeedBurner date",
            tags=["feedburner"],
        ),
        DateTimeTestCase(
            input_string="Mon, 13 Jan 2025 06:30:00 PST",
            expected_datetime=datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_WARN,
            format_type=DateTimeFormat.RFC822,
            description="Podcast RSS with PST timezone",
            tags=["podcast", "timezone", "pst"],
            notes="May produce UnknownTimezoneWarning for PST",
        ),
    ],
)


# =============================================================================
# Complete Test Suite
# =============================================================================

DATETIME_TEST_SUITE = {
    "rfc3339": RFC3339_DATES,
    "rfc822": RFC822_DATES,
    "language_specific": LANGUAGE_SPECIFIC_DATES,
    "edge_cases": EDGE_CASE_DATES,
    "invalid": INVALID_DATES,
    "real_world": REAL_WORLD_DATES,
}


def get_all_test_cases() -> List[DateTimeTestCase]:
    """Get all test cases from all categories."""
    all_cases = []
    for category in DATETIME_TEST_SUITE.values():
        all_cases.extend(category.test_cases)
    return all_cases


def get_test_cases_by_behavior(behavior: ExpectedBehavior) -> List[DateTimeTestCase]:
    """Get all test cases with a specific expected behavior."""
    return [tc for tc in get_all_test_cases() if tc.expected_behavior == behavior]


def get_test_cases_by_language(language: str) -> List[DateTimeTestCase]:
    """Get all test cases for a specific language."""
    return [tc for tc in get_all_test_cases() if tc.language == language]


def get_test_cases_by_tags(tags: List[str]) -> List[DateTimeTestCase]:
    """Get all test cases that have all specified tags."""
    return [tc for tc in get_all_test_cases() if all(tag in tc.tags for tag in tags)]


def get_languages() -> List[str]:
    """Get list of all languages in test suite."""
    languages = set()
    for tc in get_all_test_cases():
        languages.add(tc.language)
    return sorted(languages)


def get_summary_stats() -> Dict[str, Any]:
    """Get summary statistics about the test suite."""
    all_cases = get_all_test_cases()
    return {
        "total_test_cases": len(all_cases),
        "categories": len(DATETIME_TEST_SUITE),
        "languages": len(get_languages()),
        "by_behavior": {
            behavior.value: len(get_test_cases_by_behavior(behavior))
            for behavior in ExpectedBehavior
        },
        "by_format": {
            fmt.value: len([tc for tc in all_cases if tc.format_type == fmt])
            for fmt in DateTimeFormat
        },
        "languages_list": get_languages(),
    }


# =============================================================================
# Test Data Export Functions
# =============================================================================


def export_to_pytest_params(
    category_name: str, id_template: str = "{description}"
) -> List[tuple]:
    """Export test cases as pytest parametrize tuples.

    Args:
        category_name: Name of category in DATETIME_TEST_SUITE
        id_template: Template for test IDs (can use any DateTimeTestCase field)

    Returns:
        List of (input_string, expected_datetime, expected_behavior) tuples

    Example:
        @pytest.mark.parametrize(
            "input_string,expected_datetime,expected_behavior",
            export_to_pytest_params("rfc3339"),
            ids=lambda x: x[2].description if len(x) > 2 else ""
        )
        def test_dates(input_string, expected_datetime, expected_behavior):
            ...
    """
    category = DATETIME_TEST_SUITE.get(category_name)
    if not category:
        raise ValueError(f"Unknown category: {category_name}")

    return [
        (tc.input_string, tc.expected_datetime, tc.expected_behavior, tc)
        for tc in category.test_cases
    ]


if __name__ == "__main__":
    # Print summary when run directly
    import json

    stats = get_summary_stats()
    print("DateTime Test Suite Summary")
    print("=" * 50)
    print(json.dumps(stats, indent=2, default=str))
