# Shared HTTP access for the data-source clients.
#
# "Rate limits are expected, not exceptional" (CLAUDE.md), so retry with
# backoff lives here rather than being written three times and drifting.
#
# Tests inject an httpx transport instead of patching this module, so the real
# URL building, query encoding and status handling all run under test. `sleep`
# is injectable for the same reason: a backoff test should assert on the delays
# requested, not spend them.

import asyncio
import random
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, Final

import httpx

# 429 is the rate limit; the 5xx set is transient server trouble. A 4xx other
# than 429 is our own bad request and retrying it just repeats the mistake.
RETRYABLE_STATUS: Final = frozenset({429, 500, 502, 503, 504})


class UpstreamError(Exception):
    """A data source failed and retrying did not help.

    Raised rather than returning an empty result: the pipeline must never treat
    "the API was down" as "there is no news about this ticker".
    """


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 4
    base_delay: float = 0.5
    max_delay: float = 8.0
    # Full jitter. Every client in a batch backing off on the identical
    # schedule is how a rate limit turns into a thundering herd.
    jitter: bool = True

    def delay_for(self, attempt: int, *, retry_after: float | None = None) -> float:
        """Seconds to wait before `attempt` (1-based).

        A Retry-After header wins over the computed backoff — the server knows
        when it will serve us and we should not argue with it.
        """
        if retry_after is not None:
            return min(retry_after, self.max_delay)
        delay = min(self.base_delay * 2 ** (attempt - 1), self.max_delay)
        return random.uniform(0, delay) if self.jitter else delay


# Frozen, so one shared instance is safe as a default and cannot be mutated by
# a caller into everyone else's policy.
DEFAULT_RETRY_POLICY: Final = RetryPolicy()


def _retry_after_seconds(response: httpx.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        # The header also allows an HTTP date. Rare on these APIs, and falling
        # back to computed backoff is safe, so we do not parse it.
        return None


async def get_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    sleep: Callable[[float], Coroutine[Any, Any, None]] = asyncio.sleep,
    source: str = "upstream",
) -> Any:
    """GET `url` and return decoded JSON, retrying transient failures.

    Raises `UpstreamError` when the attempts run out, or on a non-retryable
    error status. Never returns a partial or substituted result.
    """
    last: str = "no attempt was made"

    for attempt in range(1, policy.attempts + 1):
        retry_after: float | None = None

        try:
            response = await client.get(url, params=params)
        except httpx.RequestError as exc:
            # Connection reset, DNS failure, timeout: transient by nature.
            last = f"{type(exc).__name__}: {exc}"
        else:
            if response.status_code < 400:
                return response.json()

            if response.status_code not in RETRYABLE_STATUS:
                # Deliberately excludes the response body: it can echo query
                # parameters back, and FRED puts the API key in the query.
                raise UpstreamError(
                    f"{source} returned {response.status_code} for {url}. "
                    "Not retryable — this is a bad request, not a busy server."
                )

            last = f"HTTP {response.status_code}"
            retry_after = _retry_after_seconds(response)

        if attempt < policy.attempts:
            await sleep(policy.delay_for(attempt, retry_after=retry_after))

    raise UpstreamError(
        f"{source} failed after {policy.attempts} attempts for {url}. "
        f"Last failure: {last}."
    )
