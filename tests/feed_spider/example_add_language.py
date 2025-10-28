"""Example: How to add a new language to datetime test data.

This example demonstrates adding Norwegian language support with multiple
date format variants.
"""

from datetime import datetime, timezone

from tests.feed_spider.datetime_test_data import (
    LANGUAGE_SPECIFIC_DATES,
    DateTimeTestCase,
    DateTimeFormat,
    ExpectedBehavior,
)


def add_norwegian_date_formats():
    """Add Norwegian (Bokmål) date formats to test suite.

    Norwegian dates use:
    - Weekdays: mandag, tirsdag, onsdag, torsdag, fredag, lørdag, søndag
    - Months: januar, februar, mars, april, mai, juni, juli,
              august, september, oktober, november, desember
    - Format: "Dag DD. måned YYYY [kl. ]HH:MM[:SS]"
    """

    # Reference datetime for all Norwegian tests
    ref_dt = datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc)

    # Norwegian test cases
    norwegian_tests = [
        # Format 1: Full format with weekday and "kl." (kl = klokken = o'clock)
        DateTimeTestCase(
            input_string="Mandag 13. januar 2025 kl. 14:30",
            expected_datetime=ref_dt,
            expected_behavior=ExpectedBehavior.PARSE_XFAIL,
            format_type=DateTimeFormat.LOCALIZED,
            description="Norwegian full format with 'kl.' time prefix",
            language="no",
            tags=["localized", "non-english", "no", "norwegian", "full-format"],
            notes="Norwegian uses 'kl.' (klokken) before time. Month names: januar, februar, etc.",
        ),
        # Format 2: Without weekday
        DateTimeTestCase(
            input_string="13. januar 2025 kl. 14:30",
            expected_datetime=ref_dt,
            expected_behavior=ExpectedBehavior.PARSE_XFAIL,
            format_type=DateTimeFormat.LOCALIZED,
            description="Norwegian without weekday",
            language="no",
            tags=["localized", "non-english", "no", "norwegian"],
            notes="Common in written Norwegian",
        ),
        # Format 3: Without "kl." prefix
        DateTimeTestCase(
            input_string="13. januar 2025 14:30",
            expected_datetime=ref_dt,
            expected_behavior=ExpectedBehavior.PARSE_XFAIL,
            format_type=DateTimeFormat.LOCALIZED,
            description="Norwegian without 'kl.' prefix",
            language="no",
            tags=["localized", "non-english", "no", "norwegian", "informal"],
        ),
        # Format 4: Date only
        DateTimeTestCase(
            input_string="13. januar 2025",
            expected_datetime=datetime(2025, 1, 13, 0, 0, 0, tzinfo=timezone.utc),
            expected_behavior=ExpectedBehavior.PARSE_XFAIL,
            format_type=DateTimeFormat.LOCALIZED,
            description="Norwegian date only",
            language="no",
            tags=["localized", "non-english", "no", "norwegian", "date-only"],
        ),
        # Format 5: Abbreviated month (informal)
        DateTimeTestCase(
            input_string="13. jan. 2025 14:30",
            expected_datetime=ref_dt,
            expected_behavior=ExpectedBehavior.PARSE_XFAIL,
            format_type=DateTimeFormat.LOCALIZED,
            description="Norwegian with abbreviated month",
            language="no",
            tags=["localized", "non-english", "no", "norwegian", "abbreviated"],
            notes="Jan, feb, mar, apr, mai, jun, jul, aug, sep, okt, nov, des",
        ),
        # Format 6: Lowercase (common in informal writing)
        DateTimeTestCase(
            input_string="mandag 13. januar 2025 kl. 14:30",
            expected_datetime=ref_dt,
            expected_behavior=ExpectedBehavior.PARSE_XFAIL,
            format_type=DateTimeFormat.LOCALIZED,
            description="Norwegian with lowercase weekday",
            language="no",
            tags=["localized", "non-english", "no", "norwegian", "lowercase"],
            notes="Lowercase is common in Norwegian",
        ),
    ]

    # Add all Norwegian tests to the language-specific category
    for test in norwegian_tests:
        LANGUAGE_SPECIFIC_DATES.add_test(test)

    print(f"✅ Added {len(norwegian_tests)} Norwegian test cases")


def add_hindi_date_formats():
    """Add Hindi (Devanagari script) date formats.

    Hindi dates use:
    - Devanagari numerals or Arabic numerals
    - Month names in Hindi
    - Various format patterns
    """

    ref_dt = datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc)

    hindi_tests = [
        DateTimeTestCase(
            input_string="13 जनवरी 2025 14:30",
            expected_datetime=ref_dt,
            expected_behavior=ExpectedBehavior.PARSE_XFAIL,
            format_type=DateTimeFormat.LOCALIZED,
            description="Hindi with Devanagari month name",
            language="hi",
            tags=["localized", "non-english", "hi", "hindi", "devanagari"],
            notes="Uses Devanagari script for month names",
        ),
        DateTimeTestCase(
            input_string="१३ जनवरी २०२५ १४:३०",
            expected_datetime=ref_dt,
            expected_behavior=ExpectedBehavior.PARSE_XFAIL,
            format_type=DateTimeFormat.LOCALIZED,
            description="Hindi with Devanagari numerals",
            language="hi",
            tags=["localized", "non-english", "hi", "hindi", "devanagari", "numerals"],
            notes="Uses Devanagari numerals (०-९) instead of Arabic numerals",
        ),
    ]

    for test in hindi_tests:
        LANGUAGE_SPECIFIC_DATES.add_test(test)

    print(f"✅ Added {len(hindi_tests)} Hindi test cases")


def add_greek_date_formats():
    """Add Greek date formats.

    Greek dates use:
    - Greek month names
    - Greek weekday names
    - Various format patterns
    """

    ref_dt = datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc)

    greek_tests = [
        DateTimeTestCase(
            input_string="Δευτέρα, 13 Ιανουαρίου 2025, 14:30",
            expected_datetime=ref_dt,
            expected_behavior=ExpectedBehavior.PARSE_XFAIL,
            format_type=DateTimeFormat.LOCALIZED,
            description="Greek full format with genitive month",
            language="el",
            tags=["localized", "non-english", "el", "greek"],
            notes="Greek uses genitive case for months in dates (Ιανουαρίου instead of Ιανουάριος)",
        ),
        DateTimeTestCase(
            input_string="13 Ιαν 2025 14:30",
            expected_datetime=ref_dt,
            expected_behavior=ExpectedBehavior.PARSE_XFAIL,
            format_type=DateTimeFormat.LOCALIZED,
            description="Greek abbreviated month",
            language="el",
            tags=["localized", "non-english", "el", "greek", "abbreviated"],
        ),
    ]

    for test in greek_tests:
        LANGUAGE_SPECIFIC_DATES.add_test(test)

    print(f"✅ Added {len(greek_tests)} Greek test cases")


def demonstrate_custom_category():
    """Demonstrate creating a completely custom category.

    This shows how to create a new category for specialized date formats,
    such as dates from specific platforms or APIs.
    """

    from tests.feed_spider.datetime_test_data import (
        DateTimeTestCategory,
        DATETIME_TEST_SUITE,
    )

    # Create a category for GitHub-style dates
    github_dates = DateTimeTestCategory(
        name="GitHub API Dates",
        description="Date formats used in GitHub API responses",
        tags=["github", "api", "platform-specific"],
        test_cases=[
            DateTimeTestCase(
                input_string="2025-01-13T14:30:00Z",
                expected_datetime=datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc),
                expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
                format_type=DateTimeFormat.RFC3339,
                description="GitHub API timestamp (ISO 8601)",
                tags=["github", "api", "rfc3339"],
            ),
        ],
    )

    # Add to test suite
    DATETIME_TEST_SUITE["github_api"] = github_dates
    print("✅ Added GitHub API dates category")


def show_statistics():
    """Show updated statistics after adding new languages."""
    from tests.feed_spider.datetime_test_data import get_summary_stats

    stats = get_summary_stats()

    print("\n" + "=" * 50)
    print("Updated Test Suite Statistics")
    print("=" * 50)
    print(f"Total Test Cases: {stats['total_test_cases']}")
    print(f"Languages: {stats['languages']}")
    print(f"Categories: {stats['categories']}")
    print(f"\nLanguages: {', '.join(sorted(stats['languages_list']))}")


if __name__ == "__main__":
    print("Adding new languages to datetime test data...\n")

    # Add Norwegian
    add_norwegian_date_formats()

    # Add Hindi
    add_hindi_date_formats()

    # Add Greek
    add_greek_date_formats()

    # Show custom category example
    demonstrate_custom_category()

    # Show updated stats
    show_statistics()

    print("\n✅ All examples completed!")
    print("\nTo use these in tests, import from datetime_test_data:")
    print("  from tests.feed_spider.datetime_test_data import DATETIME_TEST_SUITE")
    print("  norwegian_tests = get_test_cases_by_language('no')")
