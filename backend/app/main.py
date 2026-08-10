from fastapi import FastAPI

from app.alpaca import AlpacaClient, HttpAlpacaClient
from app.config import DEFAULT_PNL_BASELINE, load_config
from app.snapshot import Snapshot, build_snapshot


def create_app(alpaca: AlpacaClient, pnl_baseline: float = DEFAULT_PNL_BASELINE) -> FastAPI:
    app = FastAPI(title="Paper Trading Dashboard API")

    @app.get("/api/snapshot")
    async def snapshot() -> Snapshot:
        account = await alpaca.get_account()
        week_ago_equity = await alpaca.get_week_ago_equity()
        positions = await alpaca.get_positions()
        closes = await alpaca.get_recent_closes([p.symbol for p in positions])
        history = await alpaca.get_portfolio_history()
        return build_snapshot(account, week_ago_equity, positions, closes, history, pnl_baseline)

    return app


def app_from_env() -> FastAPI:
    config = load_config()
    return create_app(
        HttpAlpacaClient(
            base_url=config.alpaca_paper_base_url,
            key_id=config.alpaca_api_key_id,
            secret_key=config.alpaca_api_secret_key,
        ),
        pnl_baseline=config.pnl_baseline,
    )
