# Technical indicators over a bars DataFrame.
#
# Pure functions: no network, no cache, no state. Every one takes the frame
# app.data.alpaca_client.bars_to_frame produces and returns a Series or frame
# on the same index.
#
# TA-Lib does the arithmetic — it is the reference implementation, and
# hand-rolling Wilder's smoothing is how subtly wrong RSI values get into an
# agent's argument. It works in numpy arrays, so each function here is the thin
# DataFrame-in/DataFrame-out wrapper around it.
#
# Warm-up periods stay NaN. They are never filled, back-filled, or quietly
# computed over a shorter window: a 200-day average of 82 days of data does not
# exist, and saying so is the only honest answer. Callers check for NaN.
#
# One caveat worth knowing before an agent reasons about a MACD value: TA-Lib
# seeds each EMA with a simple average of the first `period` closes, while the
# other common convention seeds with the first close alone. The difference
# decays, but it is still a few percent at ~80 bars and large on a recent
# listing. Prefer a long window when the absolute MACD level matters, rather
# than only its sign or its crossings.

from typing import Final

import numpy as np
import pandas as pd
import talib

RSI_PERIOD: Final = 14
ATR_PERIOD: Final = 14
BOLLINGER_PERIOD: Final = 20
BOLLINGER_STDDEV: Final = 2.0
MACD_FAST: Final = 12
MACD_SLOW: Final = 26
MACD_SIGNAL: Final = 9
VOLUME_AVERAGE_PERIOD: Final = 20
SMA_PERIODS: Final = (20, 50, 200)


def _column(bars: pd.DataFrame, name: str) -> np.ndarray:
    """One column as the float64 array TA-Lib requires.

    Raises on a missing column rather than letting a KeyError surface from
    inside TA-Lib, where the message says nothing about which frame was wrong.
    """
    if name not in bars.columns:
        raise ValueError(
            f"bars frame has no {name!r} column. Got: {list(bars.columns)}. "
            "Expected the frame from alpaca_client.bars_to_frame."
        )
    return bars[name].to_numpy(dtype="float64")


def rsi(bars: pd.DataFrame, period: int = RSI_PERIOD) -> pd.Series:
    """Wilder's RSI. NaN until `period` bars have accumulated."""
    return pd.Series(
        talib.RSI(_column(bars, "close"), timeperiod=period),
        index=bars.index,
        name=f"rsi_{period}",
    )


def sma(bars: pd.DataFrame, period: int) -> pd.Series:
    return pd.Series(
        talib.SMA(_column(bars, "close"), timeperiod=period),
        index=bars.index,
        name=f"sma_{period}",
    )


def atr(bars: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    """Average True Range — volatility in price units, not percent."""
    return pd.Series(
        talib.ATR(
            _column(bars, "high"),
            _column(bars, "low"),
            _column(bars, "close"),
            timeperiod=period,
        ),
        index=bars.index,
        name=f"atr_{period}",
    )


def macd(
    bars: pd.DataFrame,
    fast: int = MACD_FAST,
    slow: int = MACD_SLOW,
    signal: int = MACD_SIGNAL,
) -> pd.DataFrame:
    """MACD line, its signal line, and the histogram between them."""
    line, signal_line, histogram = talib.MACD(
        _column(bars, "close"),
        fastperiod=fast,
        slowperiod=slow,
        signalperiod=signal,
    )
    return pd.DataFrame(
        {"macd": line, "macd_signal": signal_line, "macd_hist": histogram},
        index=bars.index,
    )


def bollinger(
    bars: pd.DataFrame,
    period: int = BOLLINGER_PERIOD,
    stddev: float = BOLLINGER_STDDEV,
) -> pd.DataFrame:
    """Bollinger Bands.

    Note the bands use the **population** standard deviation (ddof=0), which is
    what TA-Lib and the original definition use. pandas' .std() defaults to the
    sample deviation (ddof=1), so a comparison against a hand-rolled pandas
    version disagrees slightly unless it passes ddof=0.
    """
    upper, middle, lower = talib.BBANDS(
        _column(bars, "close"),
        timeperiod=period,
        nbdevup=stddev,
        nbdevdn=stddev,
    )
    return pd.DataFrame(
        {"bb_upper": upper, "bb_middle": middle, "bb_lower": lower},
        index=bars.index,
    )


def volume_vs_average(
    bars: pd.DataFrame, period: int = VOLUME_AVERAGE_PERIOD
) -> pd.Series:
    """Today's volume as a multiple of the trailing average. 3.0 means triple.

    Not a TA-Lib indicator — it is a rolling mean, so it stays hand-written.
    The window excludes the current bar: dividing volume by an average that
    already contains it damps exactly the spike the screener is looking for.

    NOTE: on Alpaca's free IEX feed, volume is one venue's share of the
    consolidated tape, not the whole. The ratio is still meaningful because
    both sides come from the same feed, but the absolute figures are not
    comparable with a full-market source.
    """
    if "volume" not in bars.columns:
        raise ValueError(
            f"bars frame has no 'volume' column. Got: {list(bars.columns)}."
        )
    volume = bars["volume"]
    average = volume.shift(1).rolling(window=period).mean()
    return (volume / average).rename(f"volume_vs_{period}d_avg")


def add_indicators(bars: pd.DataFrame) -> pd.DataFrame:
    """The bars frame with every indicator appended as a column.

    Returns a new frame; the input is not modified. Columns whose warm-up has
    not completed are NaN for those rows — with 82 bars, sma_200 is NaN
    throughout, and that is the correct answer rather than a defect.
    """
    enriched = bars.copy()
    enriched[f"rsi_{RSI_PERIOD}"] = rsi(bars)
    for period in SMA_PERIODS:
        enriched[f"sma_{period}"] = sma(bars, period)
    enriched[f"atr_{ATR_PERIOD}"] = atr(bars)
    for name, column in macd(bars).items():
        enriched[name] = column
    for name, column in bollinger(bars).items():
        enriched[name] = column
    enriched[f"volume_vs_{VOLUME_AVERAGE_PERIOD}d_avg"] = volume_vs_average(bars)
    return enriched
