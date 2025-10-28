"""Example tests using the datetime_test_data fixtures.

This file demonstrates how to use the structured test data from datetime_test_data.py
for comprehensive datetime parsing tests.
"""

import pytest
from datetime import datetime

from feedsearch_crawler.feed_spider.lib import datestring_to_utc_datetime
from tests.feed_spider.datetime_test_data import (
    DATETIME_TEST_SUITE,
    DateTimeTestCase,
    ExpectedBehavior,
    get_all_test_cases,
    get_test_cases_by_behavior,
    get_test_cases_by_language,
    get_test_cases_by_tags,
)


# =============================================================================
# Parametrized Tests Using Test Data
# =============================================================================


@pytest.mark.parametrize(
    "test_case",
    DATETIME_TEST_SUITE["rfc3339"].test_cases,
    ids=lambda tc: tc.description,
)
def test_rfc3339_dates(test_case: DateTimeTestCase):
    """Test RFC 3339 date parsing."""
    result = datestring_to_utc_datetime(test_case.input_string)

    if test_case.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
        assert result is not None, f"Failed to parse: {test_case.description}"
        assert result == test_case.expected_datetime, (
            f"Unexpected result for: {test_case.description}"
        )
    elif test_case.expected_behavior == ExpectedBehavior.PARSE_FAIL:
        assert result is None, f"Should have failed to parse: {test_case.description}"


@pytest.mark.parametrize(
    "test_case", DATETIME_TEST_SUITE["rfc822"].test_cases, ids=lambda tc: tc.description
)
def test_rfc822_dates(test_case: DateTimeTestCase):
    """Test RFC 822 date parsing."""
    result = datestring_to_utc_datetime(test_case.input_string)

    if test_case.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
        assert result is not None, f"Failed to parse: {test_case.description}"
        assert result == test_case.expected_datetime
    elif test_case.expected_behavior == ExpectedBehavior.PARSE_WARN:
        # Should parse but may produce warnings
        assert result is not None, f"Failed to parse: {test_case.description}"
        # Approximate match (timezone interpretation may vary)
        assert result.year == test_case.expected_datetime.year
        assert result.month == test_case.expected_datetime.month
        assert result.day == test_case.expected_datetime.day


@pytest.mark.parametrize(
    "test_case",
    DATETIME_TEST_SUITE["language_specific"].test_cases,
    ids=lambda tc: f"{tc.language}_{tc.description}",
)
def test_language_specific_dates(test_case: DateTimeTestCase):
    """Test language-specific date parsing.

    These are expected to fail with current implementation.
    """
    if test_case.expected_behavior == ExpectedBehavior.PARSE_XFAIL:
        pytest.xfail(test_case.notes or "Non-English dates not supported")

    result = datestring_to_utc_datetime(test_case.input_string)
    assert result is not None, f"Failed to parse: {test_case.description}"
    assert result == test_case.expected_datetime


@pytest.mark.parametrize(
    "test_case",
    DATETIME_TEST_SUITE["edge_cases"].test_cases,
    ids=lambda tc: tc.description,
)
def test_edge_cases(test_case: DateTimeTestCase):
    """Test edge cases and boundary conditions."""
    result = datestring_to_utc_datetime(test_case.input_string)

    assert result is not None, f"Failed to parse: {test_case.description}"
    assert result == test_case.expected_datetime


@pytest.mark.parametrize(
    "test_case",
    DATETIME_TEST_SUITE["invalid"].test_cases,
    ids=lambda tc: tc.description,
)
def test_invalid_dates(test_case: DateTimeTestCase):
    """Test handling of invalid dates."""
    result = datestring_to_utc_datetime(test_case.input_string)
    assert result is None, (
        f"Should return None for invalid input: {test_case.description}"
    )


@pytest.mark.parametrize(
    "test_case",
    DATETIME_TEST_SUITE["real_world"].test_cases,
    ids=lambda tc: tc.description,
)
def test_real_world_examples(test_case: DateTimeTestCase):
    """Test real-world feed date formats."""
    result = datestring_to_utc_datetime(test_case.input_string)

    if test_case.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
        assert result is not None, f"Failed to parse: {test_case.description}"
        assert result == test_case.expected_datetime
    elif test_case.expected_behavior == ExpectedBehavior.PARSE_WARN:
        assert result is not None, f"Failed to parse: {test_case.description}"
        # Allow some flexibility for timezone interpretation


# =============================================================================
# Tests Using Helper Functions
# =============================================================================


class TestByBehavior:
    """Test grouping by expected behavior."""

    def test_all_success_cases_parse(self):
        """Test that all cases expected to succeed actually parse."""
        success_cases = get_test_cases_by_behavior(ExpectedBehavior.PARSE_SUCCESS)
        failures = []

        for tc in success_cases:
            result = datestring_to_utc_datetime(tc.input_string)
            if result is None:
                failures.append(tc.description)
            elif result != tc.expected_datetime:
                failures.append(f"{tc.description} (wrong result)")

        if failures:
            pytest.fail(f"Failed cases: {', '.join(failures)}")

    def test_all_fail_cases_return_none(self):
        """Test that all cases expected to fail return None."""
        fail_cases = get_test_cases_by_behavior(ExpectedBehavior.PARSE_FAIL)
        successes = []

        for tc in fail_cases:
            result = datestring_to_utc_datetime(tc.input_string)
            if result is not None:
                successes.append(tc.description)

        if successes:
            pytest.fail(f"Unexpectedly succeeded: {', '.join(successes)}")


class TestByLanguage:
    """Test grouping by language."""

    @pytest.mark.parametrize("language", ["en", "fr", "de", "es", "ja", "zh"])
    def test_language_support(self, language):
        """Test parsing support for specific languages."""
        test_cases = get_test_cases_by_language(language)
        assert len(test_cases) > 0, f"No test cases for language: {language}"

        if language == "en":
            # English should work
            for tc in test_cases:
                if tc.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
                    result = datestring_to_utc_datetime(tc.input_string)
                    assert result is not None, f"Failed: {tc.description}"
        else:
            # Non-English expected to fail with current implementation
            pytest.skip(f"{language} dates not yet supported")


class TestByTags:
    """Test grouping by tags."""

    def test_timezone_handling(self):
        """Test all cases with timezone tag."""
        tz_cases = get_test_cases_by_tags(["timezone"])
        assert len(tz_cases) > 0, "No timezone test cases found"

        for tc in tz_cases:
            if tc.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
                result = datestring_to_utc_datetime(tc.input_string)
                assert result is not None, f"Failed: {tc.description}"
                # Verify it's UTC
                assert result.tzinfo is not None

    def test_leap_year_handling(self):
        """Test all cases with leap-year tag."""
        leap_cases = get_test_cases_by_tags(["leap-year"])
        assert len(leap_cases) > 0, "No leap year test cases found"

        for tc in leap_cases:
            result = datestring_to_utc_datetime(tc.input_string)
            if tc.expected_behavior == ExpectedBehavior.PARSE_SUCCESS:
                assert result is not None, f"Failed: {tc.description}"
            else:
                assert result is None, f"Should fail: {tc.description}"


# =============================================================================
# Test Suite Metadata
# =============================================================================


def test_suite_completeness():
    """Verify test suite has comprehensive coverage."""
    from tests.feed_spider.datetime_test_data import get_summary_stats

    stats = get_summary_stats()

    # Should have reasonable number of test cases
    assert stats["total_test_cases"] >= 50, "Test suite should have 50+ cases"

    # Should cover multiple languages
    assert stats["languages"] >= 10, "Should test 10+ languages"

    # Should have all categories
    assert stats["categories"] >= 5, "Should have 5+ categories"

    # Should test all behaviors
    for behavior in ExpectedBehavior:
        count = stats["by_behavior"].get(behavior.value, 0)
        assert count > 0, f"No tests for behavior: {behavior.value}"


def test_no_duplicate_descriptions():
    """Ensure all test case descriptions are unique."""
    all_cases = get_all_test_cases()
    descriptions = [tc.description for tc in all_cases]

    duplicates = [d for d in descriptions if descriptions.count(d) > 1]
    assert len(set(duplicates)) == 0, f"Duplicate descriptions: {set(duplicates)}"


# =============================================================================
# Performance Tests
# =============================================================================


def test_parse_all_valid_dates_performance():
    """Test that parsing all valid dates completes quickly."""
    import time

    success_cases = get_test_cases_by_behavior(ExpectedBehavior.PARSE_SUCCESS)

    start = time.perf_counter()
    for tc in success_cases:
        datestring_to_utc_datetime(tc.input_string)
    duration = time.perf_counter() - start

    # Should parse all valid dates in reasonable time
    # Roughly < 50ms per date on modern hardware
    max_time = len(success_cases) * 0.05
    assert duration < max_time, (
        f"Too slow: {duration:.3f}s for {len(success_cases)} dates"
    )


# =============================================================================
# Example: Adding New Test Data Programmatically
# =============================================================================


def test_dynamic_test_addition():
    """Example of how to add test data dynamically."""
    from tests.feed_spider.datetime_test_data import (
        DateTimeTestCase,
        DateTimeFormat,
        ExpectedBehavior,
        RFC3339_DATES,
    )

    # Create a new test case
    from datetime import timezone

    new_test = DateTimeTestCase(
        input_string="2025-06-15T10:20:30Z",
        expected_datetime=datetime(2025, 6, 15, 10, 20, 30, tzinfo=timezone.utc),
        expected_behavior=ExpectedBehavior.PARSE_SUCCESS,
        format_type=DateTimeFormat.RFC3339,
        description="Dynamically added test",
        tags=["dynamic", "example"],
    )

    # Add to category
    original_count = len(RFC3339_DATES.test_cases)
    RFC3339_DATES.add_test(new_test)

    assert len(RFC3339_DATES.test_cases) == original_count + 1

    # Test it
    result = datestring_to_utc_datetime(new_test.input_string)
    assert result == new_test.expected_datetime

    # Clean up (remove it so it doesn't affect other tests)
    RFC3339_DATES.test_cases.remove(new_test)
