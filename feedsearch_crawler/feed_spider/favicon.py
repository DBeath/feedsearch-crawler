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
