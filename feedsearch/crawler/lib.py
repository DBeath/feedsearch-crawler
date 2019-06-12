from typing import Any, Union, Dict
from yarl import URL


def coerce_url(url: Union[URL, str], https: bool = False) -> URL:
    """
    Coerce URL to valid format

    :param url: URL
    :param https: Force https if no scheme in url
    :return: str
    """
    if isinstance(url, str):
        url = URL(url)

    scheme = "https" if https else "http"

    if not url.is_absolute():
        url_string = str(url)
        split = url_string.split("/", 1)
        url = URL.build(scheme=scheme, host=split[0])
        if len(split) > 1:
            url = url.with_path(split[1])

    return url


def to_bytes(text, encoding: str = "utf-8", errors: str = "strict"):
    """Return the binary representation of `text`. If `text`
    is already a bytes object, return it as-is."""
    if not text:
        return b""
    if isinstance(text, bytes):
        return text
    return text.encode(encoding, errors)


def to_string(item: Any, encoding: str = "utf-8", errors: str = "strict") -> str:
    """
    Return the string representation of 'item'.
    """
    if item is None:
        return ""
    if isinstance(item, bytes):
        return item.decode(encoding, errors)
    return str(item)


def case_insensitive_key(key: str, dictionary: Dict) -> bool:
    """
    Check if a case-insensitive key is in a dictionary.
    """
    k = key.lower()
    for key in dictionary.keys():
        if key.lower() == k:
            return True
