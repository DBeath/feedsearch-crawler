from typing import Any


def coerce_url(url: str, https: bool = False) -> str:
    """
    Coerce URL to valid format

    :param url: URL
    :param https: Force https if no scheme in url
    :return: str
    """
    url.strip()
    if url.startswith("feed://"):
        return f"http://{url[7:]}"
    for proto in ["http://", "https://"]:
        if url.startswith(proto):
            return url
    if https:
        return f"https://{url}"
    else:
        return f"http://{url}"


def to_bytes(text, encoding: str = "utf-8", errors: str = "strict"):
    """Return the binary representation of `text`. If `text`
    is already a bytes object, return it as-is."""
    if not text:
        return b""
    if isinstance(text, bytes):
        return text
    return text.encode(encoding, errors)


def to_string(item: Any, encoding: str = "utf-8", errors: str = "strict") -> str:
    if item is None:
        return ""
    if isinstance(item, bytes):
        return item.decode(encoding, errors)
    return str(item)
