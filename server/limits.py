"""Tiny in-memory rate limiter so public use cannot burn the free credits."""
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_calls: int, window_s: int = 3600):
        self.max_calls = max_calls
        self.window_s = window_s
        self._hits = defaultdict(deque)

    def check(self, key: str) -> int:
        """Return 0 if the call is allowed, else seconds to wait."""
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window_s:
            hits.popleft()
        if len(hits) >= self.max_calls:
            return max(1, int(self.window_s - (now - hits[0])))
        hits.append(now)
        return 0
