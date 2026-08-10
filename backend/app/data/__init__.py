# The data layer's single entry point.
#
# Downstream code imports MarketData and nothing else from here. No screener,
# agent or evaluation module should ever import finnhub_client or fred_client
# directly — swapping a vendor should mean editing this file, not hunting
# through every caller.
#
# Everything read-only. There is no order-placement path in this package.

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Final

import pandas as pd

from app.alpaca import AlpacaAccount, AlpacaClient, HttpAlpacaClient
from app.config import Config, load_config
from app.data import indicators
from app.data.alpaca_client import (
    AlpacaDataClient,
    MostActive,
    Movers,
    Snapshot,
    Timeframe,
)
from app.data.cache import Cache
from app.data.finnhub_client import (
    EarningsEvent,
    FinnhubClient,
    Fundamentals,
    InsiderTx,
    NewsItem,
)
from app.data.fred_client import DEFAULT_SERIES, FredClient
from app.data.http import UpstreamError

__all__ = [
    "DEFAULT_SERIES",
    "AlpacaAccount",
    "EarningsEvent",
    "Fundamentals",
    "InsiderTx",
    "MarketData",
    "MostActive",
    "Movers",
    "NewsItem",
    "Snapshot",
    "UpstreamError",
    "indicators",
]

# Default lookbacks, in CALENDAR days. Note the distinction: 90 calendar days
# is roughly 62 daily bars, because markets close at weekends and holidays. Any
# caller that needs N *bars* must ask for more calendar days than that —
# indicators with a 200-bar warm-up need roughly 290.
DEFAULT_BARS_LOOKBACK_DAYS: Final = 90
DEFAULT_NEWS_LOOKBACK_DAYS: Final = 7
DEFAULT_INSIDER_LOOKBACK_DAYS: Final = 180
DEFAULT_EARNINGS_WINDOW_DAYS: Final = 120
DEFAULT_MACRO_LOOKBACK_DAYS: Final = 730


class MarketData:
    """One interface to every market and fundamental source.

    Constructed with no arguments it reads the root .env and puts the cache
    where config says, so `MarketData()` works from a script or a REPL. Every
    collaborator is injectable, which is how the tests avoid both the network
    and the developer's own .env.
    """

    def __init__(
        self,
        *,
        config: Config | None = None,
        cache: Cache | None = None,
        alpaca: AlpacaDataClient | None = None,
        finnhub: FinnhubClient | None = None,
        fred: FredClient | None = None,
        account_client: AlpacaClient | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        # Config is only read if something actually needs it, so a fully
        # injected MarketData never touches .env.
        self._config = config
        self._now = now
        self._cache = cache or Cache(self._settings().data_cache_path)

        self._alpaca = alpaca or AlpacaDataClient(
            key_id=self._settings().alpaca_api_key_id,
            secret_key=self._settings().alpaca_api_secret_key,
            account_client=account_client
            or HttpAlpacaClient(
                base_url=self._settings().alpaca_paper_base_url,
                key_id=self._settings().alpaca_api_key_id,
                secret_key=self._settings().alpaca_api_secret_key,
            ),
            cache=self._cache,
            now=now,
        )
        self._finnhub = finnhub or FinnhubClient(
            api_key=self._settings().finnhub_api_key, cache=self._cache, now=now
        )
        self._fred = fred or FredClient(
            api_key=self._settings().fred_api_key, cache=self._cache, now=now
        )

    def _settings(self) -> Config:
        if self._config is None:
            self._config = load_config()
        return self._config

    def _window(self, days: int) -> tuple[date, date]:
        today = self._now().date()
        return today - timedelta(days=days), today

    # --- prices ---------------------------------------------------------

    async def get_bars(
        self,
        ticker: str,
        days: int = DEFAULT_BARS_LOOKBACK_DAYS,
        timeframe: Timeframe = "1Day",
    ) -> pd.DataFrame:
        """The last `days` CALENDAR days of bars.

        The end is clamped ~15 minutes into the past — see
        alpaca_client.clamp_end — so the trailing window is not sparse on the
        free feed.
        """
        start, _ = self._window(days)
        return await self._alpaca.get_bars(ticker, start=start, timeframe=timeframe)

    async def get_bars_with_indicators(
        self,
        ticker: str,
        days: int = DEFAULT_BARS_LOOKBACK_DAYS,
        timeframe: Timeframe = "1Day",
    ) -> pd.DataFrame:
        """Bars with every indicator appended.

        Indicators whose warm-up the window does not cover are NaN throughout;
        ask for more days rather than reading the NaN as a zero.
        """
        return indicators.add_indicators(await self.get_bars(ticker, days, timeframe))

    async def get_snapshot(self, ticker: str) -> Snapshot:
        """Current price state. Never cached."""
        return await self._alpaca.get_snapshot(ticker)

    async def get_account(self) -> AlpacaAccount:
        return await self._alpaca.get_account()

    # --- screener sweeps ------------------------------------------------

    async def get_most_actives(self, top: int = 20) -> list[MostActive]:
        return await self._alpaca.get_most_actives(top=top)

    async def get_market_movers(self, top: int = 20) -> Movers:
        return await self._alpaca.get_market_movers(top=top)

    # --- fundamentals and news ------------------------------------------

    async def get_fundamentals(self, ticker: str) -> Fundamentals:
        return await self._finnhub.get_fundamentals(ticker)

    async def get_company_news(
        self, ticker: str, days: int = DEFAULT_NEWS_LOOKBACK_DAYS
    ) -> list[NewsItem]:
        start, end = self._window(days)
        return await self._finnhub.get_company_news(ticker, start=start, end=end)

    async def get_earnings_calendar(
        self, ticker: str, days: int = DEFAULT_EARNINGS_WINDOW_DAYS
    ) -> list[EarningsEvent]:
        """Earnings `days` either side of today — past results and scheduled
        dates in one call, since a screener wants the next one and an
        evaluation pass wants the last."""
        today = self._now().date()
        return await self._finnhub.get_earnings_calendar(
            ticker, start=today - timedelta(days=days), end=today + timedelta(days=days)
        )

    async def get_insider_transactions(
        self, ticker: str, days: int = DEFAULT_INSIDER_LOOKBACK_DAYS
    ) -> list[InsiderTx]:
        start, end = self._window(days)
        return await self._finnhub.get_insider_transactions(ticker, start=start, end=end)

    # --- macro ----------------------------------------------------------

    async def get_macro_series(
        self,
        series_id: str,
        days: int = DEFAULT_MACRO_LOOKBACK_DAYS,
        *,
        as_of: date | None = None,
    ) -> pd.Series:
        """One FRED series. Pass `as_of` in any backtest or evaluation path:
        FRED revises, so the default view of a past date is look-ahead."""
        start, end = self._window(days)
        return await self._fred.get_series(series_id, start=start, end=end, as_of=as_of)

    # --- maintenance ----------------------------------------------------

    def purge_expired_cache(self) -> int:
        return self._cache.purge_expired()
