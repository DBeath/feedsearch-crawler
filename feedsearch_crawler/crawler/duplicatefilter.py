import hashlib

from w3lib.url import canonicalize_url
from yarl import URL

from feedsearch_crawler.crawler.lib import to_bytes
import asyncio
import copy


class DuplicateFilter:
    def __init__(self):
        self.fingerprints = dict()
        self._seen_lock = asyncio.Lock()

    async def url_seen(self, url: URL, method: str = "") -> bool:
        fp = self.url_fingerprint(url, method)
        async with self._seen_lock:
            if fp in self.fingerprints:
                return True
            self.fingerprints[fp] = copy.copy(url)
            return False

    def url_fingerprint(self, url: URL, method: str = "") -> str:
        return self.url_fingerprint_hash(url, method)

    @staticmethod
    def url_fingerprint_hash(url: URL, method: str = "") -> str:
        fp = hashlib.sha1()
        fp.update(to_bytes(canonicalize_url(str(url))))
        if method:
            fp.update(to_bytes(method))
        return fp.hexdigest()
