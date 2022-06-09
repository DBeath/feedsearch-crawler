import cgi
from datetime import datetime
from typing import Union, List

from dateutil import tz, parser
from yarl import URL


class ParseTypes:
    JSON = "json"
    XML = "xml"


def parse_header_links(value):
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


def force_utc(dt: datetime) -> datetime:
    """
    Change a datetime to UTC, and convert naive datetimes to tz-aware UTC.

    :param dt: datetime to change to UTC
    :return: tz-aware UTC datetime
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.tzutc())
    return dt.astimezone(tz.tzutc())


def datestring_to_utc_datetime(date_string: str) -> datetime:
    """
    Convert a date string to a tz-aware UTC datetime.

    :param date_string: A datetime as a string in almost any format.
    :return: tz-aware UTC datetime
    """
    dt = parser.parse(date_string)
    return force_utc(dt)


def create_content_type(parse_type: str, encoding: str, content_type: str) -> str:
    """
    Create the actual content type of the feed.

    :param parse_type: How the feed is being parsed. XML or JSON
    :param encoding: Charset encoding of the response
    :param content_type: Content-Type header string of the response
    :return: Content-Type string
    """
    ctype, pdict = cgi.parse_header(content_type)

    if parse_type == ParseTypes.JSON and ParseTypes.JSON not in ctype.lower():
        ctype = "application/json"
    elif parse_type == ParseTypes.XML and ParseTypes.XML not in ctype.lower():
        ctype = "application/xml"

    return f"{ctype}; charset={encoding}".lower()
