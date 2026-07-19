# Assembles the dashboard snapshot from Alpaca account numbers.
#
# Numeric wire contract: every field is a raw number (percentages rounded to
# 2 decimals); all display formatting lives in the frontend.

from pydantic import BaseModel

from app.alpaca import AlpacaAccount


class Snapshot(BaseModel):
    portfolioValue: float
    cash: float
    totalPnl: float
    totalPnlPct: float
    dailyChange: float
    dailyChangePct: float
    cashPct: float
    weekChangePct: float | None


def _pct(part: float, whole: float) -> float:
    return round(part / whole * 100, 2) if whole else 0.0


def build_snapshot(
    account: AlpacaAccount, week_ago_equity: float | None, pnl_baseline: float
) -> Snapshot:
    daily_change = account.equity - account.last_equity
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
    )
