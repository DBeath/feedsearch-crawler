"""Comprehensive tests for datetime parsing with various formats and locales.

This test suite covers:
- Standard RSS/Atom/JSON Feed formats
- Multiple language date strings
- Edge cases and malformed dates
- Timezone handling
- Invalid inputs
"""

import locale
from datetime import datetime, timezone

import pytest

from feedsearch_crawler.feed_spider.lib import datestring_to_utc_datetime, force_utc


class TestRFC3339Dates:
    """Test Atom and JSON Feed RFC 3339 format dates.

    RFC 3339 is the standard for Atom feeds and JSON Feed.
    Format: YYYY-MM-DDTHH:MM:SS[.fraction][timezone]
    """

    def test_basic_rfc3339_with_z_suffix(self):
        """Test basic RFC 3339 with Z (UTC) suffix."""
        result = datestring_to_utc_datetime("2025-01-13T14:30:00Z")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 0
        assert result.tzinfo is not None

    def test_rfc3339_with_positive_offset(self):
        """Test RFC 3339 with positive timezone offset."""
        result = datestring_to_utc_datetime("2025-01-13T14:30:00+05:30")
        assert result is not None
        # Should be converted to UTC
        assert result.hour == 9  # 14:30 +05:30 = 09:00 UTC
        assert result.minute == 0

    def test_rfc3339_with_negative_offset(self):
        """Test RFC 3339 with negative timezone offset."""
        result = datestring_to_utc_datetime("2025-01-13T14:30:00-05:00")
        assert result is not None
        # Should be converted to UTC
        assert result.hour == 19  # 14:30 -05:00 = 19:30 UTC
        assert result.minute == 30

    def test_rfc3339_with_microseconds(self):
        """Test RFC 3339 with fractional seconds."""
        result = datestring_to_utc_datetime("2025-01-13T14:30:00.123456Z")
        assert result is not None
        assert result.microsecond == 123456

    def test_rfc3339_with_milliseconds(self):
        """Test RFC 3339 with milliseconds."""
        result = datestring_to_utc_datetime("2025-01-13T14:30:00.123Z")
        assert result is not None
        assert result.microsecond == 123000

    def test_rfc3339_zero_offset(self):
        """Test RFC 3339 with +00:00 offset."""
        result = datestring_to_utc_datetime("2025-01-13T14:30:00+00:00")
        assert result is not None
        assert result.hour == 14

    def test_iso8601_compact(self):
        """Test compact ISO 8601 format (no separators)."""
        result = datestring_to_utc_datetime("20250113T143000Z")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13


class TestRFC822Dates:
    """Test RSS 2.0 RFC 822/2822 format dates.

    RFC 822/2822 is the standard for RSS 2.0 feeds.
    Format: Day, DD Mon YYYY HH:MM:SS TZ
    """

    def test_basic_rfc822_with_gmt(self):
        """Test basic RFC 822 with GMT timezone."""
        result = datestring_to_utc_datetime("Mon, 13 Jan 2025 14:30:00 GMT")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13
        assert result.hour == 14

    def test_rfc822_with_numeric_offset(self):
        """Test RFC 822 with numeric timezone offset."""
        result = datestring_to_utc_datetime("Mon, 13 Jan 2025 14:30:00 +0000")
        assert result is not None
        assert result.hour == 14

    def test_rfc822_negative_offset(self):
        """Test RFC 822 with negative timezone offset."""
        result = datestring_to_utc_datetime("Mon, 13 Jan 2025 14:30:00 -0500")
        assert result is not None
        assert result.hour == 19  # Converted to UTC

    def test_rfc822_without_day_name(self):
        """Test RFC 822 without day name."""
        result = datestring_to_utc_datetime("13 Jan 2025 14:30:00 GMT")
        assert result is not None
        assert result.day == 13

    def test_rfc822_two_digit_year(self):
        """Test RFC 822 with two-digit year."""
        result = datestring_to_utc_datetime("13 Jan 25 14:30:00 GMT")
        assert result is not None
        # Should interpret as 2025
        assert result.year == 2025

    def test_rfc822_various_timezones(self):
        """Test RFC 822 with various timezone abbreviations."""
        test_cases = [
            "Mon, 13 Jan 2025 14:30:00 EST",
            "Mon, 13 Jan 2025 14:30:00 PST",
            "Mon, 13 Jan 2025 14:30:00 CST",
            "Mon, 13 Jan 2025 14:30:00 MST",
        ]
        for date_str in test_cases:
            result = datestring_to_utc_datetime(date_str)
            assert result is not None, f"Failed to parse: {date_str}"

    def test_rfc822_full_month_names(self):
        """Test RFC 822 with full month names."""
        result = datestring_to_utc_datetime("Mon, 13 January 2025 14:30:00 GMT")
        assert result is not None
        assert result.month == 1


class TestNonEnglishLocales:
    """Test dates in non-English languages.

    These tests verify that the parser handles (or gracefully fails) dates
    in various languages. Currently, most will fail with the existing
    implementation, which is expected behavior that will be fixed.
    """

    @pytest.mark.xfail(reason="Current implementation may not handle French dates")
    def test_french_date(self):
        """Test French date string."""
        # "Monday, January 13, 2025 at 14:30"
        result = datestring_to_utc_datetime("Lundi 13 janvier 2025 14:30:00")
        assert result is not None

    @pytest.mark.xfail(reason="Current implementation may not handle German dates")
    def test_german_date(self):
        """Test German date string."""
        # "Monday, 13. January 2025 14:30 Uhr"
        result = datestring_to_utc_datetime("Montag, 13. Januar 2025 14:30 Uhr")
        assert result is not None

    @pytest.mark.xfail(reason="Current implementation may not handle Spanish dates")
    def test_spanish_date(self):
        """Test Spanish date string."""
        # "Monday, 13 of January of 2025"
        result = datestring_to_utc_datetime("Lunes, 13 de enero de 2025 14:30")
        assert result is not None

    @pytest.mark.xfail(reason="Current implementation may not handle Italian dates")
    def test_italian_date(self):
        """Test Italian date string."""
        # "Monday, 13 January 2025"
        result = datestring_to_utc_datetime("Lunedì 13 gennaio 2025 14:30")
        assert result is not None

    @pytest.mark.xfail(reason="Current implementation may not handle Portuguese dates")
    def test_portuguese_date(self):
        """Test Portuguese date string."""
        # "Monday, 13 of January of 2025"
        result = datestring_to_utc_datetime(
            "Segunda-feira, 13 de janeiro de 2025 14:30"
        )
        assert result is not None

    @pytest.mark.xfail(reason="Current implementation may not handle Dutch dates")
    def test_dutch_date(self):
        """Test Dutch date string."""
        result = datestring_to_utc_datetime("Maandag 13 januari 2025 14:30")
        assert result is not None

    @pytest.mark.xfail(reason="Current implementation may not handle Russian dates")
    def test_russian_date(self):
        """Test Russian date string."""
        # "13 January 2025"
        result = datestring_to_utc_datetime("13 января 2025 14:30")
        assert result is not None

    @pytest.mark.xfail(reason="Current implementation may not handle Japanese dates")
    def test_japanese_date(self):
        """Test Japanese date string."""
        # "2025年1月13日"
        result = datestring_to_utc_datetime("2025年1月13日 14時30分")
        assert result is not None

    @pytest.mark.xfail(reason="Current implementation may not handle Chinese dates")
    def test_chinese_date(self):
        """Test Chinese date string."""
        # "2025年1月13日"
        result = datestring_to_utc_datetime("2025年1月13日 14:30")
        assert result is not None

    @pytest.mark.xfail(reason="Current implementation may not handle Korean dates")
    def test_korean_date(self):
        """Test Korean date string."""
        # "2025년 1월 13일"
        result = datestring_to_utc_datetime("2025년 1월 13일 14:30")
        assert result is not None


class TestVariousFormats:
    """Test various date formats commonly found in feeds."""

    def test_iso8601_date_only(self):
        """Test ISO 8601 date without time."""
        result = datestring_to_utc_datetime("2025-01-13")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 13

    def test_american_format(self):
        """Test American date format (MM/DD/YYYY)."""
        result = datestring_to_utc_datetime("01/13/2025 14:30:00")
        assert result is not None
        assert result.month == 1
        assert result.day == 13

    def test_european_format(self):
        """Test European date format (DD/MM/YYYY)."""
        # This is ambiguous - may be interpreted as MM/DD
        result = datestring_to_utc_datetime("13/01/2025 14:30:00")
        assert result is not None
        # Could be Jan 13 or potentially misinterpreted

    def test_dotted_format(self):
        """Test dotted date format (DD.MM.YYYY)."""
        result = datestring_to_utc_datetime("13.01.2025 14:30:00")
        assert result is not None

    def test_year_first_format(self):
        """Test year-first format (YYYY/MM/DD)."""
        result = datestring_to_utc_datetime("2025/01/13 14:30:00")
        assert result is not None
        assert result.year == 2025

    def test_verbose_format(self):
        """Test verbose date format."""
        result = datestring_to_utc_datetime("January 13, 2025 at 2:30 PM")
        assert result is not None

    def test_short_month_names(self):
        """Test all short month names."""
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        for i, month in enumerate(months, 1):
            result = datestring_to_utc_datetime(f"13 {month} 2025 14:30:00 GMT")
            assert result is not None, f"Failed to parse month: {month}"
            assert result.month == i


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_leap_year_date(self):
        """Test leap year date."""
        result = datestring_to_utc_datetime("2024-02-29T12:00:00Z")
        assert result is not None
        assert result.month == 2
        assert result.day == 29

    def test_end_of_year(self):
        """Test end of year date."""
        result = datestring_to_utc_datetime("2025-12-31T23:59:59Z")
        assert result is not None
        assert result.month == 12
        assert result.day == 31

    def test_start_of_year(self):
        """Test start of year date."""
        result = datestring_to_utc_datetime("2025-01-01T00:00:00Z")
        assert result is not None
        assert result.month == 1
        assert result.day == 1

    def test_midnight_utc(self):
        """Test midnight UTC."""
        result = datestring_to_utc_datetime("2025-01-13T00:00:00Z")
        assert result is not None
        assert result.hour == 0

    def test_dst_transition_spring(self):
        """Test date during DST transition (spring forward)."""
        # March 9, 2025 is DST transition in US
        result = datestring_to_utc_datetime("2025-03-09T02:30:00-05:00")
        assert result is not None

    def test_dst_transition_fall(self):
        """Test date during DST transition (fall back)."""
        # November 2, 2025 is DST transition in US
        result = datestring_to_utc_datetime("2025-11-02T01:30:00-04:00")
        assert result is not None

    def test_very_old_date(self):
        """Test very old date (1970s)."""
        result = datestring_to_utc_datetime("1970-01-01T00:00:00Z")
        assert result is not None
        assert result.year == 1970

    def test_future_date(self):
        """Test future date."""
        result = datestring_to_utc_datetime("2099-12-31T23:59:59Z")
        assert result is not None
        assert result.year == 2099

    def test_single_digit_components(self):
        """Test dates with single-digit day/month."""
        result = datestring_to_utc_datetime("2025-1-1T9:5:3Z")
        assert result is not None
        assert result.month == 1
        assert result.day == 1


class TestInvalidDates:
    """Test handling of invalid and malformed dates."""

    def test_empty_string(self):
        """Test empty string."""
        result = datestring_to_utc_datetime("")
        assert result is None

    def test_whitespace_only(self):
        """Test whitespace-only string."""
        result = datestring_to_utc_datetime("   ")
        assert result is None

    def test_none_value(self):
        """Test None value."""
        result = datestring_to_utc_datetime(None)
        assert result is None

    def test_non_date_string(self):
        """Test completely invalid string."""
        result = datestring_to_utc_datetime("not a date at all")
        assert result is None

    def test_invalid_month(self):
        """Test date with invalid month."""
        result = datestring_to_utc_datetime("2025-13-01T12:00:00Z")
        assert result is None

    def test_invalid_day(self):
        """Test date with invalid day."""
        result = datestring_to_utc_datetime("2025-01-32T12:00:00Z")
        assert result is None

    def test_invalid_leap_year(self):
        """Test Feb 29 in non-leap year."""
        result = datestring_to_utc_datetime("2025-02-29T12:00:00Z")
        assert result is None

    def test_malformed_rfc3339(self):
        """Test malformed RFC 3339 format."""
        result = datestring_to_utc_datetime("2025-01-13T25:00:00Z")  # Invalid hour
        assert result is None

    def test_partial_date(self):
        """Test incomplete date string."""
        datestring_to_utc_datetime("2025-01")
        # May or may not parse depending on implementation

    def test_garbage_after_valid_date(self):
        """Test valid date followed by garbage."""
        datestring_to_utc_datetime("2025-01-13T12:00:00Z garbage text here")
        # dateutil might parse the valid part

    def test_numeric_only(self):
        """Test purely numeric string."""
        datestring_to_utc_datetime("20250113")
        # Might be interpreted as YYYYMMDD

    def test_wrong_type_integer(self):
        """Test passing wrong type (integer)."""
        result = datestring_to_utc_datetime(12345)
        assert result is None

    def test_wrong_type_list(self):
        """Test passing wrong type (list)."""
        result = datestring_to_utc_datetime(["2025-01-13"])
        assert result is None


class TestTimezoneHandling:
    """Test timezone conversion and handling."""

    def test_naive_datetime_becomes_utc(self):
        """Test that naive datetime is converted to UTC."""
        # Create a naive datetime
        naive = datetime(2025, 1, 13, 14, 30, 0)
        result = force_utc(naive)
        assert result.tzinfo is not None
        # Should be interpreted as UTC
        assert result.hour == 14

    def test_aware_datetime_converted_to_utc(self):
        """Test that aware datetime is converted to UTC."""
        from dateutil import tz

        # Create datetime in EST (UTC-5)
        est = tz.tzoffset("EST", -5 * 3600)
        aware = datetime(2025, 1, 13, 14, 30, 0, tzinfo=est)
        result = force_utc(aware)

        # Should be converted to UTC (14:30 EST = 19:30 UTC)
        assert result.hour == 19
        assert result.minute == 30

    def test_already_utc_unchanged(self):
        """Test that UTC datetime remains unchanged."""
        utc = datetime(2025, 1, 13, 14, 30, 0, tzinfo=timezone.utc)
        result = force_utc(utc)
        assert result.hour == 14
        assert result.minute == 30


class TestLocaleIndependence:
    """Test that parsing is independent of system locale.

    These tests verify that standard RSS/Atom dates parse correctly
    regardless of the system's locale setting.
    """

    def test_rfc822_independent_of_locale(self):
        """Test RFC 822 parsing with different system locales."""
        test_date = "Mon, 13 Jan 2025 14:30:00 GMT"

        # Get original locale
        original = None
        try:
            original = locale.getlocale(locale.LC_TIME)
        except Exception:
            pass

        locales_to_test = []

        # Try to set various locales if available
        for loc in ["C", "en_US.UTF-8", "fr_FR.UTF-8", "de_DE.UTF-8"]:
            try:
                locale.setlocale(locale.LC_TIME, loc)
                locales_to_test.append(loc)
                # Reset to original
                if original:
                    locale.setlocale(locale.LC_TIME, original)
            except Exception:
                # Locale not available on this system
                pass

        # Test with each available locale
        for loc in locales_to_test:
            try:
                locale.setlocale(locale.LC_TIME, loc)
                result = datestring_to_utc_datetime(test_date)
                assert result is not None, f"Failed to parse with locale: {loc}"
                assert result.year == 2025
                assert result.month == 1
                assert result.day == 13
            finally:
                # Always restore original locale
                if original:
                    try:
                        locale.setlocale(locale.LC_TIME, original)
                    except Exception:
                        pass

    def test_rfc3339_independent_of_locale(self):
        """Test RFC 3339 parsing is independent of locale."""
        test_date = "2025-01-13T14:30:00Z"

        original = None
        try:
            original = locale.getlocale(locale.LC_TIME)
        except Exception:
            pass

        try:
            # Try to set to French locale
            try:
                locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
            except Exception:
                # Locale not available, skip
                pytest.skip("French locale not available")

            result = datestring_to_utc_datetime(test_date)
            assert result is not None
            assert result.year == 2025

        finally:
            if original:
                try:
                    locale.setlocale(locale.LC_TIME, original)
                except Exception:
                    pass


class TestRealWorldExamples:
    """Test real-world date formats found in actual feeds."""

    def test_wordpress_rss_date(self):
        """Test WordPress RSS date format."""
        result = datestring_to_utc_datetime("Mon, 13 Jan 2025 14:30:45 +0000")
        assert result is not None

    def test_atom_feed_date(self):
        """Test typical Atom feed date."""
        result = datestring_to_utc_datetime("2025-01-13T14:30:45.123Z")
        assert result is not None

    def test_json_feed_date(self):
        """Test JSON Feed date format."""
        result = datestring_to_utc_datetime("2025-01-13T14:30:45-05:00")
        assert result is not None

    def test_medium_rss_date(self):
        """Test Medium RSS date format."""
        result = datestring_to_utc_datetime("2025-01-13 14:30:45")
        assert result is not None

    def test_feedburner_date(self):
        """Test FeedBurner date format."""
        result = datestring_to_utc_datetime("Mon, 13 Jan 2025 14:30:45 GMT")
        assert result is not None

    def test_podcast_rss_date(self):
        """Test podcast RSS date format."""
        result = datestring_to_utc_datetime("Mon, 13 Jan 2025 06:30:00 PST")
        assert result is not None

    def test_rss_with_milliseconds(self):
        """Test RSS with milliseconds (non-standard but seen in wild)."""
        result = datestring_to_utc_datetime("Mon, 13 Jan 2025 14:30:45.123 GMT")
        assert result is not None


class TestPerformance:
    """Test performance characteristics of date parsing."""

    def test_parse_many_dates(self):
        """Test parsing many dates doesn't degrade significantly."""
        import time

        dates = [
            "2025-01-13T14:30:00Z",
            "Mon, 13 Jan 2025 14:30:00 GMT",
            "2025-01-13T14:30:00+05:30",
            "13 Jan 2025 14:30:00 GMT",
        ] * 250  # 1000 total dates

        start = time.perf_counter()
        results = [datestring_to_utc_datetime(d) for d in dates]
        duration = time.perf_counter() - start

        # Should parse 1000 dates in less than 1 second
        assert duration < 1.0, f"Parsing took {duration:.3f}s, expected < 1.0s"
        assert len([r for r in results if r is not None]) == 1000
