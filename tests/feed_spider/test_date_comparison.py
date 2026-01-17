"""
Tests for date parsing comparison logic between feedparser and dateutil.

This module tests the parse_date_with_comparison function that compares
feedparser's struct_time results with dateutil's parsing of raw strings.
"""

import time
from datetime import datetime

from feedsearch_crawler.feed_spider.lib import parse_date_with_comparison


class TestDateComparison:
    """Test comparison between feedparser and dateutil date parsing."""

    def test_both_parsers_agree(self):
        """When both parsers agree, use feedparser result."""
        date_string = "2025-01-13T14:30:00Z"
        # Create struct_time for the same date
        parsed_tuple = time.strptime("2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S")

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13
        assert result.hour == 14
        assert result.minute == 30
        # Check that it's UTC (using dateutil's tzutc)
        assert result.tzinfo is not None
        assert result.utcoffset().total_seconds() == 0

    def test_parsers_differ_uses_dateutil(self):
        """When parsers differ, use dateutil result."""
        date_string = "2025-01-13T14:30:00Z"
        # Create struct_time for a different date
        parsed_tuple = time.strptime("2025-01-13 10:00:00", "%Y-%m-%d %H:%M:%S")

        result = parse_date_with_comparison(date_string, parsed_tuple)

        # Should use dateutil result (14:30) not feedparser (10:00)
        assert result is not None
        assert result.hour == 14
        assert result.minute == 30

    def test_only_dateutil_available(self):
        """When only date string is available, use dateutil."""
        date_string = "Mon, 13 Jan 2025 14:30:00 GMT"
        parsed_tuple = None

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13

    def test_only_feedparser_available(self):
        """When only struct_time is available, use feedparser."""
        date_string = None
        parsed_tuple = time.strptime("2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S")

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13

    def test_both_none(self):
        """When both are None, return None."""
        result = parse_date_with_comparison(None, None)
        assert result is None

    def test_both_invalid(self):
        """When both fail to parse, return None."""
        date_string = "invalid date"
        parsed_tuple = None  # Invalid struct_time

        result = parse_date_with_comparison(date_string, parsed_tuple)
        assert result is None

    def test_with_locale_parameter(self):
        """Locale parameter is accepted and logged."""
        date_string = "2025-01-13T14:30:00Z"
        parsed_tuple = None

        result = parse_date_with_comparison(date_string, parsed_tuple, locale="en_US")

        assert result is not None
        assert result.year == 2025

    def test_rfc822_format(self):
        """Test with RFC 822 format (RSS)."""
        date_string = "Mon, 13 Jan 2025 14:30:00 +0000"
        parsed_tuple = time.strptime(
            "Mon, 13 Jan 2025 14:30:00", "%a, %d %b %Y %H:%M:%S"
        )

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        # Check that it's UTC
        assert result.tzinfo is not None
        assert result.utcoffset().total_seconds() == 0

    def test_rfc3339_format(self):
        """Test with RFC 3339 format (Atom)."""
        date_string = "2025-01-13T14:30:00Z"
        parsed_tuple = time.strptime("2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S")

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        assert result.year == 2025
        # Check that it's UTC
        assert result.tzinfo is not None
        assert result.utcoffset().total_seconds() == 0

    def test_struct_time_with_invalid_values(self):
        """Test that invalid struct_time is handled gracefully."""
        date_string = "2025-01-13T14:30:00Z"
        # Create invalid struct_time (year 9999 causes OverflowError in some cases)
        try:
            parsed_tuple = time.struct_time((9999, 99, 99, 0, 0, 0, 0, 0, 0))
        except ValueError:
            parsed_tuple = None

        result = parse_date_with_comparison(date_string, parsed_tuple)

        # Should fall back to dateutil
        assert result is not None
        assert result.year == 2025

    def test_empty_string(self):
        """Empty string is handled gracefully."""
        result = parse_date_with_comparison("", None)
        assert result is None

    def test_whitespace_string(self):
        """Whitespace-only string is handled gracefully."""
        result = parse_date_with_comparison("   ", None)
        assert result is None


class TestEntryDatesWithComparison:
    """Test entry_dates method with comparison logic."""

    def test_entry_dates_with_parsed_tuple(self):
        """Test that entry_dates uses comparison with *_parsed fields."""
        from datetime import date

        from feedsearch_crawler.feed_spider.feed_info_parser import FeedInfoParser

        # Simulate feedparser output with both string and parsed fields
        entries = [
            {
                "published": "2025-01-13T14:30:00Z",
                "published_parsed": time.strptime(
                    "2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S"
                ),
            },
            {
                "updated": "2025-01-14T10:00:00Z",
                "updated_parsed": time.strptime(
                    "2025-01-14 10:00:00", "%Y-%m-%d %H:%M:%S"
                ),
            },
        ]

        current_date = date(2025, 1, 15)
        dates = list(
            FeedInfoParser.entry_dates(entries, ["published", "updated"], current_date)
        )

        assert len(dates) == 2
        assert all(isinstance(d, datetime) for d in dates)
        assert dates[0].day == 13
        assert dates[1].day == 14

    def test_entry_dates_without_parsed_tuple(self):
        """Test entry_dates with only raw date strings (JSON feeds)."""
        from datetime import date

        from feedsearch_crawler.feed_spider.feed_info_parser import FeedInfoParser

        # JSON feed entries don't have *_parsed fields
        entries = [
            {"date_published": "2025-01-13T14:30:00Z"},
            {"date_modified": "2025-01-14T10:00:00Z"},
        ]

        current_date = date(2025, 1, 15)
        dates = list(
            FeedInfoParser.entry_dates(
                entries, ["date_published", "date_modified"], current_date
            )
        )

        assert len(dates) == 2
        assert dates[0].day == 13
        assert dates[1].day == 14

    def test_entry_dates_with_locale(self):
        """Test entry_dates accepts locale parameter."""
        from datetime import date

        from feedsearch_crawler.feed_spider.feed_info_parser import FeedInfoParser

        entries = [{"published": "2025-01-13T14:30:00Z"}]

        current_date = date(2025, 1, 15)
        dates = list(
            FeedInfoParser.entry_dates(
                entries, ["published"], current_date, locale="en_US"
            )
        )

        assert len(dates) == 1
        assert dates[0].day == 13

    def test_entry_dates_filters_future(self):
        """Test that future dates are filtered out."""
        from datetime import date

        from feedsearch_crawler.feed_spider.feed_info_parser import FeedInfoParser

        entries = [
            {"published": "2025-01-13T14:30:00Z"},  # Past
            {"published": "2025-12-31T23:59:59Z"},  # Future
        ]

        current_date = date(2025, 1, 15)
        dates = list(FeedInfoParser.entry_dates(entries, ["published"], current_date))

        # Only past date should be included
        assert len(dates) == 1
        assert dates[0].day == 13

    def test_entry_dates_handles_missing_fields(self):
        """Test graceful handling of missing date fields."""
        from datetime import date

        from feedsearch_crawler.feed_spider.feed_info_parser import FeedInfoParser

        entries = [
            {"published": "2025-01-13T14:30:00Z"},
            {"title": "No date field"},  # Missing date
            {"updated": "2025-01-14T10:00:00Z"},
        ]

        current_date = date(2025, 1, 15)
        dates = list(FeedInfoParser.entry_dates(entries, ["published"], current_date))

        # Should get dates from entries that have them
        assert len(dates) == 1

    def test_entry_dates_handles_invalid_dates(self):
        """Test graceful handling of invalid date values."""
        from datetime import date

        from feedsearch_crawler.feed_spider.feed_info_parser import FeedInfoParser

        entries = [
            {"published": "2025-01-13T14:30:00Z"},  # Valid
            {"published": "invalid date"},  # Invalid
            {"published": "2025-01-14T10:00:00Z"},  # Valid
        ]

        current_date = date(2025, 1, 15)
        dates = list(FeedInfoParser.entry_dates(entries, ["published"], current_date))

        # Should get 2 valid dates
        assert len(dates) == 2


class TestFeedparserFallbackForNonEnglish:
    """Test that feedparser's parsed dates are used as fallback for non-English strings.

    When dateutil fails to parse a non-English date string (e.g., French "janvier"),
    the function should fall back to feedparser's pre-parsed struct_time result.
    This ensures feeds with non-English dates still get proper date metadata.
    """

    def test_french_date_falls_back_to_feedparser(self):
        """French date string that dateutil can't parse uses feedparser result."""
        # French date string - dateutil will fail on "janvier"
        date_string = "Lundi 13 janvier 2025 14:30:00"
        # But feedparser would have parsed it successfully
        parsed_tuple = time.strptime("2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S")

        result = parse_date_with_comparison(date_string, parsed_tuple)

        # Should use feedparser result since dateutil fails
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13
        assert result.hour == 14
        assert result.minute == 30

    def test_german_date_falls_back_to_feedparser(self):
        """German date string that dateutil can't parse uses feedparser result."""
        date_string = "Montag, 13. Januar 2025 14:30 Uhr"
        parsed_tuple = time.strptime("2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S")

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13

    def test_spanish_date_falls_back_to_feedparser(self):
        """Spanish date string that dateutil can't parse uses feedparser result."""
        date_string = "Lunes, 13 de enero de 2025 14:30"
        parsed_tuple = time.strptime("2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S")

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13

    def test_russian_date_falls_back_to_feedparser(self):
        """Russian/Cyrillic date string uses feedparser result."""
        date_string = "13 января 2025 14:30"
        parsed_tuple = time.strptime("2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S")

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13

    def test_japanese_date_falls_back_to_feedparser(self):
        """Japanese date string uses feedparser result."""
        date_string = "2025年1月13日 14時30分"
        parsed_tuple = time.strptime("2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S")

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13

    def test_chinese_date_falls_back_to_feedparser(self):
        """Chinese date string uses feedparser result."""
        date_string = "2025年1月13日 14:30"
        parsed_tuple = time.strptime("2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S")

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13


class TestExistingFunctionalityPreserved:
    """Ensure feedparser fallback doesn't override existing functionality.

    These tests verify that when dateutil CAN parse the date string,
    its result is still used (not overridden by feedparser).
    """

    def test_english_rfc822_uses_dateutil_when_both_agree(self):
        """Standard RFC 822 dates still work with dateutil."""
        date_string = "Mon, 13 Jan 2025 14:30:00 GMT"
        parsed_tuple = time.strptime("2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S")

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13
        assert result.hour == 14
        assert result.minute == 30

    def test_iso8601_uses_dateutil_when_both_agree(self):
        """ISO 8601 dates still work with dateutil."""
        date_string = "2025-01-13T14:30:00Z"
        parsed_tuple = time.strptime("2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S")

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13

    def test_dateutil_preferred_when_parsers_differ(self):
        """When both parse but differ, dateutil result is used."""
        # RFC 822 with timezone - dateutil will handle correctly
        date_string = "Mon, 13 Jan 2025 14:30:00 -0500"
        # Feedparser might not adjust for timezone in struct_time
        parsed_tuple = time.strptime("2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S")

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        # Dateutil should convert -0500 to UTC (19:30)
        assert result.hour == 19
        assert result.minute == 30

    def test_dateutil_still_used_for_json_feed_dates(self):
        """JSON Feed dates (no feedparser tuple) still use dateutil."""
        date_string = "2025-01-13T14:30:00-05:00"
        parsed_tuple = None  # JSON feeds don't have *_parsed fields

        result = parse_date_with_comparison(date_string, parsed_tuple)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13
        # Should be converted to UTC
        assert result.hour == 19
        assert result.minute == 30


class TestEntryDatesNonEnglishFallback:
    """Test entry_dates method with non-English dates and feedparser fallback."""

    def test_entry_dates_non_english_with_parsed_tuple(self):
        """Non-English dates with *_parsed fields are handled correctly."""
        from datetime import date

        from feedsearch_crawler.feed_spider.feed_info_parser import FeedInfoParser

        # Simulate feedparser output for a French feed
        entries = [
            {
                "published": "Lundi 13 janvier 2025 14:30:00",  # French - dateutil fails
                "published_parsed": time.strptime(
                    "2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S"
                ),
            },
            {
                "published": "Mardi 14 janvier 2025 10:00:00",  # French - dateutil fails
                "published_parsed": time.strptime(
                    "2025-01-14 10:00:00", "%Y-%m-%d %H:%M:%S"
                ),
            },
        ]

        current_date = date(2025, 1, 15)
        dates = list(FeedInfoParser.entry_dates(entries, ["published"], current_date))

        # Both dates should be parsed via feedparser fallback
        assert len(dates) == 2
        assert all(isinstance(d, datetime) for d in dates)
        assert dates[0].day == 13
        assert dates[1].day == 14

    def test_mixed_english_and_non_english_entries(self):
        """Mixed English and non-English dates in same feed work correctly."""
        from datetime import date

        from feedsearch_crawler.feed_spider.feed_info_parser import FeedInfoParser

        entries = [
            {
                # English - dateutil handles this
                "published": "Mon, 13 Jan 2025 14:30:00 GMT",
                "published_parsed": time.strptime(
                    "2025-01-13 14:30:00", "%Y-%m-%d %H:%M:%S"
                ),
            },
            {
                # French - falls back to feedparser
                "published": "Mardi 14 janvier 2025 10:00:00",
                "published_parsed": time.strptime(
                    "2025-01-14 10:00:00", "%Y-%m-%d %H:%M:%S"
                ),
            },
            {
                # ISO format - dateutil handles this
                "published": "2025-01-15T08:00:00Z",
                "published_parsed": time.strptime(
                    "2025-01-15 08:00:00", "%Y-%m-%d %H:%M:%S"
                ),
            },
        ]

        current_date = date(2025, 1, 16)
        dates = list(FeedInfoParser.entry_dates(entries, ["published"], current_date))

        # All three dates should be parsed
        assert len(dates) == 3
        days = sorted([d.day for d in dates])
        assert days == [13, 14, 15]

    def test_non_english_without_parsed_tuple_returns_none(self):
        """Non-English dates without feedparser backup are skipped gracefully."""
        from datetime import date

        from feedsearch_crawler.feed_spider.feed_info_parser import FeedInfoParser

        entries = [
            {
                # French without *_parsed - will be skipped
                "published": "Lundi 13 janvier 2025 14:30:00",
                # No published_parsed field
            },
            {
                # English - will work
                "published": "Tue, 14 Jan 2025 10:00:00 GMT",
                "published_parsed": time.strptime(
                    "2025-01-14 10:00:00", "%Y-%m-%d %H:%M:%S"
                ),
            },
        ]

        current_date = date(2025, 1, 15)
        dates = list(FeedInfoParser.entry_dates(entries, ["published"], current_date))

        # Only the English date should be parsed
        assert len(dates) == 1
        assert dates[0].day == 14
