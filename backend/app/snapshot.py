# Assembles the dashboard snapshot from Alpaca account numbers.
#
# Numeric wire contract: every field is a raw number (percentages rounded to
# 2 decimals); all display formatting lives in the frontend.

from pydantic import BaseModel

from app.alpaca import AlpacaAccount, AlpacaPosition, ChartPeriod, HistoryPoint


class PositionSnapshot(BaseModel):
    ticker: str
    shares: float
    avgCost: float
    currentPrice: float
    value: float
    gain: float
    gainPct: float
    """Recent daily closes, oldest first — the frontend derives sparkline
    geometry from these raw numbers."""
    closes: list[float]


class AllocationEntry(BaseModel):
    ticker: str
    """Share of the invested (non-cash) portfolio value."""
    weightPct: float


class Snapshot(BaseModel):
    portfolioValue: float
    cash: float
    totalPnl: float
    totalPnlPct: float
    dailyChange: float
    dailyChangePct: float
    cashPct: float
    weekChangePct: float | None
    positions: list[PositionSnapshot]
    allocation: list[AllocationEntry]
    """Portfolio-history series keyed by chart period (1M/3M/1Y) — raw
    timestamp/value pairs; chart geometry is derived client-side."""
    history: dict[ChartPeriod, list[HistoryPoint]]


def _pct(part: float, whole: float) -> float:
    return round(part / whole * 100, 2) if whole else 0.0


def build_snapshot(
    account: AlpacaAccount,
    week_ago_equity: float | None,
    positions: list[AlpacaPosition],
    closes: dict[str, list[float]],
    history: dict[ChartPeriod, list[HistoryPoint]],
    pnl_baseline: float,
) -> Snapshot:
    daily_change = account.equity - account.last_equity
    invested = sum(p.market_value for p in positions)
    return Snapshot(
        portfolioValue=account.equity,
        cash=account.cash,
        totalPnl=account.equity - pnl_baseline,
        totalPnlPct=_pct(account.equity - pnl_baseline, pnl_baseline),
        dailyChange=daily_change,
        dailyChangePct=_pct(daily_change, account.last_equity),
        cashPct=_pct(account.cash, account.equity),
        weekChangePct=(
            _pct(account.equity - week_ago_equity, week_ago_equity)
            if week_ago_equity is not None
            else None
        ),
        positions=[
            PositionSnapshot(
                ticker=p.symbol,
                shares=p.qty,
                avgCost=p.avg_entry_price,
                currentPrice=p.current_price,
                value=p.market_value,
                gain=p.unrealized_pl,
                gainPct=round(p.unrealized_plpc * 100, 2),
                closes=closes.get(p.symbol, []),
            )
            for p in positions
        ],
        allocation=[
            AllocationEntry(ticker=p.symbol, weightPct=_pct(p.market_value, invested))
            for p in positions
        ],
        history=history,
    )
