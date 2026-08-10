# Finnhub client, driven by the recorded fixtures through an httpx transport.

from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest

from app.data.cache import Cache
from app.data.finnhub_client import FinnhubClient, Fundamentals
from app.data.http import RetryPolicy, UpstreamError
from app.data.rate_limit import RateLimiter
from tests.fixtures import load

NOW = datetime(2026, 8, 9, 14, 30, tzinfo=UTC)
WINDOW = {"start": date(2026, 8, 2), "end": date(2026, 8, 9)}


class Recorder:
    def __init__(self, routes: dict[str, object], status: int = 200):
        self.routes = routes
        self.status = status
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        for fragment, body in self.routes.items():
            if fragment in request.url.path:
                return httpx.Response(self.status, json=body)
        return httpx.Response(404, json={"message": "no route"})

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]


class NeverWaits(RateLimiter):
    """A limiter that records rather than waits, so client tests measure the
    client. The limiter's own behaviour is covered in test_rate_limit.py."""

    def __init__(self):
        self.acquisitions = 0
        super().__init__(60, 60.0)

    async def acquire(self) -> None:
        self.acquisitions += 1


@pytest.fixture
def cache(tmp_path: Path) -> Cache:
    return Cache(tmp_path / "cache.sqlite3", now=lambda: NOW)


@pytest.fixture
def limiter() -> NeverWaits:
    return NeverWaits()


def build_client(recorder: Recorder, cache: Cache, limiter: RateLimiter) -> FinnhubClient:
    return FinnhubClient(
        api_key="test-token",
        cache=cache,
        limiter=limiter,
        transport=httpx.MockTransport(recorder),
        policy=RetryPolicy(attempts=3, base_delay=0, jitter=False),
        now=lambda: NOW,
    )


# --- fundamentals ------------------------------------------------------------


async def test_fundamentals_lift_the_named_metrics(cache, limiter):
    recorder = Recorder({"/stock/metric": load("finnhub_metrics_aapl")})
    client = build_client(recorder, cache, limiter)

    fundamentals = await client.get_fundamentals("AAPL")

    assert fundamentals.ticker == "AAPL"
    assert fundamentals.pe_ttm == 35.4673
    assert fundamentals.price_to_book == 42.5297
    assert fundamentals.beta == pytest.approx(1.0813427)
    assert fundamentals.gross_margin_ttm == 48.65
    assert fundamentals.operating_margin_ttm == 33.17
    assert fundamentals.net_margin_ttm == 27.62
    assert fundamentals.week52_high == 344.5699
    assert fundamentals.week52_low == 216.58
    assert fundamentals.is_populated


async def test_market_cap_is_millions_and_says_so(cache, limiter):
    # The units gotcha: AAPL is a ~$4.5T company reported as ~4_572_794.
    recorder = Recorder({"/stock/metric": load("finnhub_metrics_aapl")})
    client = build_client(recorder, cache, limiter)

    fundamentals = await client.get_fundamentals("AAPL")

    assert fundamentals.market_cap_millions == pytest.approx(4_572_794.5)
    assert fundamentals.market_cap_millions * 1e6 > 4e12


async def test_the_untouched_metrics_are_still_reachable(cache, limiter):
    # 133 fields arrive; naming 16 must not throw the rest away.
    recorder = Recorder({"/stock/metric": load("finnhub_metrics_aapl")})
    client = build_client(recorder, cache, limiter)

    fundamentals = await client.get_fundamentals("AAPL")

    assert fundamentals.raw["dividendGrowthRate5Y"] == 4.95
    assert len(fundamentals.raw) > 100


def test_an_absent_metric_is_none_not_zero():
    # An agent told a margin is 0 reasons very differently from one told the
    # figure is unavailable.
    fundamentals = Fundamentals.from_wire("XYZ", {"metric": {"peTTM": None, "beta": 1.2}})

    assert fundamentals.pe_ttm is None
    assert fundamentals.beta == 1.2


def test_a_non_numeric_metric_is_none():
    # Finnhub also uses "" and "n/a" in places.
    fundamentals = Fundamentals.from_wire("XYZ", {"metric": {"peTTM": "", "pb": "n/a"}})

    assert fundamentals.pe_ttm is None
    assert fundamentals.price_to_book is None


async def test_an_unknown_ticker_is_distinguishable_from_a_sparse_one(cache, limiter):
    # Finnhub answers 200 with an empty body for a symbol it does not know,
    # so is_populated is the only way to tell the two apart.
    recorder = Recorder({"/stock/metric": {"metric": {}, "symbol": "NOSUCH"}})
    client = build_client(recorder, cache, limiter)

    fundamentals = await client.get_fundamentals("NOSUCH")

    assert fundamentals.is_populated is False
    assert fundamentals.pe_ttm is None


# --- news --------------------------------------------------------------------


async def test_news_parses_and_orders_newest_first(cache, limiter):
    recorder = Recorder({"/company-news": load("finnhub_company_news_aapl")})
    client = build_client(recorder, cache, limiter)

    news = await client.get_company_news("AAPL", **WINDOW)

    assert len(news) == 10
    assert news[0].headline
    assert news[0].url.startswith("http")
    assert [item.published_at for item in news] == sorted(
        (item.published_at for item in news), reverse=True
    )


async def test_a_news_timestamp_is_epoch_seconds_turned_utc(cache, limiter):
    recorder = Recorder({"/company-news": load("finnhub_company_news_aapl")})
    client = build_client(recorder, cache, limiter)

    news = await client.get_company_news("AAPL", **WINDOW)

    assert news[0].published_at.tzinfo is UTC
    assert news[0].published_at.year == 2026


async def test_the_news_window_is_sent_as_from_and_to(cache, limiter):
    recorder = Recorder({"/company-news": load("finnhub_company_news_aapl")})
    client = build_client(recorder, cache, limiter)

    await client.get_company_news("AAPL", **WINDOW)

    assert recorder.last.url.params.get("from") == "2026-08-02"
    assert recorder.last.url.params.get("to") == "2026-08-09"


async def test_no_news_is_an_empty_list(cache, limiter):
    recorder = Recorder({"/company-news": []})
    client = build_client(recorder, cache, limiter)

    assert await client.get_company_news("QUIET", **WINDOW) == []


# --- earnings ----------------------------------------------------------------


async def test_the_earnings_calendar_parses_chronologically(cache, limiter):
    recorder = Recorder({"/calendar/earnings": load("finnhub_earnings_calendar_aapl")})
    client = build_client(recorder, cache, limiter)

    events = await client.get_earnings_calendar("AAPL", start=date(2026, 2, 9), end=date(2027, 2, 9))

    assert [event.date for event in events] == sorted(event.date for event in events)
    assert all(isinstance(event.date, date) for event in events)


async def test_a_future_earnings_date_has_an_estimate_but_no_actual(cache, limiter):
    # This is what "earnings within N days" screens on, and treating a null
    # actual as 0.0 would invent a catastrophic miss.
    recorder = Recorder({"/calendar/earnings": load("finnhub_earnings_calendar_aapl")})
    client = build_client(recorder, cache, limiter)

    events = await client.get_earnings_calendar("AAPL", start=date(2026, 2, 9), end=date(2027, 2, 9))
    upcoming = [event for event in events if event.date > date(2026, 8, 9)]

    assert upcoming
    assert all(event.eps_actual is None for event in upcoming)
    assert all(not event.is_reported for event in upcoming)
    assert any(event.eps_estimate is not None for event in upcoming)


async def test_a_past_earnings_date_is_reported(cache, limiter):
    recorder = Recorder({"/calendar/earnings": load("finnhub_earnings_calendar_aapl")})
    client = build_client(recorder, cache, limiter)

    events = await client.get_earnings_calendar("AAPL", start=date(2026, 2, 9), end=date(2027, 2, 9))
    past = [event for event in events if event.date == date(2026, 7, 30)]

    assert past[0].is_reported
    assert past[0].eps_actual == 1.91
    assert past[0].hour == "amc"


# --- insider -----------------------------------------------------------------


async def test_insider_transactions_parse_newest_filing_first(cache, limiter):
    recorder = Recorder(
        {"/stock/insider-transactions": load("finnhub_insider_transactions_aapl")}
    )
    client = build_client(recorder, cache, limiter)

    transactions = await client.get_insider_transactions(
        "AAPL", start=date(2026, 2, 9), end=date(2026, 8, 9)
    )

    assert transactions
    filings = [tx.filing_date for tx in transactions]
    assert filings == sorted(filings, reverse=True)


async def test_a_disposal_keeps_its_sign(cache, limiter):
    recorder = Recorder(
        {"/stock/insider-transactions": load("finnhub_insider_transactions_aapl")}
    )
    client = build_client(recorder, cache, limiter)

    transactions = await client.get_insider_transactions(
        "AAPL", start=date(2026, 2, 9), end=date(2026, 8, 9)
    )

    assert any(tx.change < 0 for tx in transactions)


async def test_gifts_and_grants_are_not_open_market_trades(cache, limiter):
    # The classic misreading: counting a grant or a gift as an insider
    # purchase. Only P and S carry a price signal.
    recorder = Recorder(
        {"/stock/insider-transactions": load("finnhub_insider_transactions_aapl")}
    )
    client = build_client(recorder, cache, limiter)

    transactions = await client.get_insider_transactions(
        "AAPL", start=date(2026, 2, 9), end=date(2026, 8, 9)
    )
    gifts = [tx for tx in transactions if tx.transaction_code == "G"]

    assert gifts
    assert all(not tx.is_open_market for tx in gifts)
    assert all(tx.is_open_market for tx in transactions if tx.transaction_code == "S")


# --- quota -------------------------------------------------------------------


async def test_every_request_passes_the_limiter(cache, limiter):
    recorder = Recorder(
        {
            "/stock/metric": load("finnhub_metrics_aapl"),
            "/company-news": load("finnhub_company_news_aapl"),
        }
    )
    client = build_client(recorder, cache, limiter)

    await client.get_fundamentals("AAPL")
    await client.get_company_news("AAPL", **WINDOW)

    assert limiter.acquisitions == 2


async def test_a_cache_hit_spends_no_quota(cache, limiter):
    # Quota is gated on the request, not the lookup: a cache hit costs Finnhub
    # nothing and must not count against the minute.
    recorder = Recorder({"/stock/metric": load("finnhub_metrics_aapl")})
    client = build_client(recorder, cache, limiter)

    await client.get_fundamentals("AAPL")
    await client.get_fundamentals("AAPL")

    assert len(recorder.requests) == 1
    assert limiter.acquisitions == 1


async def test_a_real_limiter_holds_a_burst_under_the_ceiling(cache):
    # End to end through the client: 8 tickers against a limit of 3 a minute.
    # The assertion is the property that matters — no minute-long window ever
    # contains a fourth request — rather than a count of sleeps, which depends
    # on how a mock transport bunches identical timestamps.
    slept: list[float] = []
    clock = {"now": 0.0}
    sent_at: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)
        clock["now"] += seconds

    body = load("finnhub_metrics_aapl")

    def timestamped(request: httpx.Request) -> httpx.Response:
        sent_at.append(clock["now"])
        return httpx.Response(200, json=body)

    client = FinnhubClient(
        api_key="test-token",
        cache=cache,
        limiter=RateLimiter(3, 60.0, now=lambda: clock["now"], sleep=sleep),
        transport=httpx.MockTransport(timestamped),
        policy=RetryPolicy(attempts=3, base_delay=0, jitter=False),
        now=lambda: NOW,
    )

    for ticker in ("A", "B", "C", "D", "E", "F", "G", "H"):
        await client.get_fundamentals(ticker)

    assert len(sent_at) == 8
    for start in sent_at:
        assert len([t for t in sent_at if start <= t < start + 60.0]) <= 3
    # And it really did have to wait to achieve that.
    assert slept


# --- caching and failure -----------------------------------------------------


async def test_news_and_fundamentals_do_not_share_a_cache_entry(cache, limiter):
    recorder = Recorder(
        {
            "/stock/metric": load("finnhub_metrics_aapl"),
            "/company-news": load("finnhub_company_news_aapl"),
        }
    )
    client = build_client(recorder, cache, limiter)

    await client.get_fundamentals("AAPL")
    await client.get_company_news("AAPL", **WINDOW)

    assert len(recorder.requests) == 2


async def test_a_persistent_failure_raises(cache, limiter):
    recorder = Recorder({"/stock/metric": {}}, status=503)
    client = build_client(recorder, cache, limiter)

    with pytest.raises(UpstreamError, match="finnhub"):
        await client.get_fundamentals("AAPL")


async def test_the_token_is_sent_but_never_reaches_an_error_message(cache, limiter):
    recorder = Recorder({"/stock/metric": load("finnhub_metrics_aapl")})
    client = build_client(recorder, cache, limiter)

    await client.get_fundamentals("AAPL")
    assert recorder.last.url.params.get("token") == "test-token"

    failing = Recorder({"/stock/metric": {"error": "invalid token test-token"}}, status=403)
    client = build_client(failing, cache, limiter)

    with pytest.raises(UpstreamError) as caught:
        await client.get_fundamentals("MSFT")

    assert "test-token" not in str(caught.value)
