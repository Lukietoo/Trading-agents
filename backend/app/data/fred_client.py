# FRED macro series.
#
# Two things about this feed that are easy to get wrong, both handled here:
#
# 1. A missing observation is the string "." — not null, not "". float(".")
#    raises, and a client that coerces it to 0.0 turns "the Treasury spread was
#    not published that day" into "the spread was zero", which is a real value
#    with the opposite meaning. Missing becomes NaN.
#
# 2. FRED serves *revisions*. CPI for a month is published weeks later and then
#    revised repeatedly, and a plain request returns today's revision of a
#    figure for any past date. That is look-ahead — CLAUDE.md's sixth hard rule
#    — so `as_of` exists to ask for the vintage as it stood on a given date.

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any, Final

import httpx
import pandas as pd

from app.data.cache import MACRO_TTL, NEVER_EXPIRES, Cache, CacheKey
from app.data.http import DEFAULT_RETRY_POLICY, RetryPolicy, get_json

DEFAULT_BASE_URL: Final = "https://api.stlouisfed.org/fred"

# FRED's marker for "no observation on this date".
MISSING: Final = "."

# The starting set from the spec. Named so a caller writes DFF rather than
# rediscovering the series id each time.
FED_FUNDS_RATE: Final = "DFF"
CPI: Final = "CPIAUCSL"
UNEMPLOYMENT: Final = "UNRATE"
YIELD_CURVE_10Y_2Y: Final = "T10Y2Y"

DEFAULT_SERIES: Final = (FED_FUNDS_RATE, CPI, UNEMPLOYMENT, YIELD_CURVE_10Y_2Y)


def observations_to_series(raw: dict[str, Any], series_id: str) -> pd.Series:
    """FRED's observation list to a float64 Series on a DatetimeIndex.

    Missing observations become NaN and keep their date rather than being
    dropped: a gap in a macro series is information, and silently compressing
    the index would misalign it against any other series.
    """
    observations = raw.get("observations") or []
    index = pd.DatetimeIndex(
        [pd.Timestamp(row["date"]) for row in observations], name="date"
    )
    values = [
        float("nan") if row.get("value") in (MISSING, None, "") else float(row["value"])
        for row in observations
    ]
    return pd.Series(values, index=index, name=series_id, dtype="float64").sort_index()


class FredClient:
    def __init__(
        self,
        *,
        api_key: str,
        cache: Cache,
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx.AsyncBaseTransport | None = None,
        policy: RetryPolicy = DEFAULT_RETRY_POLICY,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._api_key = api_key
        self._cache = cache
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._policy = policy
        self._now = now

    async def get_series(
        self,
        series_id: str,
        start: date,
        end: date,
        *,
        as_of: date | None = None,
    ) -> pd.Series:
        """One macro series over a date range.

        `as_of` pins the data to the revision that was public on that date.
        Leave it None for the current view, which is what a live pre-market run
        wants; set it in any backtest or evaluation path, where using today's
        revision of a figure for a past date is look-ahead.

        Cached aggressively: these series update monthly at most, and a pinned
        `as_of` view is immutable by construction, so it never expires.
        """
        params: dict[str, Any] = {
            "series_id": series_id,
            "file_type": "json",
            "observation_start": start.isoformat(),
            "observation_end": end.isoformat(),
        }
        if as_of is not None:
            # Both bounds set to the same day: "the vintage as published then".
            params["realtime_start"] = as_of.isoformat()
            params["realtime_end"] = as_of.isoformat()

        key = CacheKey(
            source="fred",
            method="series",
            params={**params, "as_of": as_of.isoformat() if as_of else None},
        )

        async def load() -> Any:
            # The key goes on the request but never into the cache key: it is a
            # credential, and the cache file is on disk.
            async with httpx.AsyncClient(transport=self._transport, timeout=30.0) as http:
                return await get_json(
                    http,
                    f"{self._base_url}/series/observations",
                    params={**params, "api_key": self._api_key},
                    policy=self._policy,
                    source="fred",
                )

        body = await self._cache.fetch(
            key,
            ttl=NEVER_EXPIRES if as_of is not None else MACRO_TTL,
            load=load,
        )
        return observations_to_series(body, series_id)
