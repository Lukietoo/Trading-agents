# Alpaca paper API access. The AlpacaClient protocol is the seam the HTTP
# tests fake; HttpAlpacaClient is the real implementation.

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel

ChartPeriod = Literal["1M", "3M", "1Y"]


class AlpacaAccount(BaseModel):
    equity: float
    cash: float
    last_equity: float


class AlpacaPosition(BaseModel):
    symbol: str
    qty: float
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pl: float
    # Fraction, not percent: +6.7% arrives as 0.067.
    unrealized_plpc: float


class HistoryPoint(BaseModel):
    """One portfolio-history sample: epoch seconds and equity."""

    t: int
    v: float


class AlpacaClient(Protocol):
    async def get_account(self) -> AlpacaAccount: ...

    async def get_week_ago_equity(self) -> float | None: ...

    async def get_positions(self) -> list[AlpacaPosition]: ...

    async def get_recent_closes(self, symbols: list[str]) -> dict[str, list[float]]: ...

    async def get_portfolio_history(self) -> dict[ChartPeriod, list[HistoryPoint]]: ...


SPARKLINE_CLOSES = 10


class HttpAlpacaClient:
    def __init__(self, base_url: str, key_id: str, secret_key: str, data_base_url: str = "https://data.alpaca.markets"):
        # Accept the base URL with or without a trailing /v2 — both forms
        # circulate in Alpaca docs and env files.
        self._base_url = base_url.rstrip("/").removesuffix("/v2")
        self._data_base_url = data_base_url.rstrip("/").removesuffix("/v2")
        self._headers = {
            "APCA-API-KEY-ID": key_id,
            "APCA-API-SECRET-KEY": secret_key,
        }

    async def get_account(self) -> AlpacaAccount:
        async with httpx.AsyncClient(headers=self._headers) as http:
            response = await http.get(f"{self._base_url}/v2/account")
            response.raise_for_status()
        return AlpacaAccount.model_validate(response.json())

    async def get_week_ago_equity(self) -> float | None:
        async with httpx.AsyncClient(headers=self._headers) as http:
            response = await http.get(
                f"{self._base_url}/v2/account/portfolio/history",
                params={"period": "1W", "timeframe": "1D"},
            )
            response.raise_for_status()
        equities = [e for e in response.json().get("equity", []) if e is not None]
        return equities[0] if equities else None

    async def get_positions(self) -> list[AlpacaPosition]:
        async with httpx.AsyncClient(headers=self._headers) as http:
            response = await http.get(f"{self._base_url}/v2/positions")
            response.raise_for_status()
        return [AlpacaPosition.model_validate(p) for p in response.json()]

    async def get_portfolio_history(self) -> dict[ChartPeriod, list[HistoryPoint]]:
        # Alpaca spells the one-year period "1A"; the wire contract keys the
        # series by the frontend's period names.
        periods: dict[ChartPeriod, str] = {"1M": "1M", "3M": "3M", "1Y": "1A"}

        async def fetch(http: httpx.AsyncClient, alpaca_period: str) -> list[HistoryPoint]:
            response = await http.get(
                f"{self._base_url}/v2/account/portfolio/history",
                params={"period": alpaca_period, "timeframe": "1D"},
            )
            response.raise_for_status()
            body = response.json()
            return [
                HistoryPoint(t=t, v=v)
                for t, v in zip(body.get("timestamp", []), body.get("equity", []))
                if v is not None
            ]

        async with httpx.AsyncClient(headers=self._headers) as http:
            series = await asyncio.gather(*(fetch(http, p) for p in periods.values()))
        return dict(zip(periods.keys(), series))

    async def get_recent_closes(self, symbols: list[str]) -> dict[str, list[float]]:
        if not symbols:
            return {}
        # Without an explicit start, the bars endpoint defaults to today only —
        # reach back far enough to cover SPARKLINE_CLOSES trading days.
        start = datetime.now(timezone.utc) - timedelta(days=SPARKLINE_CLOSES * 2 + 5)
        async with httpx.AsyncClient(headers=self._headers) as http:
            response = await http.get(
                f"{self._data_base_url}/v2/stocks/bars",
                params={
                    "symbols": ",".join(symbols),
                    "timeframe": "1Day",
                    "start": start.date().isoformat(),
                    # IEX feed is available on free paper-account keys.
                    "feed": "iex",
                    # The limit counts bars across all symbols, not per symbol.
                    "limit": 10_000,
                },
            )
            response.raise_for_status()
        bars_by_symbol = response.json().get("bars") or {}
        return {
            symbol: [bar["c"] for bar in bars[-SPARKLINE_CLOSES:]]
            for symbol, bars in bars_by_symbol.items()
        }
