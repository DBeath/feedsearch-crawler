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