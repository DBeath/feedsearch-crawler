from yarl import URL

from feedsearch_crawler.crawler import Item


class Favicon(Item):
    url: URL = None
    priority: int = 0
    rel: str = ""
    data_uri: str = ""
    resp_url: URL = None
    site_host: str = ""

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.url == other.url

    def __hash__(self):
        return hash(self.url)

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self.url)})"

    def matches_host(self, host: str, requires_data_uri: bool = False) -> bool:
        """
        Check that the Favicon site_host is a match for the host.

        :param host: domain host url string
        :param requires_data_uri: Whether the Favicon is required to have a data_uri
        :return: bool
        """
        return (
            self.url
            and self.site_host
            and self.site_host in host
            and (self.data_uri if requires_data_uri else True)
        )
