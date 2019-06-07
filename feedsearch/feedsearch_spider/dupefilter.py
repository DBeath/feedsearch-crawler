from w3lib.url import url_query_cleaner
from yarl import URL

from feedsearch.crawler import DuplicateFilter


class NoQueryDupeFilter(DuplicateFilter):
    valid_keys = ["feedformat", "feed", "rss", "atom", "jsonfeed", "format"]

    def url_fingerprint(self, url: URL, method: str = "") -> str:
        query = url.query
        if any(key in query for key in self.valid_keys):
            return self.url_fingerprint_hash(url, method)

        new_url = URL(url_query_cleaner(str(url)))
        hash = self.url_fingerprint_hash(new_url, method)
        return hash
