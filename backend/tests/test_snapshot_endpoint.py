# HTTP-boundary tests: run the FastAPI app with a fake Alpaca client injected,
# no network. This is the backend test seam every later slice builds on.

from fastapi.testclient import TestClient

from app.alpaca import AlpacaAccount, AlpacaPosition
from app.main import create_app


class FakeAlpacaClient:
    """In-memory stand-in for the Alpaca paper API."""

    def __init__(
        self,
        account: AlpacaAccount,
        week_ago_equity: float | None = None,
        positions: list[AlpacaPosition] | None = None,
        closes: dict[str, list[float]] | None = None,
    ):
        self._account = account
        self._week_ago_equity = week_ago_equity
        self._positions = positions or []
        self._closes = closes or {}

    async def get_account(self) -> AlpacaAccount:
        return self._account

    async def get_week_ago_equity(self) -> float | None:
        return self._week_ago_equity

    async def get_positions(self) -> list[AlpacaPosition]:
        return self._positions

    async def get_recent_closes(self, symbols: list[str]) -> dict[str, list[float]]:
        return {s: self._closes[s] for s in symbols if s in self._closes}


def make_client(
    account: AlpacaAccount,
    week_ago_equity: float | None = None,
    baseline: float = 100_000.0,
    positions: list[AlpacaPosition] | None = None,
    closes: dict[str, list[float]] | None = None,
) -> TestClient:
    app = create_app(
        FakeAlpacaClient(account, week_ago_equity, positions, closes),
        pnl_baseline=baseline,
    )
    return TestClient(app)


def test_snapshot_returns_account_summary_numbers():
    # Worked example: the design-reference account. Equity $104,820 with
    # $18,340 cash, up $4,820 all-time vs the $100k baseline, down $312
    # since open (last_equity $105,132), up 4.8% on the week.
    client = make_client(
        AlpacaAccount(equity=104_820.0, cash=18_340.0, last_equity=105_132.0),
        week_ago_equity=100_019.0,
    )

    body = client.get("/api/snapshot").json()

    assert body["portfolioValue"] == 104_820.0
    assert body["cash"] == 18_340.0
    assert body["totalPnl"] == 4_820.0
    assert body["totalPnlPct"] == 4.82
    assert body["dailyChange"] == -312.0
    assert body["dailyChangePct"] == -0.3
    assert body["cashPct"] == 17.5
    assert body["weekChangePct"] == 4.8


def test_week_change_is_null_when_no_portfolio_history():
    # A brand-new paper account has no history yet.
    body = make_client(
        AlpacaAccount(equity=100_000.0, cash=100_000.0, last_equity=100_000.0),
        week_ago_equity=None,
    ).get("/api/snapshot").json()

    assert body["weekChangePct"] is None


def test_total_pnl_measured_from_configured_baseline():
    body = make_client(
        AlpacaAccount(equity=104_820.0, cash=18_340.0, last_equity=105_132.0),
        baseline=96_400.0,
    ).get("/api/snapshot").json()

    assert body["totalPnl"] == 8_420.0
    assert body["totalPnlPct"] == 8.73


def test_snapshot_carries_positions_with_recent_closes():
    # Worked example: the design-reference AAPL row — 12 shares at $229.67
    # average, $245.00 now, worth $2,940, up $184 (+6.7%).
    body = make_client(
        AlpacaAccount(equity=104_820.0, cash=18_340.0, last_equity=105_132.0),
        positions=[
            AlpacaPosition(
                symbol="AAPL",
                qty=12,
                avg_entry_price=229.67,
                current_price=245.0,
                market_value=2_940.0,
                unrealized_pl=184.0,
                unrealized_plpc=0.0668,
            )
        ],
        closes={"AAPL": [238.0, 240.5, 239.0, 243.2, 245.0]},
    ).get("/api/snapshot").json()

    assert body["positions"] == [
        {
            "ticker": "AAPL",
            "shares": 12,
            "avgCost": 229.67,
            "currentPrice": 245.0,
            "value": 2_940.0,
            "gain": 184.0,
            "gainPct": 6.68,
            "closes": [238.0, 240.5, 239.0, 243.2, 245.0],
        }
    ]


def test_allocation_weights_are_shares_of_invested_value():
    body = make_client(
        AlpacaAccount(equity=104_820.0, cash=92_120.0, last_equity=104_820.0),
        positions=[
            AlpacaPosition(symbol="AAPL", qty=12, avg_entry_price=229.67, current_price=245.0, market_value=2_940.0, unrealized_pl=184.0, unrealized_plpc=0.0668),
            AlpacaPosition(symbol="NVDA", qty=8, avg_entry_price=1_065.0, current_price=1_220.0, market_value=9_760.0, unrealized_pl=1_240.0, unrealized_plpc=0.1456),
        ],
    ).get("/api/snapshot").json()

    # Invested total $12,700: AAPL 2940/12700, NVDA 9760/12700.
    assert body["allocation"] == [
        {"ticker": "AAPL", "weightPct": 23.15},
        {"ticker": "NVDA", "weightPct": 76.85},
    ]


def test_empty_account_has_no_positions_or_allocation():
    body = make_client(
        AlpacaAccount(equity=100_000.0, cash=100_000.0, last_equity=100_000.0)
    ).get("/api/snapshot").json()

    assert body["positions"] == []
    assert body["allocation"] == []


def test_position_without_close_history_gets_empty_closes():
    body = make_client(
        AlpacaAccount(equity=100_000.0, cash=97_060.0, last_equity=100_000.0),
        positions=[
            AlpacaPosition(symbol="AAPL", qty=12, avg_entry_price=229.67, current_price=245.0, market_value=2_940.0, unrealized_pl=184.0, unrealized_plpc=0.0668)
        ],
        closes={},
    ).get("/api/snapshot").json()

    assert body["positions"][0]["closes"] == []


def test_snapshot_ok_status_and_json_content_type():
    response = make_client(
        AlpacaAccount(equity=100_000.0, cash=100_000.0, last_equity=100_000.0)
    ).get("/api/snapshot")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
