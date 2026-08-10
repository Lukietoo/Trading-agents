# The decision-side wire contract, mirroring frontend/src/types/decisions.ts.
# The frontend leads and the backend conforms (CONTEXT.md), so these models
# declare camelCase attribute names directly — the Python attribute name *is*
# the wire name, as in app/snapshot.py. No alias generator, no snake_case layer.
#
# Dates and timestamps are ISO strings, matching the `string` the TS interfaces
# declare, so a model round-trips through JSON and SQLite unchanged.

from typing import Literal

from pydantic import BaseModel

Action = Literal["BUY", "SELL", "HOLD"]
Conviction = Literal["low", "medium", "high"]
DecisionStatus = Literal["pending", "executed", "skipped", "expired"]


class Trigger(BaseModel):
    """The condition that made a ticker a Candidate, with the values that
    fired it."""

    name: str
    value: float
    threshold: float


class Candidate(BaseModel):
    """A ticker the screener flagged on a given date as worth analyzing.
    Says nothing about direction."""

    ticker: str
    """ISO date (YYYY-MM-DD) — the trading day the screener ran over."""
    asOfDate: str
    triggers: list[Trigger]
    """1 = most worth analyzing. Ranks attention, not conviction."""
    rank: int
    """False for a Skipped Candidate — the control group, kept deliberately."""
    analyzed: bool


class Outcome(BaseModel):
    """The realized result of a Decision. Every field is None until the horizon
    has passed and the evaluation job has filled it in."""

    return1dPct: float | None
    return5dPct: float | None
    return20dPct: float | None
    """Return relative to the benchmark (SPY)."""
    alpha1dPct: float | None
    alpha5dPct: float | None
    alpha20dPct: float | None
    """ISO timestamp of the measurement, None while unmeasured."""
    measuredAt: str | None


class ModelConfig(BaseModel):
    """What produced a Decision, recorded so outcomes can be attributed to it."""

    provider: str
    deepModel: str
    quickModel: str
    debateRounds: int


class RunCost(BaseModel):
    """Token spend for one Analysis Run."""

    inputTokens: int
    outputTokens: int
    estimatedUsd: float


class Decision(BaseModel):
    """The pipeline's recorded output for one ticker on one date. A record, not
    an order — it may never be executed, and it is immutable once written."""

    id: str
    ticker: str
    """ISO date (YYYY-MM-DD) — the trading day the Decision is about."""
    asOfDate: str
    """ISO timestamp the record was written."""
    createdAt: str
    """The triggers carried over from the Candidate this Decision came from."""
    triggers: list[Trigger]
    action: Action
    conviction: Conviction
    """Short natural-language rationale."""
    thesis: str
    """Pointer to the stored agent reports, which live outside the database."""
    reportsRef: str | None
    modelConfig: ModelConfig
    cost: RunCost
    status: DecisionStatus
    outcome: Outcome | None
