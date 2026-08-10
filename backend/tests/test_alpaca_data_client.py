# Alpaca data client, driven by the recorded fixtures through an httpx
# MockTransport. The transport sits below httpx rather than replacing it, so
# URL building, query encoding and status handling are all really exercised —
# a test that stubbed the client's own methods would assert nothing about them.

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pandas as pd
import pytest

from app.alpaca import AlpacaAccount
from app.data.alpaca_client import (
    FREE_FEED_DELAY,
    AlpacaDataClient,
    bars_to_frame,
    clamp_end,
)
from app.data.cache import Cache
from app.data.http import RetryPolicy, UpstreamError
from tests.fixtures import load

NOW = datetime(2026, 8, 9, 14, 30, tzinfo=UTC)


class FakeAccountClient:
    """The seam app/alpaca.py already defines. get_account delegates here, so
    the test proves delegation rather than reimplementation."""

    def __init__(self):
        self.calls = 0

    async def get_account(self) -> AlpacaAccount:
        self.calls += 1
        return AlpacaAccount(equity=101_240.5, cash=24_000.0, last_equity=100_980.0)


class Recorder:
    """Serves fixtures and records every request httpx actually sent."""

    def __init__(self, routes: dict[str, object], status: int = 200):
        self.routes = routes
        self.status = status
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        for fragment, body in self.routes.items():
            if fragment in request.url.path:
                if callable(body):
                    return body(request)
                return httpx.Response(self.status, json=body)
        return httpx.Response(404, json={"message": "no route"})

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]

    def param(self, name: str) -> str | None:
        return self.last.url.params.get(name)


@pytest.fixture
def account_client() -> FakeAccountClient:
    return FakeAccountClient()


@pytest.fixture
def cache(tmp_path: Path) -> Cache:
    return Cache(tmp_path / "cache.sqlite3", now=lambda: NOW)


def build_client(
    recorder: Recorder,
    cache: Cache,
    account_client: FakeAccountClient,
    *,
    now: datetime = NOW,
) -> AlpacaDataClient:
    return AlpacaDataClient(
        key_id="test-key",
        secret_key="test-secret",
        account_client=account_client,
        cache=cache,
        transport=httpx.MockTransport(recorder),
        # No real backoff: a retry test should assert on behaviour, not spend
        # eight seconds proving it.
        policy=RetryPolicy(attempts=3, base_delay=0, jitter=False),
        now=lambda: now,
    )


# --- the 15-minute clamp -----------------------------------------------------
#
# The spec calls this the single most common source of "the API returned
# nothing", so it is tested as a pure function and again through a real request.


def test_end_of_none_means_fifteen_minutes_ago():
    assert clamp_end(None, now=NOW) == NOW - FREE_FEED_DELAY


def test_an_end_of_now_is_pulled_back():
    assert clamp_end(NOW, now=NOW) == NOW - FREE_FEED_DELAY


def test_an_end_inside_the_blind_spot_is_pulled_back():
    inside = NOW - timedelta(minutes=5)

    assert clamp_end(inside, now=NOW) == NOW - FREE_FEED_DELAY


def test_an_end_safely_in_the_past_is_left_alone():
    past = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)

    assert clamp_end(past, now=NOW) == past


def test_an_end_in_the_future_is_pulled_back_to_the_ceiling():
    assert clamp_end(NOW + timedelta(days=3), now=NOW) == NOW - FREE_FEED_DELAY


def test_a_bare_end_date_means_the_close_of_that_day():
    # Midnight would silently drop that day's bar, whose timestamp is the
    # session open — a window one day shorter than asked for, with no error.
    clamped = clamp_end(date(2026, 8, 1), now=NOW)

    assert clamped.date() == date(2026, 8, 1)
    assert clamped.hour == 23


def test_a_naive_datetime_is_treated_as_utc():
    assert clamp_end(datetime(2026, 8, 1, 12, 0), now=NOW).tzinfo is UTC


async def test_the_request_really_carries_the_clamped_end(cache, account_client):
    recorder = Recorder({"/v2/stocks/bars": load("alpaca_bars_aapl_1day")})
    client = build_client(recorder, cache, account_client)

    await client.get_bars("AAPL", start=date(2026, 4, 13))

    sent_end = datetime.fromisoformat(recorder.param("end"))
    assert sent_end == NOW - FREE_FEED_DELAY


# --- bars --------------------------------------------------------------------


async def test_bars_come_back_as_a_named_indicator_ready_frame(cache, account_client):
    recorder = Recorder({"/v2/stocks/bars": load("alpaca_bars_aapl_1day")})
    client = build_client(recorder, cache, account_client)

    frame = await client.get_bars("AAPL", start=date(2026, 4, 13))

    assert list(frame.columns) == [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trade_count",
        "vwap",
    ]
    assert len(frame) == 82
    assert frame.index.name == "timestamp"
    assert str(frame.index.tz) == "UTC"
    assert frame.index.is_monotonic_increasing
    assert frame["close"].dtype == "float64"


def test_the_frame_carries_the_recorded_values():
    # First bar of the fixture, checked by hand against the JSON.
    frame = bars_to_frame(load("alpaca_bars_aapl_1day")["bars"]["AAPL"])
    first = frame.iloc[0]

    assert first["open"] == 259.73
    assert first["high"] == 260.125
    assert first["low"] == 256.7
    assert first["close"] == 259.13
    assert first["volume"] == 1_154_691
    assert first["trade_count"] == 14_965
    assert frame.index[0] == pd.Timestamp("2026-04-13T04:00:00Z")


def test_an_empty_response_is_an_empty_frame_not_a_crash():
    # A halted ticker or a holiday window is legitimately empty. Downstream
    # branches on .empty, so the columns must exist even with no rows.
    frame = bars_to_frame([])

    assert frame.empty
    assert "close" in frame.columns
    assert str(frame.index.tz) == "UTC"


async def test_paging_follows_next_page_token(cache, account_client):
    # Stopping at page one would truncate any long window, and the truncated
    # numbers still look plausible — which is what makes it dangerous.
    page_one = {
        "bars": {"AAPL": [{"t": "2026-04-13T04:00:00Z", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10, "n": 2, "vw": 1.2}]},
        "next_page_token": "page-2",
    }
    page_two = {
        "bars": {"AAPL": [{"t": "2026-04-14T04:00:00Z", "o": 2, "h": 3, "l": 1.5, "c": 2.5, "v": 20, "n": 4, "vw": 2.2}]},
        "next_page_token": None,
    }

    def serve(request: httpx.Request) -> httpx.Response:
        token = request.url.params.get("page_token")
        return httpx.Response(200, json=page_two if token == "page-2" else page_one)

    recorder = Recorder({"/v2/stocks/bars": serve})
    client = build_client(recorder, cache, account_client)

    frame = await client.get_bars("AAPL", start=date(2026, 4, 13))

    assert len(frame) == 2
    assert len(recorder.requests) == 2


async def test_the_free_feed_is_requested_by_name(cache, account_client):
    recorder = Recorder({"/v2/stocks/bars": load("alpaca_bars_aapl_1day")})
    client = build_client(recorder, cache, account_client)

    await client.get_bars("AAPL", start=date(2026, 4, 13))

    assert recorder.param("feed") == "iex"


# --- caching -----------------------------------------------------------------


async def test_a_second_call_for_a_closed_window_makes_no_request(cache, account_client):
    # The acceptance criterion: second call hits cache.
    recorder = Recorder({"/v2/stocks/bars": load("alpaca_bars_aapl_1day")})
    client = build_client(recorder, cache, account_client)
    window = {"start": date(2026, 4, 13), "end": date(2026, 8, 7)}

    first = await client.get_bars("AAPL", **window)
    second = await client.get_bars("AAPL", **window)

    assert len(recorder.requests) == 1
    pd.testing.assert_frame_equal(first, second)


async def test_a_different_window_is_a_different_cache_entry(cache, account_client):
    recorder = Recorder({"/v2/stocks/bars": load("alpaca_bars_aapl_1day")})
    client = build_client(recorder, cache, account_client)

    await client.get_bars("AAPL", start=date(2026, 4, 13), end=date(2026, 8, 7))
    await client.get_bars("AAPL", start=date(2026, 5, 13), end=date(2026, 8, 7))

    assert len(recorder.requests) == 2


async def test_a_different_ticker_is_a_different_cache_entry(cache, account_client):
    recorder = Recorder({"/v2/stocks/bars": load("alpaca_bars_aapl_1day")})
    client = build_client(recorder, cache, account_client)

    await client.get_bars("AAPL", start=date(2026, 4, 13), end=date(2026, 8, 7))
    await client.get_bars("MSFT", start=date(2026, 4, 13), end=date(2026, 8, 7))

    assert len(recorder.requests) == 2


# --- snapshot ----------------------------------------------------------------


async def test_snapshot_parses_the_recorded_response(cache, account_client):
    recorder = Recorder({"/v2/stocks/snapshots": load("alpaca_snapshot_aapl")})
    client = build_client(recorder, cache, account_client)

    snapshot = await client.get_snapshot("AAPL")

    assert snapshot.ticker == "AAPL"
    assert snapshot.daily_bar.close == 313.29
    assert snapshot.previous_daily_bar.close == 312.45
    assert snapshot.minute_bar.close == 313.29
    assert snapshot.latest_trade_price == 313.29
    assert snapshot.latest_trade_at.year == 2026


async def test_the_gap_is_todays_open_against_yesterdays_close(cache, account_client):
    recorder = Recorder({"/v2/stocks/snapshots": load("alpaca_snapshot_aapl")})
    client = build_client(recorder, cache, account_client)

    snapshot = await client.get_snapshot("AAPL")

    # open 311.395 vs previous close 312.45 -> -0.34%
    assert snapshot.gap_pct == pytest.approx(-0.34, abs=0.01)


async def test_a_gap_with_no_previous_bar_is_unknown_not_zero(cache, account_client):
    # "No gap" and "we do not know" are different answers; a screener must not
    # read the second as the first.
    recorder = Recorder({"/v2/stocks/snapshots": {"AAPL": {"dailyBar": {"t": "2026-08-07T04:00:00Z", "o": 1, "h": 1, "l": 1, "c": 1, "v": 1, "n": 1, "vw": 1}}}})
    client = build_client(recorder, cache, account_client)

    assert (await client.get_snapshot("AAPL")).gap_pct is None


async def test_snapshots_are_never_cached(cache, account_client):
    # A cached quote is a wrong quote.
    recorder = Recorder({"/v2/stocks/snapshots": load("alpaca_snapshot_aapl")})
    client = build_client(recorder, cache, account_client)

    await client.get_snapshot("AAPL")
    await client.get_snapshot("AAPL")

    assert len(recorder.requests) == 2


async def test_an_unknown_ticker_snapshot_is_empty_not_an_error(cache, account_client):
    recorder = Recorder({"/v2/stocks/snapshots": {}})
    client = build_client(recorder, cache, account_client)

    snapshot = await client.get_snapshot("NOSUCH")

    assert snapshot.daily_bar is None
    assert snapshot.latest_trade_price is None


# --- screener ----------------------------------------------------------------


async def test_most_actives_parses_the_recorded_response(cache, account_client):
    recorder = Recorder({"most-actives": load("alpaca_most_actives")})
    client = build_client(recorder, cache, account_client)

    actives = await client.get_most_actives(top=20)

    assert actives[0].symbol == "HCWC"
    assert actives[0].volume == 654_104_296
    assert actives[0].trade_count == 733_341
    assert all(a.symbol for a in actives)


async def test_movers_split_into_gainers_and_losers(cache, account_client):
    recorder = Recorder({"movers": load("alpaca_movers")})
    client = build_client(recorder, cache, account_client)

    movers = await client.get_market_movers(top=20)

    assert movers.gainers[0].symbol == "ANSCW"
    assert movers.gainers[0].percent_change == 250
    assert movers.losers
    assert all(m.percent_change < 0 for m in movers.losers)


async def test_the_screener_sweeps_are_not_cached(cache, account_client):
    # A stale candidate list would point the agents at yesterday's movers.
    recorder = Recorder({"most-actives": load("alpaca_most_actives")})
    client = build_client(recorder, cache, account_client)

    await client.get_most_actives()
    await client.get_most_actives()

    assert len(recorder.requests) == 2


# --- delegation --------------------------------------------------------------


async def test_get_account_delegates_rather_than_reimplementing(cache, account_client):
    # app/alpaca.py owns account access; this client composes it. If this ever
    # starts issuing its own HTTP request, the dashboard and the pipeline can
    # disagree about the account.
    recorder = Recorder({})
    client = build_client(recorder, cache, account_client)

    account = await client.get_account()

    assert account.equity == 101_240.5
    assert account_client.calls == 1
    assert recorder.requests == []


# --- failure -----------------------------------------------------------------


async def test_a_persistent_server_error_raises(cache, account_client):
    recorder = Recorder({"/v2/stocks/bars": {}}, status=503)
    client = build_client(recorder, cache, account_client)

    with pytest.raises(UpstreamError, match="alpaca"):
        await client.get_bars("AAPL", start=date(2026, 4, 13))


async def test_a_failed_call_caches_nothing(cache, account_client):
    recorder = Recorder({"/v2/stocks/bars": {}}, status=503)
    client = build_client(recorder, cache, account_client)

    with pytest.raises(UpstreamError):
        await client.get_bars("AAPL", start=date(2026, 4, 13), end=date(2026, 8, 7))

    recorder.status = 200
    recorder.routes = {"/v2/stocks/bars": load("alpaca_bars_aapl_1day")}
    frame = await client.get_bars("AAPL", start=date(2026, 4, 13), end=date(2026, 8, 7))

    assert len(frame) == 82


async def test_no_module_in_the_data_layer_places_an_order():
    # Hard rule, asserted rather than trusted: only the executor may place
    # orders, and this phase has no executor.
    source = Path(__file__).resolve().parents[1] / "app" / "data"
    forbidden = ("/v2/orders", "submit_order", "place_order", ".post(", ".delete(")

    offenders = [
        f"{path.name}: {token}"
        for path in source.rglob("*.py")
        for token in forbidden
        if token in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
