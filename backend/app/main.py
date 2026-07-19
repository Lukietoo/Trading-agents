import os

from fastapi import FastAPI

from app.alpaca import AlpacaClient, HttpAlpacaClient
from app.snapshot import Snapshot, build_snapshot

# Until the reset-epoch ticket lands, total P&L is measured from the paper
# account's starting balance.
DEFAULT_PNL_BASELINE = 100_000.0


def create_app(alpaca: AlpacaClient, pnl_baseline: float = DEFAULT_PNL_BASELINE) -> FastAPI:
    app = FastAPI(title="Paper Trading Dashboard API")

    @app.get("/api/snapshot")
    async def snapshot() -> Snapshot:
        account = await alpaca.get_account()
        week_ago_equity = await alpaca.get_week_ago_equity()
        return build_snapshot(account, week_ago_equity, pnl_baseline)

    return app


def app_from_env() -> FastAPI:
    return create_app(
        HttpAlpacaClient(
            base_url=os.environ.get("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets"),
            key_id=os.environ["ALPACA_API_KEY_ID"],
            secret_key=os.environ["ALPACA_API_SECRET_KEY"],
        ),
        pnl_baseline=float(os.environ.get("PNL_BASELINE", DEFAULT_PNL_BASELINE)),
    )
