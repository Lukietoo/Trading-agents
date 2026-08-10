# The Phase 1 acceptance criteria, made executable.
#
# One test per checkbox in specs/phase-1.md, in the spec's own order and
# wording. The behaviour is covered in depth elsewhere — test_cache.py,
# test_indicators.py and so on. The point of this file is different: it is the
# thing that justifies ticking a box, and it fails if a later phase quietly
# undoes something Phase 1 promised.
#
# Read it as the spec's own test, not as extra coverage.

import re
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import httpx
import pandas as pd
import pytest

from app.config import Config, MissingConfigError, load_config
from app.data import MarketData, indicators
from app.data.alpaca_client import bars_to_frame
from tests.conftest import MarketClock, NetworkAccessAttempted, Router
from tests.fixtures import load

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
DATA_LAYER = BACKEND / "app" / "data"


# --- [x] MarketData().get_bars('AAPL', 90) returns clean data; -------------
#         second call hits cache


async def test_get_bars_returns_clean_data(market: MarketData):
    frame = await market.get_bars("AAPL", 90)

    assert not frame.empty
    assert list(frame.columns) == [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trade_count",
        "vwap",
    ]
    # "Clean" spelled out: no gaps, sane ordering, real dtypes, and prices that
    # hold together as OHLC rather than merely being numbers.
    assert frame[["open", "high", "low", "close"]].notna().all().all()
    assert frame.index.is_monotonic_increasing
    assert not frame.index.has_duplicates
    assert str(frame.index.tz) == "UTC"
    assert frame["close"].dtype == "float64"
    assert (frame["high"] >= frame["low"]).all()
    assert (frame["high"] >= frame["close"]).all()
    assert (frame["low"] <= frame["close"]).all()
    assert (frame["volume"] >= 0).all()


async def test_the_second_call_hits_the_cache(market: MarketData, router: Router):
    first = await market.get_bars("AAPL", 90)
    second = await market.get_bars("AAPL", 90)

    assert len(router.requests) == 1
    pd.testing.assert_frame_equal(first, second)


async def test_the_second_call_hits_the_cache_on_a_clock_that_moves(
    market: MarketData, router: Router, market_clock: MarketClock
):
    # The frozen-clock version above passed even when the cache never hit in
    # production, because the window end went into the cache key at
    # microsecond precision. Repeating it on a clock that moves is what makes
    # the tick honest — and the clock has to be the one the Alpaca client
    # uses, since that is where the window end is computed. Verified by
    # restoring the original bug and watching this fail.
    await market.get_bars("AAPL", 90)
    market_clock.advance(timedelta(seconds=3))
    await market.get_bars("AAPL", 90)

    assert len(router.requests) == 1


def test_market_data_takes_no_arguments(monkeypatch, tmp_path):
    # The criterion is written `MarketData()`, so the no-argument constructor
    # has to work. It reads .env, which is why the keys are supplied here
    # rather than borrowed from the developer's own machine.
    for name, value in {
        "ALPACA_API_KEY_ID": "id",
        "ALPACA_API_SECRET_KEY": "secret",
        "FINNHUB_API_KEY": "finnhub",
        "FRED_API_KEY": "fred",
        "DATA_CACHE_PATH": str(tmp_path / "cache.sqlite3"),
    }.items():
        monkeypatch.setenv(name, value)

    assert isinstance(MarketData(), MarketData)


# --- [x] MarketData().get_fundamentals('AAPL') returns populated fields ----


async def test_get_fundamentals_returns_populated_fields(market: MarketData):
    fundamentals = await market.get_fundamentals("AAPL")

    assert fundamentals.is_populated
    # Named individually: "populated" must not be satisfiable by one field
    # arriving and the rest being None.
    for field in (
        "market_cap_millions",
        "pe_ttm",
        "price_to_book",
        "beta",
        "gross_margin_ttm",
        "operating_margin_ttm",
        "net_margin_ttm",
        "week52_high",
        "week52_low",
    ):
        assert getattr(fundamentals, field) is not None, f"{field} came back empty"

    assert fundamentals.week52_high > fundamentals.week52_low
    assert fundamentals.market_cap_millions > 0


# --- [x] Indicators compute correctly on fixtures --------------------------


def test_indicators_compute_correctly_on_fixtures():
    bars = bars_to_frame(load("alpaca_bars_aapl_1day")["bars"]["AAPL"])

    enriched = indicators.add_indicators(bars)

    # Checked against arithmetic that does not go through TA-Lib.
    assert enriched["sma_20"].iloc[-1] == pytest.approx(bars["close"].tail(20).mean())
    assert enriched["bb_middle"].iloc[-1] == pytest.approx(
        bars["close"].tail(20).mean()
    )
    assert enriched["macd_hist"].iloc[-1] == pytest.approx(
        enriched["macd"].iloc[-1] - enriched["macd_signal"].iloc[-1]
    )
    assert enriched["rsi_14"].dropna().between(0, 100).all()
    assert (enriched["atr_14"].dropna() >= 0).all()
    assert (enriched["bb_upper"].dropna() >= enriched["bb_lower"].dropna()).all()


def test_an_indicator_the_window_cannot_support_is_nan_not_invented():
    # The honest-answer rule. 82 bars cannot produce a 200-bar average, and
    # nothing quietly substitutes a shorter window.
    bars = bars_to_frame(load("alpaca_bars_aapl_1day")["bars"]["AAPL"])

    enriched = indicators.add_indicators(bars)

    assert len(bars) == 82
    assert enriched["sma_200"].isna().all()
    assert enriched["sma_20"].notna().any()


def test_a_warm_up_is_never_back_filled():
    # An all-NaN column alone is a weak check: back-filling cannot forge a
    # 200-bar average out of nothing, so the mutation hides. A *partly*
    # computable indicator is where filling would show, and its early rows
    # must stay empty. Verified by making add_indicators bfill and watching
    # this fail.
    bars = bars_to_frame(load("alpaca_bars_aapl_1day")["bars"]["AAPL"])

    enriched = indicators.add_indicators(bars)

    assert enriched["sma_20"].iloc[:19].isna().all()
    assert enriched["sma_20"].iloc[19:].notna().all()
    assert enriched["sma_50"].iloc[:49].isna().all()
    assert enriched["rsi_14"].iloc[:14].isna().all()
    assert enriched["volume_vs_20d_avg"].iloc[:20].isna().all()


# --- [x] Missing config key produces a clear startup error naming the key --


@pytest.mark.parametrize(
    "missing",
    ["ALPACA_API_KEY_ID", "ALPACA_API_SECRET_KEY", "FINNHUB_API_KEY", "FRED_API_KEY"],
)
def test_a_missing_config_key_is_named_in_the_error(monkeypatch, missing: str):
    for name in (
        "ALPACA_API_KEY_ID",
        "ALPACA_API_SECRET_KEY",
        "FINNHUB_API_KEY",
        "FRED_API_KEY",
    ):
        monkeypatch.setenv(name, "present")
    monkeypatch.delenv(missing)

    with pytest.raises(MissingConfigError) as caught:
        load_config(env_file=None)

    message = str(caught.value)
    assert missing in message
    # "Clear" means it also says what to do about it.
    assert ".env" in message


def test_every_missing_key_is_named_at_once(monkeypatch):
    # Setting up a machine should cost one error message, not four runs.
    for name in (
        "ALPACA_API_KEY_ID",
        "ALPACA_API_SECRET_KEY",
        "FINNHUB_API_KEY",
        "FRED_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(MissingConfigError) as caught:
        load_config(env_file=None)

    for name in (
        "ALPACA_API_KEY_ID",
        "ALPACA_API_SECRET_KEY",
        "FINNHUB_API_KEY",
        "FRED_API_KEY",
    ):
        assert name in str(caught.value)


# --- [x] pytest passes with no network access; ruff check clean ------------


def _flattened(error: BaseException):
    """Unwrap ExceptionGroups. httpx connects via anyio's happy-eyeballs, which
    races several addresses and reports the losers as a group."""
    if isinstance(error, BaseExceptionGroup):
        for inner in error.exceptions:
            yield from _flattened(inner)
    else:
        yield error


def test_a_real_socket_connection_is_refused():
    # The guard in conftest.py is session-wide and autouse, so this is a
    # property of every test in the run, not just of this one.
    import socket

    with pytest.raises(NetworkAccessAttempted):
        socket.socket().connect(("data.alpaca.markets", 443))


async def test_an_unmocked_client_cannot_reach_a_real_api():
    # The same guard seen from where it matters: a client that lost its
    # injected transport fails loudly instead of quietly calling the API with
    # a live key.
    with pytest.raises(BaseException) as caught:  # noqa: B017 - group unwrapped below
        async with httpx.AsyncClient(timeout=1.0) as client:
            await client.get("https://data.alpaca.markets/v2/stocks/bars")

    assert any(
        isinstance(error, NetworkAccessAttempted) for error in _flattened(caught.value)
    )


def test_ruff_check_is_clean():
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"ruff check failed:\n{result.stdout}{result.stderr}"


# --- [x] .env.example lists every key --------------------------------------


def test_env_example_lists_every_config_key():
    declared = set(
        re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", (REPO / ".env.example").read_text(), re.M)
    )
    required = {name.upper() for name in Config.model_fields}

    assert not (required - declared), (
        f"missing from .env.example: {sorted(required - declared)}"
    )


def test_env_example_carries_no_real_looking_secret():
    # It is committed, so a real key pasted in by accident should fail here
    # rather than reach the remote.
    for line in (REPO / ".env.example").read_text().splitlines():
        if line.startswith("#") or "=" not in line:
            continue
        _, _, value = line.partition("=")
        value = value.strip()
        assert not value or "your-" in value or value.startswith("https://"), (
            f"{line.split('=')[0]} looks like a real value, not a placeholder"
        )


def test_the_cache_and_env_are_gitignored():
    # Both are machine-local. Committing either is how a key or a stale cache
    # reaches the remote.
    ignored = (REPO / ".gitignore").read_text()

    assert ".env" in ignored
    assert ".data/" in ignored


# --- [x] no order-placement call anywhere in backend/data/ -----------------


def test_no_module_in_the_data_layer_places_an_order():
    # Hard rule 2: only the executor places orders, and it does not exist yet.
    forbidden = ("/v2/orders", "submit_order", "place_order", "OrderRequest")

    offenders = [
        f"{path.relative_to(BACKEND)}: {token}"
        for path in DATA_LAYER.rglob("*.py")
        for token in forbidden
        if token in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_the_data_layer_only_ever_issues_get_requests():
    # Stronger than grepping for order endpoints: no HTTP write verb exists
    # anywhere in the package, so there is no request that *could* place one.
    writes = re.compile(r"\.(post|put|patch|delete)\s*\(")

    offenders = [
        f"{path.relative_to(BACKEND)}:{number}"
        for path in DATA_LAYER.rglob("*.py")
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        # Cache.put is this project's own method, not an HTTP call.
        if writes.search(line) and ".put(" not in line
    ]

    assert offenders == []


def test_the_live_trading_host_is_refused_by_config(monkeypatch):
    # Hard rule 1, at the one place a host can enter the system.
    for name in (
        "ALPACA_API_KEY_ID",
        "ALPACA_API_SECRET_KEY",
        "FINNHUB_API_KEY",
        "FRED_API_KEY",
    ):
        monkeypatch.setenv(name, "present")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://api.alpaca.markets")

    with pytest.raises(ValueError, match="paper-only"):
        load_config(env_file=None)
