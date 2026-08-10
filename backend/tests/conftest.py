# Shared builders for the decision-side tests. The defaults are one worked
# example — a BUY on NVDA flagged by a volume spike — so assertions read
# against realistic values rather than placeholders.
#
# Also home to the network guard, which is enforced for every test in the
# suite rather than asserted once.

import socket
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app.alpaca import AlpacaAccount
from app.data import MarketData
from app.data.alpaca_client import AlpacaDataClient
from app.data.cache import Cache
from app.data.finnhub_client import FinnhubClient
from app.data.fred_client import FredClient
from app.data.http import RetryPolicy
from app.data.rate_limit import RateLimiter
from app.decisions.schema import (
    Action,
    Candidate,
    Conviction,
    Decision,
    DecisionStatus,
    ModelConfig,
    Outcome,
    RunCost,
    Trigger,
)
from tests.fixtures import load

VOLUME_SPIKE = Trigger(name="volume_spike", value=3.4, threshold=2.0)


class NetworkAccessAttempted(RuntimeError):
    """A test tried to open a real socket.

    Every external call in this suite goes through an httpx MockTransport or a
    fake. A test reaching the network is either a bug in the test or a client
    that stopped honouring its injected transport — and either way it would
    make CI depend on the weather, a rate limit, and a live API key.
    """


@pytest.fixture(scope="session", autouse=True)
def forbid_network():
    """Make a real connection raise, for the whole session.

    The phase spec asks that pytest passes with no network access. Asserting
    that once proves nothing about the other tests, so it is enforced here
    instead: any socket connect fails, everywhere, unconditionally.
    """
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def refuse(self, address, *args, **kwargs):
        raise NetworkAccessAttempted(
            f"A test tried to connect to {address}. Tests must use an httpx "
            "MockTransport or a fake — see tests/fixtures/ for the recorded "
            "responses."
        )

    socket.socket.connect = refuse
    socket.socket.connect_ex = refuse
    try:
        yield
    finally:
        socket.socket.connect = real_connect
        socket.socket.connect_ex = real_connect_ex


@pytest.fixture
def make_decision() -> Callable[..., Decision]:
    def _make(
        decision_id: str = "dec-20260807-nvda",
        ticker: str = "NVDA",
        as_of_date: str = "2026-08-07",
        created_at: str = "2026-08-07T13:05:00Z",
        action: Action = "BUY",
        conviction: Conviction = "high",
        status: DecisionStatus = "pending",
        outcome: Outcome | None = None,
    ) -> Decision:
        return Decision(
            id=decision_id,
            ticker=ticker,
            asOfDate=as_of_date,
            createdAt=created_at,
            triggers=[VOLUME_SPIKE],
            action=action,
            conviction=conviction,
            thesis="Volume three times the 20-day average on an earnings beat.",
            reportsRef=f"reports/{decision_id}",
            modelConfig=ModelConfig(
                provider="litellm",
                deepModel="gemini-2.5-pro",
                quickModel="llama-3.3-70b",
                debateRounds=1,
            ),
            cost=RunCost(inputTokens=18_432, outputTokens=2_104, estimatedUsd=0.0231),
            status=status,
            outcome=outcome,
        )

    return _make


@pytest.fixture
def make_candidate() -> Callable[..., Candidate]:
    def _make(
        ticker: str = "NVDA",
        as_of_date: str = "2026-08-07",
        rank: int = 1,
        analyzed: bool = False,
    ) -> Candidate:
        return Candidate(
            ticker=ticker,
            asOfDate=as_of_date,
            triggers=[VOLUME_SPIKE],
            rank=rank,
            analyzed=analyzed,
        )

    return _make


@pytest.fixture
def measured_outcome() -> Outcome:
    return Outcome(
        return1dPct=1.42,
        return5dPct=3.08,
        return20dPct=None,
        alpha1dPct=0.91,
        alpha5dPct=2.15,
        alpha20dPct=None,
        measuredAt="2026-08-14T22:00:00Z",
    )


# --- the data layer, fully wired and entirely offline ------------------------
#
# Shared because both the facade tests and the phase acceptance tests need the
# same wiring. A frozen clock keeps window arithmetic deterministic.

NOW = datetime(2026, 8, 9, 14, 30, tzinfo=UTC)


class MarketClock:
    """A clock shared by the facade and every client under it.

    Shared deliberately. Giving each client its own frozen clock let a cache
    bug survive a test that advanced only the facade's: the window end is
    computed inside the Alpaca client, so that is the clock that has to move.
    """

    def __init__(self, now: datetime = NOW):
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


class Router:
    """Serves every fixture by URL fragment and records the requests."""

    ROUTES = {
        "/v2/stocks/bars": "alpaca_bars_aapl_1day",
        "/v2/stocks/snapshots": "alpaca_snapshot_aapl",
        "most-actives": "alpaca_most_actives",
        "movers": "alpaca_movers",
        "/stock/metric": "finnhub_metrics_aapl",
        "/company-news": "finnhub_company_news_aapl",
        "/calendar/earnings": "finnhub_earnings_calendar_aapl",
        "/stock/insider-transactions": "finnhub_insider_transactions_aapl",
        "/series/observations": "fred_unrate",
    }

    def __init__(self):
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        for fragment, fixture in self.ROUTES.items():
            if fragment in request.url.path:
                return httpx.Response(200, json=load(fixture))
        return httpx.Response(404, json={"message": f"no route for {request.url.path}"})

    def paths(self) -> list[str]:
        return [str(request.url.path) for request in self.requests]

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]


class FakeAccountClient:
    async def get_account(self) -> AlpacaAccount:
        return AlpacaAccount(equity=101_240.5, cash=24_000.0, last_equity=100_980.0)


@pytest.fixture
def router() -> Router:
    return Router()


@pytest.fixture
def market_clock() -> MarketClock:
    return MarketClock()


@pytest.fixture
def market(tmp_path: Path, router: Router, market_clock: MarketClock) -> MarketData:
    """A fully injected facade: no .env, no network, no real waiting."""
    transport = httpx.MockTransport(router)
    policy = RetryPolicy(attempts=2, base_delay=0, jitter=False)
    cache = Cache(tmp_path / "cache.sqlite3", now=market_clock)

    return MarketData(
        cache=cache,
        now=market_clock,
        alpaca=AlpacaDataClient(
            key_id="k",
            secret_key="s",
            account_client=FakeAccountClient(),
            cache=cache,
            transport=transport,
            policy=policy,
            now=market_clock,
        ),
        finnhub=FinnhubClient(
            api_key="k",
            cache=cache,
            limiter=RateLimiter(1000, 60.0),
            transport=transport,
            policy=policy,
            now=market_clock,
        ),
        fred=FredClient(
            api_key="k",
            cache=cache,
            transport=transport,
            policy=policy,
            now=market_clock,
        ),
    )
