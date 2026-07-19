# Alpaca paper API access. The AlpacaClient protocol is the seam the HTTP
# tests fake; HttpAlpacaClient is the real implementation.

from typing import Protocol

import httpx
from pydantic import BaseModel


class AlpacaAccount(BaseModel):
    equity: float
    cash: float
    last_equity: float


class AlpacaClient(Protocol):
    async def get_account(self) -> AlpacaAccount: ...

    async def get_week_ago_equity(self) -> float | None: ...


class HttpAlpacaClient:
    def __init__(self, base_url: str, key_id: str, secret_key: str):
        # Accept the base URL with or without a trailing /v2 — both forms
        # circulate in Alpaca docs and env files.
        self._base_url = base_url.rstrip("/").removesuffix("/v2")
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
