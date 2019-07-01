from w3lib.url import url_query_cleaner
from yarl import URL

from feedsearch_crawler.crawler import DuplicateFilter


class NoQueryDupeFilter(DuplicateFilter):
    valid_keys = ["feedformat", "feed", "rss", "atom", "jsonfeed", "format"]

    def parse_url(self, url: URL) -> str:
        if any(key in url.query for key in self.valid_keys):
            return str(url)

        return url_query_cleaner(str(url))
