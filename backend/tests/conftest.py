# Shared builders for the decision-side tests. The defaults are one worked
# example — a BUY on NVDA flagged by a volume spike — so assertions read
# against realistic values rather than placeholders.

from collections.abc import Callable

import pytest

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

VOLUME_SPIKE = Trigger(name="volume_spike", value=3.4, threshold=2.0)


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
