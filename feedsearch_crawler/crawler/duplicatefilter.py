import asyncio
import hashlib

from yarl import URL

from feedsearch_crawler.crawler.lib import to_bytes


class DuplicateFilter:
    """
    Filters duplicate URLs.
    """

    def __init__(self):
        # Dictionary whose keys are the hashed fingerprints of the URLs
        self.fingerprints = dict()
        # Locks the fingerprints dict when accessing keys.
        self._seen_lock = asyncio.Lock()

    async def url_seen(self, url: URL, method: str = "") -> bool:
        """
        Checks if the URL has already been seen, and adds the URL fingerprint if not.

        :param url: URL object
        :param method: Optional HTTP method to use for hashing
        :return: True if URL already seen
        """
        url_str: str = self.parse_url(url)
        fp = self.url_fingerprint_hash(url_str, method)
        async with self._seen_lock:
            if fp in self.fingerprints:
                return True
            self.fingerprints[fp] = url_str
            return False

    def parse_url(self, url: URL) -> str:
        """
        Parse the URL object to a string. Used for functionality such as filtering query strings.

        :param url: URL object
        :return: URL as string
        """
        return str(url)

    @staticmethod
    def url_fingerprint_hash(url: str, method: str = "") -> str:
        """
        Create a fingerprint hash of a URL string along with the method if provided.

        :param url: URL as string
        :param method: Optional HTTP method
        :return: Hashed string
        """
        fp = hashlib.sha1()
        fp.update(to_bytes(url))
        if method:
            fp.update(to_bytes(method))
        return fp.hexdigest()
