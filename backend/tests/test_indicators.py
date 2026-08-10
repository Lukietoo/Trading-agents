# Indicator tests.
#
# Asserting that talib.RSI equals talib.RSI would prove nothing, so the
# expected values here come from arithmetic done independently of TA-Lib:
# pandas rolling means, the defining identities of each indicator, and one
# fully hand-worked RSI on a series small enough to compute on paper.

import numpy as np
import pandas as pd
import pytest

from app.data.alpaca_client import bars_to_frame
from app.data.indicators import (
    add_indicators,
    atr,
    bollinger,
    macd,
    rsi,
    sma,
    volume_vs_average,
)
from tests.fixtures import load


@pytest.fixture
def bars() -> pd.DataFrame:
    """82 real AAPL daily bars."""
    return bars_to_frame(load("alpaca_bars_aapl_1day")["bars"]["AAPL"])


def frame_from(closes: list[float], *, highs=None, lows=None, volumes=None) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=len(closes), freq="D", tz="UTC", name="timestamp")
    return pd.DataFrame(
        {
            "open": closes,
            "high": highs if highs is not None else closes,
            "low": lows if lows is not None else closes,
            "close": closes,
            "volume": volumes if volumes is not None else [1_000.0] * len(closes),
            "trade_count": [10] * len(closes),
            "vwap": closes,
        },
        index=index,
    )


# --- SMA, checked against plain arithmetic -----------------------------------


def test_sma_equals_the_mean_of_the_trailing_window(bars: pd.DataFrame):
    # Independent of TA-Lib: the arithmetic mean of the last 20 closes.
    result = sma(bars, 20)

    expected = bars["close"].tail(20).mean()
    assert result.iloc[-1] == pytest.approx(expected)


def test_sma_matches_a_pandas_rolling_mean_everywhere(bars: pd.DataFrame):
    result = sma(bars, 50)
    expected = bars["close"].rolling(50).mean()

    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_sma_of_a_constant_series_is_that_constant():
    result = sma(frame_from([7.0] * 30), 20)

    assert result.iloc[-1] == pytest.approx(7.0)


# --- warm-up honesty ---------------------------------------------------------


def test_the_warm_up_period_stays_nan(bars: pd.DataFrame):
    result = sma(bars, 20)

    # 19 bars of no answer, then answers.
    assert result.iloc[:19].isna().all()
    assert result.iloc[19:].notna().all()


def test_a_200_day_average_of_82_days_is_nan_throughout(bars: pd.DataFrame):
    # The honest answer. Quietly computing it over a shorter window would hand
    # an agent a number that looks like a 200-day trend and is not one.
    assert len(bars) == 82

    assert sma(bars, 200).isna().all()


def test_indicators_on_an_empty_frame_are_empty_not_an_error():
    empty = bars_to_frame([])

    assert rsi(empty).empty
    assert sma(empty, 20).empty
    assert atr(empty).empty
    assert macd(empty).empty


def test_a_frame_missing_a_column_says_which_one():
    incomplete = frame_from([1.0] * 30).drop(columns="high")

    with pytest.raises(ValueError, match="high"):
        atr(incomplete)


# --- RSI, hand-worked --------------------------------------------------------


def test_rsi_of_a_series_that_only_rises_is_100():
    # No losses at all, so RS is infinite and RSI saturates. Computable on
    # paper: RSI = 100 - 100/(1 + avg_gain/avg_loss), avg_loss = 0.
    result = rsi(frame_from([float(i) for i in range(1, 40)]))

    assert result.iloc[-1] == pytest.approx(100.0)


def test_rsi_of_a_series_that_only_falls_is_0():
    result = rsi(frame_from([float(i) for i in range(40, 1, -1)]))

    assert result.iloc[-1] == pytest.approx(0.0)


def test_rsi_of_an_evenly_alternating_series_oscillates_around_50():
    # Equal gains and losses give RS = 1, so the *seed* RSI is exactly 50. The
    # smoothed value then straddles it, sitting a little high after an up day
    # and a little low after a down one — it does not settle on 50, and a test
    # demanding that it does would be asserting the wrong thing.
    closes = [100.0 + (1.0 if i % 2 else 0.0) for i in range(60)]

    result = rsi(frame_from(closes))
    after_a_gain, after_a_loss = result.iloc[-1], result.iloc[-2]

    assert after_a_loss < 50 < after_a_gain
    assert (after_a_gain + after_a_loss) / 2 == pytest.approx(50.0, abs=0.5)


def test_the_first_rsi_value_matches_wilders_definition_computed_by_hand():
    # Wilder's first RSI is the simple mean of the first `period` gains over
    # the simple mean of the first `period` losses. Computed here with pandas
    # arithmetic, deliberately not with TA-Lib.
    period = 14
    closes = [
        44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
        45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28,
    ]
    frame = frame_from(closes)

    change = pd.Series(closes).diff()
    average_gain = change[1 : period + 1].clip(lower=0).mean()
    average_loss = (-change[1 : period + 1].clip(upper=0)).mean()
    expected = 100 - 100 / (1 + average_gain / average_loss)

    first = rsi(frame, period).dropna().iloc[0]

    assert first == pytest.approx(expected, abs=1e-6)


def test_rsi_stays_within_its_bounds(bars: pd.DataFrame):
    result = rsi(bars).dropna()

    assert not result.empty
    assert result.between(0, 100).all()


# --- MACD, checked by its defining identities --------------------------------


def test_the_histogram_is_the_macd_line_minus_its_signal(bars: pd.DataFrame):
    # True by definition, whatever the smoothing.
    result = macd(bars).dropna()

    assert not result.empty
    pd.testing.assert_series_equal(
        result["macd_hist"],
        (result["macd"] - result["macd_signal"]).rename("macd_hist"),
    )


def test_the_macd_line_is_the_fast_ema_minus_the_slow_one():
    # Checked on a long series, where the two implementations agree to machine
    # precision. See the seeding test below for why 82 bars would not.
    closes = 100 + np.cumsum(np.random.default_rng(7).normal(0, 1, 600))
    frame = frame_from(list(closes))

    result = macd(frame)
    close = frame["close"]
    expected = (
        close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    )

    assert result["macd"].iloc[-1] == pytest.approx(expected.iloc[-1], rel=1e-9)


def test_a_short_history_makes_macd_depend_on_the_seeding_convention():
    # Worth knowing before an agent reasons about a MACD value. TA-Lib seeds
    # its EMA with a simple average of the first `slow` closes; the other
    # common convention seeds with the first close. The choice decays away, but
    # on ~82 bars the two still differ by several percent, and on a fresh
    # listing they differ a lot. Recorded as behaviour, not asserted as good.
    closes = 100 + np.cumsum(np.random.default_rng(7).normal(0, 1, 82))
    frame = frame_from(list(closes))

    ours = macd(frame)["macd"].iloc[-1]
    seeded_from_first_close = (
        frame["close"].ewm(span=12, adjust=False).mean()
        - frame["close"].ewm(span=26, adjust=False).mean()
    ).iloc[-1]

    assert ours != pytest.approx(seeded_from_first_close, rel=1e-3)
    assert abs(ours - seeded_from_first_close) < 0.1


def test_the_macd_of_a_flat_series_is_zero():
    result = macd(frame_from([50.0] * 80)).dropna()

    assert result["macd"].iloc[-1] == pytest.approx(0.0, abs=1e-9)
    assert result["macd_hist"].iloc[-1] == pytest.approx(0.0, abs=1e-9)


# --- Bollinger ---------------------------------------------------------------


def test_the_middle_band_is_the_simple_moving_average(bars: pd.DataFrame):
    bands = bollinger(bars, period=20)

    pd.testing.assert_series_equal(
        bands["bb_middle"], sma(bars, 20), check_names=False
    )


def test_the_bands_use_the_population_deviation_not_the_sample_one(bars: pd.DataFrame):
    # TA-Lib and the original definition use ddof=0. pandas defaults to ddof=1,
    # so a hand-rolled comparison disagrees unless it says so — which is the
    # whole reason this test exists.
    bands = bollinger(bars, period=20, stddev=2.0)
    window = bars["close"].tail(20)

    population = window.std(ddof=0)
    sample = window.std(ddof=1)
    expected_upper = window.mean() + 2 * population

    assert bands["bb_upper"].iloc[-1] == pytest.approx(expected_upper)
    assert bands["bb_upper"].iloc[-1] != pytest.approx(window.mean() + 2 * sample)


def test_the_bands_straddle_the_middle_symmetrically(bars: pd.DataFrame):
    bands = bollinger(bars).dropna()

    above = bands["bb_upper"] - bands["bb_middle"]
    below = bands["bb_middle"] - bands["bb_lower"]
    pd.testing.assert_series_equal(above, below, check_names=False)


def test_a_flat_series_has_zero_width_bands():
    bands = bollinger(frame_from([12.0] * 40)).dropna()

    assert bands["bb_upper"].iloc[-1] == pytest.approx(12.0)
    assert bands["bb_lower"].iloc[-1] == pytest.approx(12.0)


# --- ATR ---------------------------------------------------------------------


def test_the_first_atr_is_the_mean_of_the_first_true_ranges():
    # Wilder seeds ATR with a simple average of the first `period` true ranges.
    # True range here is high - low, since the frame has no gaps.
    period = 14
    highs = [10.0 + i * 0.5 for i in range(30)]
    lows = [9.0 + i * 0.5 for i in range(30)]
    closes = [9.5 + i * 0.5 for i in range(30)]
    frame = frame_from(closes, highs=highs, lows=lows)

    first = atr(frame, period).dropna().iloc[0]

    # Every true range is max(h-l, |h-prev_close|, |l-prev_close|) = 1.0 here.
    assert first == pytest.approx(1.0)


def test_atr_is_never_negative(bars: pd.DataFrame):
    result = atr(bars).dropna()

    assert not result.empty
    assert (result >= 0).all()


def test_atr_is_in_price_units_not_percent(bars: pd.DataFrame):
    # A ~$300 stock's daily range is dollars, not a fraction.
    result = atr(bars).dropna()

    assert 0.5 < result.iloc[-1] < 50


# --- volume vs its average ---------------------------------------------------


def test_a_tripled_volume_reads_as_three():
    volumes = [1_000.0] * 20 + [3_000.0]
    closes = [50.0] * 21

    result = volume_vs_average(frame_from(closes, volumes=volumes), period=20)

    assert result.iloc[-1] == pytest.approx(3.0)


def test_the_average_excludes_the_current_bar():
    # Including today damps exactly the spike being measured: a genuine 3x
    # would read as 2.73 against a 20-day window that already contains it.
    volumes = [1_000.0] * 20 + [3_000.0]
    frame = frame_from([50.0] * 21, volumes=volumes)

    result = volume_vs_average(frame, period=20)
    including_today = frame["volume"] / frame["volume"].rolling(20).mean()

    assert result.iloc[-1] == pytest.approx(3.0)
    assert including_today.iloc[-1] == pytest.approx(2.727, abs=0.01)


@pytest.mark.parametrize(
    "multiple,damped_to",
    [(3, 2.73), (10, 6.90), (50, 14.49), (1000, 19.63)],
)
def test_including_the_current_bar_would_saturate(multiple: int, damped_to: float):
    # The reason for the choice above, and the one that actually decides it.
    # Including today does not merely understate a spike, it *caps* it: with a
    # 20-day window the ratio cannot exceed 20 however extreme the day, so a
    # 50x and a 1000x day come out nearly the same. A screener that ranks by
    # unusualness would be blind at exactly the end that matters.
    volumes = [1_000.0] * 20 + [1_000.0 * multiple]
    frame = frame_from([50.0] * 21, volumes=volumes)

    ours = volume_vs_average(frame, period=20).iloc[-1]
    including_today = (frame["volume"] / frame["volume"].rolling(20).mean()).iloc[-1]

    assert ours == pytest.approx(float(multiple))
    assert including_today == pytest.approx(damped_to, abs=0.01)
    assert including_today < 20  # the ceiling, whatever the multiple


def test_steady_volume_reads_as_one():
    result = volume_vs_average(frame_from([50.0] * 30), period=20)

    assert result.iloc[-1] == pytest.approx(1.0)


def test_the_volume_ratio_warms_up_as_nan():
    frame = frame_from([50.0] * 25)

    result = volume_vs_average(frame, period=20)

    # One extra NaN over a plain rolling mean, because the window is shifted.
    assert result.iloc[:20].isna().all()
    assert result.iloc[20:].notna().all()


def test_the_ratio_on_real_bars_is_plausible(bars: pd.DataFrame):
    result = volume_vs_average(bars).dropna()

    assert not result.empty
    assert (result > 0).all()
    assert result.max() < 20


# --- the combined frame ------------------------------------------------------


def test_add_indicators_appends_every_column(bars: pd.DataFrame):
    enriched = add_indicators(bars)

    for column in (
        "rsi_14",
        "sma_20",
        "sma_50",
        "sma_200",
        "atr_14",
        "macd",
        "macd_signal",
        "macd_hist",
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "volume_vs_20d_avg",
    ):
        assert column in enriched.columns


def test_add_indicators_keeps_the_original_columns_and_index(bars: pd.DataFrame):
    enriched = add_indicators(bars)

    assert list(bars.columns) == list(enriched.columns)[: len(bars.columns)]
    pd.testing.assert_index_equal(bars.index, enriched.index)
    pd.testing.assert_series_equal(bars["close"], enriched["close"])


def test_add_indicators_does_not_mutate_the_input(bars: pd.DataFrame):
    before = bars.copy()

    add_indicators(bars)

    pd.testing.assert_frame_equal(bars, before)


def test_the_enriched_frame_holds_no_infinities(bars: pd.DataFrame):
    enriched = add_indicators(bars)

    assert not np.isinf(enriched.select_dtypes("float64").to_numpy()).any()
