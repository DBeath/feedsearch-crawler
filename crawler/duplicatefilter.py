from crawler.request import request_fingerprint, Request
import asyncio
import copy


class DuplicateFilter:
    def __init__(self):
        self.fingerprints = dict()
        self.seen_lock = asyncio.Lock()

    async def request_seen(self, request) -> bool:
        fp = self.request_fingerprint(request)
        async with self.seen_lock:
            if fp in self.fingerprints:
                return True
            self.fingerprints[fp] = copy.copy(request.url)
            return False

    def request_fingerprint(self, request: Request) -> str:
        return request_fingerprint(request)
