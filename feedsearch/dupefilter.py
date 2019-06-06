from w3lib.url import url_query_cleaner
from yarl import URL

from crawler import DuplicateFilter


class NoQueryDupeFilter(DuplicateFilter):
    valid_keys = ["feedformat", "feed", "rss", "atom", "jsonfeed"]

    def url_fingerprint(self, url: URL, method: str = "") -> str:
        query = url.query
        if any(key in query for key in self.valid_keys):
            return self.url_fingerprint_hash(url, method)

        url = URL(url_query_cleaner(str(url)))
        return self.url_fingerprint_hash(url, method)
