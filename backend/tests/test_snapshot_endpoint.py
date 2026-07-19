# HTTP-boundary tests: run the FastAPI app with a fake Alpaca client injected,
# no network. This is the backend test seam every later slice builds on.

from fastapi.testclient import TestClient

from app.alpaca import AlpacaAccount
from app.main import create_app


class FakeAlpacaClient:
    """In-memory stand-in for the Alpaca paper API."""

    def __init__(self, account: AlpacaAccount, week_ago_equity: float | None = None):
        self._account = account
        self._week_ago_equity = week_ago_equity

    async def get_account(self) -> AlpacaAccount:
        return self._account

    async def get_week_ago_equity(self) -> float | None:
        return self._week_ago_equity


def make_client(account: AlpacaAccount, week_ago_equity: float | None = None, baseline: float = 100_000.0) -> TestClient:
    app = create_app(FakeAlpacaClient(account, week_ago_equity), pnl_baseline=baseline)
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


def test_snapshot_ok_status_and_json_content_type():
    response = make_client(
        AlpacaAccount(equity=100_000.0, cash=100_000.0, last_equity=100_000.0)
    ).get("/api/snapshot")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
