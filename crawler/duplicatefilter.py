from crawler.request import request_fingerprint, Request
import asyncio


class DuplicateFilter:
    def __init__(self):
        self.fingerprints = set()
        self.seen_lock = asyncio.Lock()

    async def request_seen(self, request) -> bool:
        fp = self._request_fingerprint(request)
        async with self.seen_lock:
            if fp in self.fingerprints:
                return True
            self.fingerprints.add(fp)
            return False

    def _request_fingerprint(self, request: Request) -> str:
        return request_fingerprint(request)
