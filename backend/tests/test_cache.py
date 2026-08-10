# Cache behaviour, with an injected clock so TTL expiry is tested without
# sleeping and without the result depending on how long the suite takes.

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from app.data.cache import (
    FUNDAMENTALS_TTL,
    MACRO_TTL,
    NEVER_EXPIRES,
    NEWS_TTL,
    Cache,
    CacheKey,
    historical_ttl,
)

T0 = datetime(2026, 8, 9, 14, 30, tzinfo=UTC)


class Clock:
    """A hand-cranked clock. `advance` is the only way time passes."""

    def __init__(self, now: datetime = T0):
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def cache(tmp_path: Path, clock: Clock) -> Cache:
    return Cache(tmp_path / "cache.sqlite3", now=clock)


KEY = CacheKey(source="finnhub", method="fundamentals", ticker="AAPL")


def test_a_miss_returns_none(cache: Cache):
    assert cache.get(KEY) is None


def test_a_stored_value_comes_back(cache: Cache):
    cache.put(KEY, {"pe": 31.4}, ttl=FUNDAMENTALS_TTL)

    hit = cache.get(KEY)

    assert hit is not None
    assert hit.value == {"pe": 31.4}
    assert hit.is_stale is False


def test_an_entry_survives_a_new_cache_over_the_same_file(tmp_path: Path, clock: Clock):
    # The pipeline is a scheduled job: every run is a new process against the
    # same file, so persistence across instances is the whole point.
    path = tmp_path / "cache.sqlite3"
    Cache(path, now=clock).put(KEY, [1, 2, 3], ttl=FUNDAMENTALS_TTL)

    hit = Cache(path, now=clock).get(KEY)

    assert hit is not None
    assert hit.value == [1, 2, 3]


def test_the_parent_directory_is_created(tmp_path: Path, clock: Clock):
    # A fresh clone has no .data/ directory.
    cache = Cache(tmp_path / "nested" / "deeper" / "cache.sqlite3", now=clock)
    cache.put(KEY, 1, ttl=FUNDAMENTALS_TTL)

    assert cache.get(KEY) is not None


def test_a_value_is_still_fresh_just_before_its_ttl(cache: Cache, clock: Clock):
    cache.put(KEY, "v", ttl=NEWS_TTL)

    clock.advance(NEWS_TTL - timedelta(seconds=1))

    assert cache.get(KEY) is not None


def test_an_expired_value_is_a_miss(cache: Cache, clock: Clock):
    cache.put(KEY, "v", ttl=NEWS_TTL)

    clock.advance(NEWS_TTL + timedelta(seconds=1))

    assert cache.get(KEY) is None


def test_never_expires_survives_an_absurd_amount_of_time(cache: Cache, clock: Clock):
    cache.put(KEY, "a closed trading day", ttl=NEVER_EXPIRES)

    clock.advance(timedelta(days=4000))

    hit = cache.get(KEY)
    assert hit is not None
    assert hit.is_stale is False


def test_stale_data_is_never_returned_unasked(cache: Cache, clock: Clock):
    # The rule that matters: no code path hands back expired data unless the
    # caller named allow_stale, and even then it arrives flagged.
    cache.put(KEY, "old", ttl=NEWS_TTL)
    clock.advance(NEWS_TTL * 2)

    assert cache.get(KEY) is None

    deliberate = cache.get(KEY, allow_stale=True)
    assert deliberate is not None
    assert deliberate.value == "old"
    assert deliberate.is_stale is True


def test_a_fresh_hit_is_not_flagged_stale_by_allow_stale(cache: Cache):
    cache.put(KEY, "new", ttl=NEWS_TTL)

    hit = cache.get(KEY, allow_stale=True)

    assert hit is not None
    assert hit.is_stale is False


def test_putting_again_replaces_the_entry(cache: Cache):
    cache.put(KEY, "first", ttl=FUNDAMENTALS_TTL)
    cache.put(KEY, "second", ttl=FUNDAMENTALS_TTL)

    hit = cache.get(KEY)
    assert hit is not None
    assert hit.value == "second"


def test_a_replaced_entry_gets_a_fresh_expiry(cache: Cache, clock: Clock):
    cache.put(KEY, "first", ttl=NEWS_TTL)
    clock.advance(NEWS_TTL - timedelta(minutes=1))
    cache.put(KEY, "second", ttl=NEWS_TTL)

    clock.advance(timedelta(minutes=2))

    hit = cache.get(KEY)
    assert hit is not None
    assert hit.value == "second"


# --- key identity ------------------------------------------------------------


def test_different_tickers_do_not_collide(cache: Cache):
    cache.put(CacheKey("finnhub", "fundamentals", "AAPL"), "apple", ttl=FUNDAMENTALS_TTL)
    cache.put(CacheKey("finnhub", "fundamentals", "MSFT"), "microsoft", ttl=FUNDAMENTALS_TTL)

    assert cache.get(CacheKey("finnhub", "fundamentals", "AAPL")).value == "apple"
    assert cache.get(CacheKey("finnhub", "fundamentals", "MSFT")).value == "microsoft"


def test_different_sources_do_not_collide(cache: Cache):
    cache.put(CacheKey("alpaca", "bars", "AAPL"), "from alpaca", ttl=FUNDAMENTALS_TTL)
    cache.put(CacheKey("finnhub", "bars", "AAPL"), "from finnhub", ttl=FUNDAMENTALS_TTL)

    assert cache.get(CacheKey("alpaca", "bars", "AAPL")).value == "from alpaca"


def test_different_params_do_not_collide(cache: Cache):
    ninety = CacheKey("alpaca", "bars", "AAPL", {"days": 90})
    thirty = CacheKey("alpaca", "bars", "AAPL", {"days": 30})

    cache.put(ninety, "90 days", ttl=FUNDAMENTALS_TTL)
    cache.put(thirty, "30 days", ttl=FUNDAMENTALS_TTL)

    assert cache.get(ninety).value == "90 days"
    assert cache.get(thirty).value == "30 days"


def test_param_order_does_not_change_the_key(cache: Cache):
    cache.put(CacheKey("alpaca", "bars", "AAPL", {"a": 1, "b": 2}), "v", ttl=FUNDAMENTALS_TTL)

    assert cache.get(CacheKey("alpaca", "bars", "AAPL", {"b": 2, "a": 1})) is not None


def test_dates_in_params_do_not_raise(cache: Cache):
    # Bar windows are naturally keyed by date objects, which are not
    # JSON-serialisable by default.
    key = CacheKey("alpaca", "bars", "AAPL", {"start": date(2026, 1, 1)})

    cache.put(key, "v", ttl=FUNDAMENTALS_TTL)

    assert cache.get(key) is not None


def test_a_tickerless_call_is_a_valid_key(cache: Cache):
    # FRED series and screener sweeps are not about one ticker.
    dff = CacheKey("fred", "series", params={"series_id": "DFF"})
    unrate = CacheKey("fred", "series", params={"series_id": "UNRATE"})

    cache.put(dff, [1], ttl=MACRO_TTL)
    cache.put(unrate, [2], ttl=MACRO_TTL)

    assert cache.get(dff).value == [1]
    assert cache.get(unrate).value == [2]


# --- fetch -------------------------------------------------------------------


class Loader:
    """Stands in for a network call and counts how often it was made."""

    def __init__(self, value="from upstream"):
        self.calls = 0
        self.value = value

    async def __call__(self):
        self.calls += 1
        return self.value


async def test_fetch_calls_upstream_on_a_miss(cache: Cache):
    load = Loader()

    assert await cache.fetch(KEY, ttl=FUNDAMENTALS_TTL, load=load) == "from upstream"
    assert load.calls == 1


async def test_a_second_fetch_within_ttl_makes_zero_network_calls(cache: Cache, clock: Clock):
    # The acceptance criterion, stated directly.
    load = Loader()

    first = await cache.fetch(KEY, ttl=FUNDAMENTALS_TTL, load=load)
    clock.advance(FUNDAMENTALS_TTL - timedelta(hours=1))
    second = await cache.fetch(KEY, ttl=FUNDAMENTALS_TTL, load=load)

    assert first == second
    assert load.calls == 1


async def test_fetch_goes_back_upstream_once_the_ttl_lapses(cache: Cache, clock: Clock):
    load = Loader()

    await cache.fetch(KEY, ttl=NEWS_TTL, load=load)
    clock.advance(NEWS_TTL + timedelta(minutes=1))
    await cache.fetch(KEY, ttl=NEWS_TTL, load=load)

    assert load.calls == 2


async def test_an_upstream_failure_on_a_miss_raises(cache: Cache):
    # No silent fallback: a failed miss is an error, not an empty result.
    async def explode():
        raise RuntimeError("upstream is down")

    with pytest.raises(RuntimeError, match="upstream is down"):
        await cache.fetch(KEY, ttl=FUNDAMENTALS_TTL, load=explode)


async def test_an_upstream_failure_does_not_resurrect_an_expired_entry(
    cache: Cache, clock: Clock
):
    # The failure mode this rule exists to prevent: upstream breaks, and the
    # pipeline quietly analyses last week's numbers as if they were today's.
    await cache.fetch(KEY, ttl=NEWS_TTL, load=Loader("yesterday's news"))
    clock.advance(NEWS_TTL * 2)

    async def explode():
        raise RuntimeError("upstream is down")

    with pytest.raises(RuntimeError):
        await cache.fetch(KEY, ttl=NEWS_TTL, load=explode)


async def test_a_failed_fetch_stores_nothing(cache: Cache):
    async def explode():
        raise RuntimeError("upstream is down")

    with pytest.raises(RuntimeError):
        await cache.fetch(KEY, ttl=FUNDAMENTALS_TTL, load=explode)

    assert cache.get(KEY, allow_stale=True) is None


# --- purge -------------------------------------------------------------------


def test_purge_removes_only_expired_rows(cache: Cache, clock: Clock):
    fresh = CacheKey("finnhub", "fundamentals", "MSFT")
    permanent = CacheKey("alpaca", "bars", "AAPL", {"end": "2026-01-05"})
    cache.put(KEY, "news", ttl=NEWS_TTL)
    cache.put(fresh, "fundamentals", ttl=FUNDAMENTALS_TTL)
    cache.put(permanent, "a closed day", ttl=NEVER_EXPIRES)

    clock.advance(NEWS_TTL * 2)

    assert cache.purge_expired() == 1
    assert cache.get(KEY, allow_stale=True) is None
    assert cache.get(fresh) is not None
    assert cache.get(permanent) is not None


# --- historical_ttl ----------------------------------------------------------


def test_a_window_that_closed_in_the_past_never_expires():
    # A completed trading day cannot change, so re-fetching it is pure waste.
    assert historical_ttl(date(2026, 8, 7), today=date(2026, 8, 9)) is NEVER_EXPIRES


def test_a_window_ending_today_is_not_permanent():
    # Bars are still arriving, so today's window must be re-fetched.
    assert historical_ttl(date(2026, 8, 9), today=date(2026, 8, 9)) == MACRO_TTL


def test_a_window_ending_in_the_future_is_not_permanent():
    assert historical_ttl(date(2026, 8, 20), today=date(2026, 8, 9)) == MACRO_TTL
