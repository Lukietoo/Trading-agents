# Read-only Alpaca market data: bars, snapshots, and the two screener sweeps.
#
# NO ORDER PLACEMENT. Not here, not anywhere else in app/data/. Only the
# executor module places orders, and it does not exist yet.
#
# This client *wraps* app/alpaca.py rather than absorbing it. HttpAlpacaClient
# already serves the dashboard's /api/snapshot and the AlpacaClient protocol is
# the seam the existing tests fake; get_account() delegates through that seam
# instead of reimplementing account access alongside it.

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Final, Literal

import httpx
import pandas as pd

from app.alpaca import AlpacaAccount, AlpacaClient
from app.data.cache import Cache, CacheKey, historical_ttl
from app.data.http import DEFAULT_RETRY_POLICY, RetryPolicy, get_json

DEFAULT_DATA_BASE_URL: Final = "https://data.alpaca.markets"

# The free feed is real-time IEX. Its trailing window is sparse, so every bar
# request stops short of the present by this much. See clamp_end.
FREE_FEED_DELAY: Final = timedelta(minutes=15)

# Alpaca's bar fields are single letters on the wire. The DataFrame uses names,
# because an indicator reading `df["c"]` is a bug waiting to be misread.
BAR_COLUMNS: Final = {
    "o": "open",
    "h": "high",
    "l": "low",
    "c": "close",
    "v": "volume",
    "n": "trade_count",
    "vw": "vwap",
}

Timeframe = Literal["1Min", "5Min", "15Min", "1Hour", "1Day"]


@dataclass(frozen=True)
class Bar:
    """One OHLCV bar. Present for the snapshot models; bar *series* are
    DataFrames, because that is what the indicators consume."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int
    vwap: float

    @classmethod
    def from_wire(cls, raw: dict[str, Any]) -> "Bar":
        return cls(
            timestamp=_parse_timestamp(raw["t"]),
            open=raw["o"],
            high=raw["h"],
            low=raw["l"],
            close=raw["c"],
            volume=raw["v"],
            trade_count=raw["n"],
            vwap=raw["vw"],
        )


@dataclass(frozen=True)
class Snapshot:
    ticker: str
    daily_bar: Bar | None
    previous_daily_bar: Bar | None
    minute_bar: Bar | None
    latest_trade_price: float | None
    latest_trade_at: datetime | None

    @property
    def gap_pct(self) -> float | None:
        """Today's open against yesterday's close, in percent.

        None when either bar is missing rather than 0.0 — "no gap" and "we do
        not know" are different answers, and a screener must not confuse them.
        """
        if self.daily_bar is None or self.previous_daily_bar is None:
            return None
        previous_close = self.previous_daily_bar.close
        if previous_close == 0:
            return None
        return round((self.daily_bar.open - previous_close) / previous_close * 100, 2)


@dataclass(frozen=True)
class MostActive:
    """A row of the most-actives sweep. Deliberately vendor-shaped: turning one
    into a domain Candidate is Phase 2's job, and needs Trigger values this
    layer has no business inventing."""

    symbol: str
    volume: int
    trade_count: int


@dataclass(frozen=True)
class Mover:
    symbol: str
    price: float
    change: float
    percent_change: float


@dataclass(frozen=True)
class Movers:
    gainers: list[Mover] = field(default_factory=list)
    losers: list[Mover] = field(default_factory=list)


def _parse_timestamp(raw: str) -> datetime:
    # Alpaca sends RFC-3339 with a Z suffix and sub-second precision that
    # fromisoformat handles natively on 3.11+.
    return datetime.fromisoformat(raw)


def _as_datetime(value: date | datetime, *, end_of_day: bool) -> datetime:
    """Normalise a date to an instant.

    A bare `date` used as an end bound means "through the close of that day".
    Passing it as midnight would silently drop that day's bar, whose timestamp
    is the session open — the kind of off-by-one that shortens every window by
    one day without ever erroring.
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    moment = time.max if end_of_day else time.min
    return datetime.combine(value, moment, tzinfo=UTC)


def clamp_end(
    end: date | datetime | None,
    *,
    now: datetime,
    delay: timedelta = FREE_FEED_DELAY,
) -> datetime:
    """Pull a bar window's end back out of the free feed's blind spot.

    On the free IEX feed the trailing ~15 minutes of bars are sparse or absent.
    A window ending "now" therefore comes back short or empty, which reads as
    "the API returned nothing" rather than as a feed limitation — per the spec,
    the single most common source of that confusion.

    `end=None` means now. An end already in the past is left alone; only the
    part of a window that reaches into the blind spot is trimmed.
    """
    ceiling = now - delay
    if end is None:
        return ceiling
    return min(_as_datetime(end, end_of_day=True), ceiling)


def bars_to_frame(raw_bars: list[dict[str, Any]]) -> pd.DataFrame:
    """Alpaca's bar list to an indicator-ready DataFrame.

    A UTC DatetimeIndex, ascending, float64 prices. An empty response yields an
    empty frame *with these columns*, so downstream code branches on `.empty`
    rather than on a KeyError. Nothing is invented to fill a gap.
    """
    frame = pd.DataFrame(raw_bars, columns=["t", *BAR_COLUMNS])
    index = pd.DatetimeIndex(
        pd.to_datetime(frame["t"], utc=True, format="ISO8601"), name="timestamp"
    )
    frame = (
        frame.drop(columns="t").rename(columns=BAR_COLUMNS).set_index(index).sort_index()
    )
    for column in ("open", "high", "low", "close", "volume", "vwap"):
        frame[column] = frame[column].astype("float64")
    frame["trade_count"] = frame["trade_count"].astype("int64")
    return frame


class AlpacaDataClient:
    """Market data. Composes an AlpacaClient for account state."""

    def __init__(
        self,
        *,
        key_id: str,
        secret_key: str,
        account_client: AlpacaClient,
        cache: Cache,
        data_base_url: str = DEFAULT_DATA_BASE_URL,
        feed: str = "iex",
        transport: httpx.AsyncBaseTransport | None = None,
        policy: RetryPolicy = DEFAULT_RETRY_POLICY,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._base_url = data_base_url.rstrip("/").removesuffix("/v2")
        self._headers = {
            "APCA-API-KEY-ID": key_id,
            "APCA-API-SECRET-KEY": secret_key,
        }
        self._account_client = account_client
        self._cache = cache
        self._feed = feed
        self._transport = transport
        self._policy = policy
        self._now = now

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers=self._headers, transport=self._transport, timeout=30.0
        )

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        async with self._client() as http:
            return await get_json(
                http,
                f"{self._base_url}{path}",
                params=params,
                policy=self._policy,
                source="alpaca",
            )

    async def get_account(self) -> AlpacaAccount:
        """Delegated to app/alpaca.py — the dashboard's client already does
        this, and two implementations of account state would drift."""
        return await self._account_client.get_account()

    async def get_bars(
        self,
        ticker: str,
        start: date | datetime,
        end: date | datetime | None = None,
        timeframe: Timeframe = "1Day",
    ) -> pd.DataFrame:
        """Daily (or intraday) bars as a DataFrame.

        `end=None` means "as recent as the free feed can be trusted for" — see
        clamp_end. Cached permanently once the window has closed, since a
        completed session's bars cannot change.
        """
        now = self._now()
        start_at = _as_datetime(start, end_of_day=False)
        end_at = clamp_end(end, now=now)

        key = CacheKey(
            source="alpaca",
            method="bars",
            ticker=ticker,
            params={
                "start": start_at.isoformat(),
                "end": end_at.isoformat(),
                "timeframe": timeframe,
                "feed": self._feed,
            },
        )

        async def load() -> list[dict[str, Any]]:
            return await self._fetch_all_bars(ticker, start_at, end_at, timeframe)

        raw = await self._cache.fetch(
            key,
            ttl=historical_ttl(end_at.date(), today=now.date()),
            load=load,
        )
        return bars_to_frame(raw)

    async def _fetch_all_bars(
        self, ticker: str, start: datetime, end: datetime, timeframe: Timeframe
    ) -> list[dict[str, Any]]:
        """Follow next_page_token to the end.

        Stopping at the first page would silently truncate any window longer
        than a page — the numbers would still look plausible, which is exactly
        what makes it dangerous.
        """
        collected: list[dict[str, Any]] = []
        page_token: str | None = None

        while True:
            params: dict[str, Any] = {
                "symbols": ticker,
                "timeframe": timeframe,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "feed": self._feed,
                "limit": 10_000,
            }
            if page_token:
                params["page_token"] = page_token

            body = await self._get("/v2/stocks/bars", params)
            collected.extend((body.get("bars") or {}).get(ticker) or [])

            page_token = body.get("next_page_token")
            if not page_token:
                return collected

    async def get_snapshot(self, ticker: str) -> Snapshot:
        """Current state for one ticker. Not cached — a snapshot is a quote,
        and a cached quote is a wrong quote."""
        body = await self._get(
            "/v2/stocks/snapshots", {"symbols": ticker, "feed": self._feed}
        )
        raw = body.get(ticker) or {}

        def bar(field_name: str) -> Bar | None:
            value = raw.get(field_name)
            return Bar.from_wire(value) if value else None

        trade = raw.get("latestTrade") or {}
        return Snapshot(
            ticker=ticker,
            daily_bar=bar("dailyBar"),
            previous_daily_bar=bar("prevDailyBar"),
            minute_bar=bar("minuteBar"),
            latest_trade_price=trade.get("p"),
            latest_trade_at=_parse_timestamp(trade["t"]) if trade.get("t") else None,
        )

    async def get_most_actives(self, top: int = 20) -> list[MostActive]:
        """Highest-volume names. Not cached: a stale candidate list would send
        the agents at yesterday's movers."""
        body = await self._get(
            "/v1beta1/screener/stocks/most-actives", {"top": top}
        )
        return [
            MostActive(
                symbol=row["symbol"],
                volume=row["volume"],
                trade_count=row["trade_count"],
            )
            for row in body.get("most_actives") or []
        ]

    async def get_market_movers(self, top: int = 20) -> Movers:
        body = await self._get("/v1beta1/screener/stocks/movers", {"top": top})

        def movers(key: str) -> list[Mover]:
            return [
                Mover(
                    symbol=row["symbol"],
                    price=row["price"],
                    change=row["change"],
                    percent_change=row["percent_change"],
                )
                for row in body.get(key) or []
            ]

        return Movers(gainers=movers("gainers"), losers=movers("losers"))
