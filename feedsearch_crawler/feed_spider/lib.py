from typing import Union, List

from yarl import URL
from datetime import datetime
from dateutil import tz, parser


def get_site_root(url: Union[str, URL]) -> str:
    """
    Find the root domain of a url
    """
    if isinstance(url, URL):
        return url.host
    return URL(url).host


def create_allowed_domains(url: Union[str, URL]) -> List[str]:
    if isinstance(url, URL):
        return [url.host]
    return [URL(url).host]


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
