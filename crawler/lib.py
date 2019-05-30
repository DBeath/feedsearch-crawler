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


def to_bytes(text, encoding=None, errors="strict"):
    """Return the binary representation of `text`. If `text`
    is already a bytes object, return it as-is."""
    if isinstance(text, bytes):
        return text
    if encoding is None:
        encoding = "utf-8"
    return text.encode(encoding, errors)
