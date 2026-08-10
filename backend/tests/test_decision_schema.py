# The wire contract is frontend/src/types/decisions.ts. These tests assert the
# exact JSON field names the TS interfaces declare — camelCase attributes with
# no alias layer — and that a model survives a round trip through them.

from collections.abc import Callable

import pytest
from pydantic import ValidationError

from app.decisions.schema import Candidate, Decision, Outcome, Trigger


def test_decision_json_field_names_match_the_typescript_interface(
    make_decision: Callable[..., Decision],
):
    decision = make_decision()

    assert decision.model_dump(mode="json") == {
        "id": "dec-20260807-nvda",
        "ticker": "NVDA",
        "asOfDate": "2026-08-07",
        "createdAt": "2026-08-07T13:05:00Z",
        "triggers": [{"name": "volume_spike", "value": 3.4, "threshold": 2.0}],
        "action": "BUY",
        "conviction": "high",
        "thesis": "Volume three times the 20-day average on an earnings beat.",
        "reportsRef": "reports/dec-20260807-nvda",
        "modelConfig": {
            "provider": "litellm",
            "deepModel": "gemini-2.5-pro",
            "quickModel": "llama-3.3-70b",
            "debateRounds": 1,
        },
        "cost": {"inputTokens": 18_432, "outputTokens": 2_104, "estimatedUsd": 0.0231},
        "status": "pending",
        "outcome": None,
    }


def test_decision_round_trips_through_json(
    make_decision: Callable[..., Decision], measured_outcome: Outcome
):
    decision = make_decision(outcome=measured_outcome)

    assert Decision.model_validate_json(decision.model_dump_json()) == decision


def test_outcome_json_field_names_carry_the_pct_suffix(measured_outcome: Outcome):
    # Percent fields keep the repo-wide `Pct` suffix, as PositionSnapshot.gainPct
    # and AllocationEntry.weightPct do. Alpha is measured against SPY.
    assert measured_outcome.model_dump(mode="json") == {
        "return1dPct": 1.42,
        "return5dPct": 3.08,
        "return20dPct": None,
        "alpha1dPct": 0.91,
        "alpha5dPct": 2.15,
        "alpha20dPct": None,
        "measuredAt": "2026-08-14T22:00:00Z",
    }


def test_unmeasured_outcome_is_all_nulls_not_zeros():
    # An unmeasured horizon is absent, never 0.0 — a synthetic zero would read
    # as a real flat return in the evaluation loop.
    unmeasured = Outcome(
        return1dPct=None,
        return5dPct=None,
        return20dPct=None,
        alpha1dPct=None,
        alpha5dPct=None,
        alpha20dPct=None,
        measuredAt=None,
    )

    assert set(unmeasured.model_dump(mode="json").values()) == {None}


def test_candidate_json_field_names_match_the_typescript_interface(
    make_candidate: Callable[..., Candidate],
):
    assert make_candidate().model_dump(mode="json") == {
        "ticker": "NVDA",
        "asOfDate": "2026-08-07",
        "triggers": [{"name": "volume_spike", "value": 3.4, "threshold": 2.0}],
        "rank": 1,
        "analyzed": False,
    }


def test_trigger_carries_the_value_and_the_threshold_it_crossed():
    assert Trigger(name="rsi_extreme", value=18.2, threshold=30.0).model_dump(
        mode="json"
    ) == {"name": "rsi_extreme", "value": 18.2, "threshold": 30.0}


def test_action_is_uppercase_and_rejects_a_trade_side(
    make_decision: Callable[..., Decision],
):
    # Action is BUY/SELL/HOLD, deliberately distinct from TradeSide's lowercase
    # buy/sell — that is an order side, this is a recorded call.
    with pytest.raises(ValidationError):
        make_decision(action="buy")


def test_conviction_and_status_reject_values_outside_the_glossary(
    make_decision: Callable[..., Decision],
):
    with pytest.raises(ValidationError):
        make_decision(conviction="HIGH")

    with pytest.raises(ValidationError):
        make_decision(status="filled")
