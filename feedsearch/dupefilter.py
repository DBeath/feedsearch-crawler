from w3lib.url import url_query_cleaner
from yarl import URL

from crawler import DuplicateFilter, Request, request_fingerprint


class NoQueryDupeFilter(DuplicateFilter):
    valid_keys = ["feedformat", "feed", "rss", "atom", "jsonfeed"]

    def request_fingerprint(self, request: Request):
        query = request.url.query
        if any(key in query for key in self.valid_keys):
            return request_fingerprint(request)

        new_url = url_query_cleaner(str(request.url))
        request.url = URL(new_url)
        return request_fingerprint(request)
