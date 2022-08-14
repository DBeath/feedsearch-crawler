from w3lib.url import url_query_cleaner, canonicalize_url
from yarl import URL

from feedsearch_crawler.crawler import DuplicateFilter


class NoQueryDupeFilter(DuplicateFilter):
    valid_keys = ["feedformat", "feed", "rss", "atom", "jsonfeed", "format", "podcast"]

    def _parse_url(self, url: URL) -> str:
        # Keep the query strings if they might be feed strings.
        # Wikipedia for example uses query strings to differentiate feeds.
        if any(key in url.query for key in self.valid_keys):
            return canonicalize_url(str(url))

        # Canonicalizing the URL is about 4x slower, but worth it to prevent duplicate requests.
        return canonicalize_url(url_query_cleaner(str(url)))
