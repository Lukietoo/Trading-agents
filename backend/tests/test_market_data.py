# The MarketData facade: that it routes to the right client, computes the
# right windows, and can be built without touching .env or the network.

from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pandas as pd
import pytest

from app.alpaca import AlpacaAccount
from app.data import MarketData
from app.data.alpaca_client import AlpacaDataClient
from app.data.cache import Cache
from app.data.finnhub_client import FinnhubClient
from app.data.fred_client import UNEMPLOYMENT, FredClient
from app.data.http import RetryPolicy
from app.data.rate_limit import RateLimiter
from tests.fixtures import load

NOW = datetime(2026, 8, 9, 14, 30, tzinfo=UTC)


class Router:
    """Serves every fixture by URL fragment and records the requests."""

    ROUTES = {
        "/v2/stocks/bars": "alpaca_bars_aapl_1day",
        "/v2/stocks/snapshots": "alpaca_snapshot_aapl",
        "most-actives": "alpaca_most_actives",
        "movers": "alpaca_movers",
        "/stock/metric": "finnhub_metrics_aapl",
        "/company-news": "finnhub_company_news_aapl",
        "/calendar/earnings": "finnhub_earnings_calendar_aapl",
        "/stock/insider-transactions": "finnhub_insider_transactions_aapl",
        "/series/observations": "fred_unrate",
    }

    def __init__(self):
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        for fragment, fixture in self.ROUTES.items():
            if fragment in request.url.path:
                return httpx.Response(200, json=load(fixture))
        return httpx.Response(404, json={"message": f"no route for {request.url.path}"})

    def paths(self) -> list[str]:
        return [str(request.url.path) for request in self.requests]

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]


class FakeAccountClient:
    async def get_account(self) -> AlpacaAccount:
        return AlpacaAccount(equity=101_240.5, cash=24_000.0, last_equity=100_980.0)


@pytest.fixture
def router() -> Router:
    return Router()


@pytest.fixture
def market(tmp_path: Path, router: Router) -> MarketData:
    """A fully injected facade: no .env, no network, no real waiting."""
    transport = httpx.MockTransport(router)
    policy = RetryPolicy(attempts=2, base_delay=0, jitter=False)
    cache = Cache(tmp_path / "cache.sqlite3", now=lambda: NOW)

    return MarketData(
        cache=cache,
        now=lambda: NOW,
        alpaca=AlpacaDataClient(
            key_id="k",
            secret_key="s",
            account_client=FakeAccountClient(),
            cache=cache,
            transport=transport,
            policy=policy,
            now=lambda: NOW,
        ),
        finnhub=FinnhubClient(
            api_key="k",
            cache=cache,
            limiter=RateLimiter(1000, 60.0),
            transport=transport,
            policy=policy,
            now=lambda: NOW,
        ),
        fred=FredClient(
            api_key="k",
            cache=cache,
            transport=transport,
            policy=policy,
            now=lambda: NOW,
        ),
    )


# --- the acceptance criteria ------------------------------------------------


async def test_get_bars_returns_clean_data(market: MarketData, router: Router):
    frame = await market.get_bars("AAPL", 90)

    assert isinstance(frame, pd.DataFrame)
    assert not frame.empty
    assert list(frame.columns)[:4] == ["open", "high", "low", "close"]
    assert frame["close"].notna().all()
    assert frame.index.is_monotonic_increasing


async def test_the_second_call_hits_the_cache(market: MarketData, router: Router):
    first = await market.get_bars("AAPL", 90)
    second = await market.get_bars("AAPL", 90)

    assert len(router.requests) == 1
    pd.testing.assert_frame_equal(first, second)


async def test_get_fundamentals_returns_populated_fields(market: MarketData):
    fundamentals = await market.get_fundamentals("AAPL")

    assert fundamentals.is_populated
    assert fundamentals.pe_ttm is not None
    assert fundamentals.market_cap_millions is not None
    assert fundamentals.beta is not None


# --- windows ----------------------------------------------------------------


async def test_the_bars_lookback_is_calendar_days_from_today(market: MarketData, router: Router):
    await market.get_bars("AAPL", 90)

    start = datetime.fromisoformat(router.last.url.params.get("start"))
    assert start.date() == date(2026, 5, 11)  # 2026-08-09 minus 90 days


async def test_ninety_calendar_days_is_fewer_than_ninety_bars(market: MarketData):
    # The distinction the docstring makes, asserted: markets close at weekends,
    # so a caller who needs N bars must ask for more than N days.
    frame = await market.get_bars("AAPL", 90)

    assert len(frame) < 90


async def test_the_news_window_defaults_to_a_week(market: MarketData, router: Router):
    await market.get_company_news("AAPL")

    assert router.last.url.params.get("from") == "2026-08-02"
    assert router.last.url.params.get("to") == "2026-08-09"


async def test_the_earnings_window_reaches_both_directions(market: MarketData, router: Router):
    # A screener wants the next date; an evaluation pass wants the last one.
    await market.get_earnings_calendar("AAPL", calendar_days=120)

    assert router.last.url.params.get("from") == "2026-04-11"
    assert router.last.url.params.get("to") == "2026-12-07"


async def test_the_insider_window_defaults_to_six_months(market: MarketData, router: Router):
    await market.get_insider_transactions("AAPL")

    assert router.last.url.params.get("from") == "2026-02-10"


# --- routing ----------------------------------------------------------------


async def test_each_call_reaches_the_right_vendor(market: MarketData, router: Router):
    await market.get_bars("AAPL", 90)
    await market.get_fundamentals("AAPL")
    await market.get_macro_series(UNEMPLOYMENT)

    assert any("stocks/bars" in path for path in router.paths())
    assert any("stock/metric" in path for path in router.paths())
    assert any("series/observations" in path for path in router.paths())


async def test_snapshots_and_screener_sweeps_route_through(market: MarketData):
    snapshot = await market.get_snapshot("AAPL")
    actives = await market.get_most_actives(top=20)
    movers = await market.get_market_movers(top=20)

    assert snapshot.daily_bar is not None
    assert actives[0].symbol == "HCWC"
    assert movers.gainers and movers.losers


async def test_the_account_comes_from_the_composed_client(market: MarketData, router: Router):
    account = await market.get_account()

    assert account.equity == 101_240.5
    assert router.requests == []


async def test_news_earnings_and_insider_all_parse(market: MarketData):
    news = await market.get_company_news("AAPL")
    earnings = await market.get_earnings_calendar("AAPL")
    insider = await market.get_insider_transactions("AAPL")

    assert news and news[0].headline
    assert earnings and earnings[0].date
    assert insider and insider[0].name


async def test_a_macro_series_comes_back_indexed_by_date(market: MarketData):
    series = await market.get_macro_series(UNEMPLOYMENT)

    assert isinstance(series, pd.Series)
    assert isinstance(series.index, pd.DatetimeIndex)
    assert series.name == UNEMPLOYMENT


async def test_a_pinned_vintage_reaches_fred(market: MarketData, router: Router):
    await market.get_macro_series(UNEMPLOYMENT, as_of=date(2026, 3, 1))

    assert router.last.url.params.get("realtime_start") == "2026-03-01"


# --- indicators through the facade ------------------------------------------


async def test_bars_with_indicators_are_appended(market: MarketData):
    frame = await market.get_bars_with_indicators("AAPL", 90)

    assert "rsi_14" in frame.columns
    assert "macd_hist" in frame.columns
    assert "volume_vs_20d_avg" in frame.columns
    assert frame["rsi_14"].dropna().between(0, 100).all()


async def test_an_indicator_the_window_cannot_cover_is_nan_not_invented(market: MarketData):
    # 90 calendar days cannot support a 200-bar average, and the facade says so
    # rather than quietly shortening the window.
    frame = await market.get_bars_with_indicators("AAPL", 90)

    assert frame["sma_200"].isna().all()
    assert frame["sma_20"].notna().any()


# --- construction -----------------------------------------------------------


def test_a_fully_injected_facade_never_reads_the_env(market: MarketData, monkeypatch):
    # Every required key removed: constructing and using the injected facade
    # must still work, which is what keeps the suite independent of whichever
    # machine it runs on.
    for key in (
        "ALPACA_API_KEY_ID",
        "ALPACA_API_SECRET_KEY",
        "FINNHUB_API_KEY",
        "FRED_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    assert market.purge_expired_cache() == 0


async def test_nothing_downstream_needs_a_vendor_client(market: MarketData):
    # The point of the facade: a caller holding only MarketData can do the
    # whole job. If this list ever needs a vendor import to grow, the facade
    # has a gap.
    assert await market.get_bars("AAPL", 90) is not None
    assert await market.get_snapshot("AAPL") is not None
    assert await market.get_fundamentals("AAPL") is not None
    assert await market.get_company_news("AAPL") is not None
    assert await market.get_earnings_calendar("AAPL") is not None
    assert await market.get_insider_transactions("AAPL") is not None
    assert await market.get_macro_series(UNEMPLOYMENT) is not None
    assert await market.get_most_actives() is not None
    assert await market.get_market_movers() is not None
    assert await market.get_account() is not None
