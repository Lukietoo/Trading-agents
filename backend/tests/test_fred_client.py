# FRED client, against the recorded observations.

from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pandas as pd
import pytest

from app.data.cache import Cache
from app.data.fred_client import (
    CPI,
    FED_FUNDS_RATE,
    UNEMPLOYMENT,
    YIELD_CURVE_10Y_2Y,
    FredClient,
    observations_to_series,
)
from app.data.http import RetryPolicy, UpstreamError
from tests.fixtures import load

NOW = datetime(2026, 8, 9, 14, 30, tzinfo=UTC)
WINDOW = {"start": date(2024, 8, 9), "end": date(2026, 8, 9)}


class Recorder:
    def __init__(self, body: object, status: int = 200):
        self.body = body
        self.status = status
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status, json=self.body)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]


@pytest.fixture
def cache(tmp_path: Path) -> Cache:
    return Cache(tmp_path / "cache.sqlite3", now=lambda: NOW)


def build_client(recorder: Recorder, cache: Cache) -> FredClient:
    return FredClient(
        api_key="test-fred-key",
        cache=cache,
        transport=httpx.MockTransport(recorder),
        policy=RetryPolicy(attempts=3, base_delay=0, jitter=False),
        now=lambda: NOW,
    )


# --- parsing -----------------------------------------------------------------


async def test_a_series_comes_back_as_a_float_series_on_dates(cache):
    recorder = Recorder(load("fred_unrate"))
    client = build_client(recorder, cache)

    series = await client.get_series(UNEMPLOYMENT, **WINDOW)

    assert isinstance(series, pd.Series)
    assert series.name == UNEMPLOYMENT
    assert series.dtype == "float64"
    assert isinstance(series.index, pd.DatetimeIndex)
    assert series.index.is_monotonic_increasing


async def test_the_recorded_values_survive_the_trip(cache):
    recorder = Recorder(load("fred_unrate"))
    client = build_client(recorder, cache)

    series = await client.get_series(UNEMPLOYMENT, **WINDOW)

    # First observation of the fixture, checked by hand.
    assert series.index[0] == pd.Timestamp("2024-08-01")
    assert series.iloc[0] == 4.2


def test_a_missing_observation_is_nan_not_zero():
    # FRED writes "." for no observation. Coercing it to 0.0 would turn "the
    # spread was not published" into "the spread was zero" — a real value with
    # the opposite meaning.
    series = observations_to_series(
        {
            "observations": [
                {"date": "2026-08-03", "value": "0.55"},
                {"date": "2026-08-04", "value": "."},
                {"date": "2026-08-05", "value": "0.57"},
            ]
        },
        "T10Y2Y",
    )

    assert series.iloc[0] == 0.55
    assert pd.isna(series.iloc[1])
    assert series.iloc[2] == 0.57
    assert (series == 0).sum() == 0


async def test_the_real_feed_really_contains_missing_observations(cache):
    # Not a hypothetical: the recorded T10Y2Y window holds three of them.
    recorder = Recorder(load("fred_t10y2y"))
    client = build_client(recorder, cache)

    series = await client.get_series(YIELD_CURVE_10Y_2Y, **WINDOW)

    assert series.isna().sum() == 3
    assert not series.dropna().empty


def test_a_gap_keeps_its_date():
    # Dropping the row would shorten the index and misalign this series
    # against any other it is compared with.
    series = observations_to_series(
        {
            "observations": [
                {"date": "2026-08-03", "value": "."},
                {"date": "2026-08-04", "value": "1.0"},
            ]
        },
        "X",
    )

    assert len(series) == 2
    assert series.index[0] == pd.Timestamp("2026-08-03")


def test_an_empty_response_is_an_empty_series():
    series = observations_to_series({"observations": []}, "X")

    assert series.empty
    assert series.dtype == "float64"


@pytest.mark.parametrize(
    "series_id,fixture",
    [
        (FED_FUNDS_RATE, "fred_dff"),
        (CPI, "fred_cpiaucsl"),
        (UNEMPLOYMENT, "fred_unrate"),
        (YIELD_CURVE_10Y_2Y, "fred_t10y2y"),
    ],
)
async def test_every_starting_series_parses(cache, series_id: str, fixture: str):
    recorder = Recorder(load(fixture))
    client = build_client(recorder, cache)

    series = await client.get_series(series_id, **WINDOW)

    assert not series.dropna().empty
    assert series.name == series_id


# --- request shape -----------------------------------------------------------


async def test_the_observation_window_is_sent(cache):
    recorder = Recorder(load("fred_unrate"))
    client = build_client(recorder, cache)

    await client.get_series(UNEMPLOYMENT, **WINDOW)

    assert recorder.last.url.params.get("observation_start") == "2024-08-09"
    assert recorder.last.url.params.get("observation_end") == "2026-08-09"
    assert recorder.last.url.params.get("file_type") == "json"


async def test_the_latest_view_asks_for_no_vintage(cache):
    recorder = Recorder(load("fred_unrate"))
    client = build_client(recorder, cache)

    await client.get_series(UNEMPLOYMENT, **WINDOW)

    assert "realtime_start" not in recorder.last.url.params


async def test_as_of_pins_the_request_to_a_vintage(cache):
    # CLAUDE.md hard rule 6: data used for a decision dated D must not include
    # anything published after D. FRED revises, so a plain request for a past
    # date returns today's revision of it.
    recorder = Recorder(load("fred_cpiaucsl"))
    client = build_client(recorder, cache)

    await client.get_series(CPI, **WINDOW, as_of=date(2026, 3, 1))

    assert recorder.last.url.params.get("realtime_start") == "2026-03-01"
    assert recorder.last.url.params.get("realtime_end") == "2026-03-01"


# --- caching -----------------------------------------------------------------


async def test_a_second_call_makes_no_request(cache):
    recorder = Recorder(load("fred_unrate"))
    client = build_client(recorder, cache)

    first = await client.get_series(UNEMPLOYMENT, **WINDOW)
    second = await client.get_series(UNEMPLOYMENT, **WINDOW)

    assert len(recorder.requests) == 1
    pd.testing.assert_series_equal(first, second)


async def test_different_series_are_different_entries(cache):
    recorder = Recorder(load("fred_unrate"))
    client = build_client(recorder, cache)

    await client.get_series(UNEMPLOYMENT, **WINDOW)
    await client.get_series(CPI, **WINDOW)

    assert len(recorder.requests) == 2


async def test_a_pinned_vintage_is_a_different_entry_from_the_latest_view(cache):
    # They are different data. Sharing an entry would serve a revision under
    # the name of a vintage or the reverse.
    recorder = Recorder(load("fred_cpiaucsl"))
    client = build_client(recorder, cache)

    await client.get_series(CPI, **WINDOW)
    await client.get_series(CPI, **WINDOW, as_of=date(2026, 3, 1))

    assert len(recorder.requests) == 2


async def test_the_api_key_is_sent_but_never_stored_in_the_cache(cache, tmp_path):
    # The cache file sits on disk and syncs to nothing, but a credential in a
    # cache key would still be a credential written to a file that is not .env.
    recorder = Recorder(load("fred_unrate"))
    client = build_client(recorder, cache)

    await client.get_series(UNEMPLOYMENT, **WINDOW)

    assert recorder.last.url.params.get("api_key") == "test-fred-key"
    assert b"test-fred-key" not in (tmp_path / "cache.sqlite3").read_bytes()


# --- failure -----------------------------------------------------------------


async def test_a_persistent_failure_raises(cache):
    recorder = Recorder({}, status=503)
    client = build_client(recorder, cache)

    with pytest.raises(UpstreamError, match="fred"):
        await client.get_series(UNEMPLOYMENT, **WINDOW)


async def test_a_rejected_key_does_not_appear_in_the_error(cache):
    # FRED takes the key in the query string, so both the URL and the body of
    # an error response can carry it.
    recorder = Recorder({"error_message": "Bad Request. api_key test-fred-key"}, status=400)
    client = build_client(recorder, cache)

    with pytest.raises(UpstreamError) as caught:
        await client.get_series(UNEMPLOYMENT, **WINDOW)

    assert "test-fred-key" not in str(caught.value)
