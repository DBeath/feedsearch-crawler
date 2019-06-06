from typing import Union, List

from yarl import URL


def get_site_root(url: Union[str, URL]) -> str:
    """
    Find the root domain of a url
    """
    if isinstance(url, URL):
        return url.host
    return URL(url).host


def create_start_urls(url: Union[str, URL]) -> List[str]:
    if isinstance(url, URL):
        origin = url.origin()
    else:
        origin = URL(url).origin()

    return [url, origin, str(origin.join(URL("/about")))]


def create_allowed_domains(url: Union[str, URL]) -> List[str]:
    if isinstance(url, URL):
        return [url.host]
    return [URL(url).host]


def query_contains_comments(url: Union[str, URL]) -> bool:
    if isinstance(url, URL):
        query = url.query
    else:
        query = URL(url).query

    return any(key in query for key in ["comment", "comments", "post"])


def is_feedlike_url(url: Union[str, URL]) -> bool:
    if isinstance(url, URL):
        url = str(url)
    return any(map(url.lower().count, ["rss", "rdf", "xml", "atom", "feed", "json"]))


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
