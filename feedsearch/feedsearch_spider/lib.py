from typing import Union, List

from yarl import URL


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
