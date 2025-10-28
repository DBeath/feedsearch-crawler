import logging
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Dict, Optional

from dateutil import parser, tz

logger = logging.getLogger(__name__)


class ParseTypes:
    JSON = "json"
    XML = "xml"


def parse_header_links(value: str) -> List[Dict[str, str]]:
    """
    Return a list of Dicts of parsed link headers proxies.
    i.e. Link: <http:/.../front.jpeg>; rel=front; type="image/jpeg",
    <http://.../back.jpeg>; rel=back;type="image/jpeg"

    :param value: HTTP Link header to parse
    :return: List of Dicts
    """

    links = []

    replace_chars = " '\""

    for val in value.split(","):
        try:
            url, params = val.split(";", 1)
        except ValueError:
            url, params = val, ""

        link = {"url": url.strip("<> '\"")}

        for param in params.split(";"):
            try:
                key, value = param.split("=")
            except ValueError:
                break

            link[key.strip(replace_chars)] = value.strip(replace_chars)

        links.append(link)

    return links


# Common timezone abbreviations mapping to UTC offsets (in seconds)
# Used to avoid UnknownTimezoneWarning and ensure consistent parsing
COMMON_TIMEZONES = {
    # US timezones
    "EST": -5 * 3600,  # Eastern Standard Time
    "EDT": -4 * 3600,  # Eastern Daylight Time
    "CST": -6 * 3600,  # Central Standard Time
    "CDT": -5 * 3600,  # Central Daylight Time
    "MST": -7 * 3600,  # Mountain Standard Time
    "MDT": -6 * 3600,  # Mountain Daylight Time
    "PST": -8 * 3600,  # Pacific Standard Time
    "PDT": -7 * 3600,  # Pacific Daylight Time
    # Common abbreviations
    "GMT": 0,  # Greenwich Mean Time
    "UTC": 0,  # Coordinated Universal Time
}


def force_utc(dt: datetime) -> datetime:
    """
    Change a datetime to UTC, and convert naive datetimes to tz-aware UTC.

    :param dt: datetime to change to UTC
    :return: tz-aware UTC datetime
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.tzutc())
    return dt.astimezone(tz.tzutc())


def datestring_to_utc_datetime(date_string: str) -> Optional[datetime]:
    """
    Convert a date string to a tz-aware UTC datetime with robust error handling.

    This function uses a multi-strategy approach for maximum compatibility:
    1. ISO 8601 / RFC 3339 format (most common in modern feeds)
    2. RFC 822 / RFC 2822 format (RSS 2.0 standard)
    3. dateutil.parser as flexible fallback

    The strategies are tried in order of:
    - Locale independence (ISO/RFC formats use English month names)
    - Performance (fromisoformat is fastest)
    - Standards compliance (matches RSS/Atom/JSON Feed specs)

    :param date_string: A datetime string in various formats
    :return: tz-aware UTC datetime, or None if parsing fails
    """
    # Validate input
    if not date_string or not isinstance(date_string, str):
        if date_string is not None:
            logger.debug("Invalid date_string type: %s", type(date_string))
        return None

    date_string = date_string.strip()
    if not date_string:
        return None

    # Strategy 1: Try datetime.fromisoformat for ISO 8601/RFC 3339
    # This is locale-independent, fast, and handles Atom/JSON Feed formats
    try:
        # Handle 'Z' suffix (RFC 3339) by converting to +00:00
        if date_string.endswith("Z"):
            date_string_normalized = date_string[:-1] + "+00:00"
        else:
            date_string_normalized = date_string

        dt = datetime.fromisoformat(date_string_normalized)
        return force_utc(dt)
    except (ValueError, AttributeError):
        # Not ISO 8601 format, try next strategy
        pass

    # Strategy 2: Try email.utils.parsedate_to_datetime for RFC 822/2822
    # This is the RSS 2.0 standard format and is locale-independent
    try:
        dt = parsedate_to_datetime(date_string)
        return force_utc(dt)
    except (ValueError, TypeError):
        # Not RFC 822 format, try next strategy
        pass

    # Strategy 3: Try dateutil.parser as fallback (handles many formats)
    # Note: This CAN be locale-dependent for month names, but handles edge cases
    try:
        # Use ignoretz=False to preserve timezone information
        # Use dayfirst=False and yearfirst=True for international consistency
        # Provide tzinfos for common timezone abbreviations to avoid warnings
        dt = parser.parse(
            date_string,
            ignoretz=False,
            dayfirst=False,
            yearfirst=True,
            tzinfos=COMMON_TIMEZONES,
        )
        return force_utc(dt)
    except (ValueError, parser.ParserError, TypeError) as e:
        logger.debug("Failed to parse date string '%s': %s", date_string, e)
        return None


def parse_date_with_comparison(
    date_string: Optional[str],
    parsed_tuple: Optional[time.struct_time],
    locale: Optional[str] = None,
) -> Optional[datetime]:
    """
    Parse a date by comparing feedparser's parsed result with dateutil's parsing.

    This function compares feedparser's struct_time (from *_parsed fields) with
    dateutil's parsing of the raw date string. If they differ, dateutil's result
    is preferred as it handles locale and edge cases better.

    :param date_string: Raw date string (e.g., from 'published', 'updated' fields)
    :param parsed_tuple: Feedparser's parsed struct_time (from '*_parsed' fields)
    :param locale: Optional locale string for date parsing (e.g., 'en_US', 'fr_FR')
    :return: tz-aware UTC datetime, or None if parsing fails
    """
    # Parse using dateutil
    dateutil_result = None
    if date_string:
        # If locale is provided, configure dateutil parser settings
        # Note: dateutil doesn't directly support locale, but we can use it for logging
        if locale:
            logger.debug("Parsing date with locale context: %s", locale)

        dateutil_result = datestring_to_utc_datetime(date_string)

    # Convert feedparser's struct_time to datetime if available
    feedparser_result = None
    if parsed_tuple:
        try:
            # Convert struct_time to UTC datetime
            # struct_time is always in the feed's specified timezone or UTC
            dt = datetime(*parsed_tuple[:6])
            feedparser_result = force_utc(dt)
        except (ValueError, TypeError, OverflowError) as e:
            logger.debug("Failed to convert struct_time to datetime: %s", e)

    # Compare results
    if dateutil_result and feedparser_result:
        # Allow 1 second difference for rounding/precision issues
        time_diff = abs((dateutil_result - feedparser_result).total_seconds())
        if time_diff > 1:
            logger.debug(
                "Date parsing difference detected: feedparser=%s, dateutil=%s (diff=%ss). Using dateutil result.",
                feedparser_result,
                dateutil_result,
                time_diff,
            )
            return dateutil_result
        # If they're essentially the same, use feedparser result (it's pre-parsed)
        return feedparser_result

    # If only one succeeded, use whichever worked
    if dateutil_result:
        return dateutil_result
    if feedparser_result:
        return feedparser_result

    return None


def create_content_type(parse_type: str, encoding: str, content_type: str) -> str:
    """
    Create the actual content type of the feed.

    :param parse_type: How the feed is being parsed. XML or JSON
    :param encoding: Charset encoding of the response
    :param content_type: Content-Type header string of the response
    :return: Content-Type string
    """

    content_type = content_type.lower()
    if parse_type == ParseTypes.JSON and ParseTypes.JSON not in content_type:
        content_type = "application/json"
    elif parse_type == ParseTypes.XML and ParseTypes.XML not in content_type:
        content_type = "application/xml"

    return f"{content_type}; charset={encoding.lower()}"
