# A sliding-window rate limiter.
#
# Finnhub's free tier allows 60 requests a minute. Retrying on 429 would also
# "work", but only by discovering the limit through failure on every run: the
# spec asks for a limiter that never exceeds it in the first place.
#
# Sliding window rather than fixed buckets. A fixed one-minute bucket permits
# 60 calls at 11:59:59 and 60 more at 12:00:00 — 120 inside one actual minute,
# which is exactly the burst the limit exists to prevent.

import asyncio
from collections import deque
from collections.abc import Callable, Coroutine
from time import monotonic
from typing import Any

# Leave a little headroom under the documented ceiling. The window is measured
# on our clock, and the server's differs by however long a request is in
# flight; spending the last request of the quota is not worth a 429.
FINNHUB_CALLS_PER_MINUTE = 55


class RateLimiter:
    """Admits at most `max_calls` in any `per`-second window.

    `acquire` returns when it is this caller's turn. Concurrent callers are
    serialised through a lock and admitted in order, so a burst of coroutines
    started by asyncio.gather cannot collectively overrun the limit — each one
    sees the calls the others already made.

    `now` and `sleep` are injectable so the limiter is testable without
    spending a real minute proving it waits.
    """

    def __init__(
        self,
        max_calls: int,
        per: float = 60.0,
        *,
        now: Callable[[], float] = monotonic,
        sleep: Callable[[float], Coroutine[Any, Any, None]] = asyncio.sleep,
    ):
        if max_calls < 1:
            raise ValueError("max_calls must be at least 1")
        self._max_calls = max_calls
        self._per = per
        self._now = now
        self._sleep = sleep
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = self._now()
                self._evict(before=now - self._per)

                if len(self._calls) < self._max_calls:
                    self._calls.append(now)
                    return

                # Wait exactly until the oldest call leaves the window, which
                # is the earliest instant another is permitted.
                await self._sleep(max(self._calls[0] + self._per - now, 0.0))

    def _evict(self, *, before: float) -> None:
        while self._calls and self._calls[0] <= before:
            self._calls.popleft()

    @property
    def calls_in_window(self) -> int:
        """Calls currently counted against the limit. Diagnostics only."""
        self._evict(before=self._now() - self._per)
        return len(self._calls)
