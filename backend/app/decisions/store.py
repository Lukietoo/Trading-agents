# SQLite persistence for Candidates and Decisions.
#
# A Decision is immutable once written (CONTEXT.md): save_decision refuses an
# id that is already stored, and update_outcome is the only permitted mutation.
# Candidates are not immutable — save_candidate upserts on (ticker, asOfDate),
# which is how one becomes analyzed after its Analysis Run.
#
# Agent reports are not stored here. They are large and rarely queried, so they
# live in files keyed by decision id, pointed at by Decision.reportsRef.
#
# Column names mirror the model attribute names, so a row maps straight onto
# model fields without a translation layer.

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.decisions.schema import Candidate, Decision, DecisionStatus, Outcome, Trigger


class DecisionStoreError(Exception):
    """Base for store-level violations of the decision-record contract."""


class DecisionExistsError(DecisionStoreError):
    """Raised when saving a Decision whose id is already stored. Decisions are
    immutable — a correction is a new Decision, not an overwrite."""


class DecisionNotFoundError(DecisionStoreError):
    """Raised when updating the outcome of a Decision that is not stored."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    ticker    TEXT NOT NULL,
    asOfDate  TEXT NOT NULL,
    triggers  TEXT NOT NULL,
    "rank"    INTEGER NOT NULL,
    analyzed  INTEGER NOT NULL,
    PRIMARY KEY (ticker, asOfDate)
);

CREATE TABLE IF NOT EXISTS decisions (
    id          TEXT PRIMARY KEY,
    ticker      TEXT NOT NULL,
    asOfDate    TEXT NOT NULL,
    createdAt   TEXT NOT NULL,
    triggers    TEXT NOT NULL,
    action      TEXT NOT NULL,
    conviction  TEXT NOT NULL,
    thesis      TEXT NOT NULL,
    reportsRef  TEXT,
    modelConfig TEXT NOT NULL,
    cost        TEXT NOT NULL,
    status      TEXT NOT NULL,
    outcome     TEXT
);

CREATE INDEX IF NOT EXISTS decisions_by_ticker ON decisions (ticker, asOfDate);
"""

_DECISION_COLUMNS = (
    "id, ticker, asOfDate, createdAt, triggers, action, conviction, thesis, "
    "reportsRef, modelConfig, cost, status, outcome"
)


def _dump_triggers(triggers: list[Trigger]) -> str:
    return json.dumps([t.model_dump() for t in triggers])


def _to_candidate(row: sqlite3.Row) -> Candidate:
    return Candidate(
        ticker=row["ticker"],
        asOfDate=row["asOfDate"],
        triggers=json.loads(row["triggers"]),
        rank=row["rank"],
        analyzed=bool(row["analyzed"]),
    )


def _to_decision(row: sqlite3.Row) -> Decision:
    return Decision(
        id=row["id"],
        ticker=row["ticker"],
        asOfDate=row["asOfDate"],
        createdAt=row["createdAt"],
        triggers=json.loads(row["triggers"]),
        action=row["action"],
        conviction=row["conviction"],
        thesis=row["thesis"],
        reportsRef=row["reportsRef"],
        modelConfig=json.loads(row["modelConfig"]),
        cost=json.loads(row["cost"]),
        status=row["status"],
        outcome=json.loads(row["outcome"]) if row["outcome"] is not None else None,
    )


class DecisionStore:
    """Records what the pipeline considered and what it concluded.

    `path` is required rather than defaulted: where the store lives is config,
    and nothing here may assume a host or filesystem layout. Tests pass a
    tmp_path; the runner's real path is wired up by the caller.
    """

    def __init__(self, path: Path):
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def save_candidate(self, candidate: Candidate) -> None:
        """Persist a Candidate, analyzed or not — the names not analyzed are
        the control group. Upserts on (ticker, asOfDate), so re-saving is how a
        Candidate is marked analyzed once its Analysis Run finishes.
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO candidates (ticker, asOfDate, triggers, "rank", analyzed)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (ticker, asOfDate) DO UPDATE SET
                    triggers = excluded.triggers,
                    "rank"   = excluded."rank",
                    analyzed = excluded.analyzed
                """,
                (
                    candidate.ticker,
                    candidate.asOfDate,
                    _dump_triggers(candidate.triggers),
                    candidate.rank,
                    int(candidate.analyzed),
                ),
            )

    def save_decision(self, decision: Decision) -> str:
        """Write a Decision and return its id. Raises DecisionExistsError if
        the id is already stored: Decisions are immutable, and a correction is
        a new Decision.
        """
        with self._connect() as conn:
            try:
                conn.execute(
                    f"INSERT INTO decisions ({_DECISION_COLUMNS}) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        decision.id,
                        decision.ticker,
                        decision.asOfDate,
                        decision.createdAt,
                        _dump_triggers(decision.triggers),
                        decision.action,
                        decision.conviction,
                        decision.thesis,
                        decision.reportsRef,
                        decision.modelConfig.model_dump_json(),
                        decision.cost.model_dump_json(),
                        decision.status,
                        decision.outcome.model_dump_json() if decision.outcome else None,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise DecisionExistsError(
                    f"decision {decision.id!r} is already stored; "
                    "Decisions are immutable, record a correction as a new Decision"
                ) from exc
        return decision.id

    def get_decision(self, decision_id: str) -> Decision | None:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {_DECISION_COLUMNS} FROM decisions WHERE id = ?",
                (decision_id,),
            ).fetchone()
        return _to_decision(row) if row is not None else None

    def list_decisions(
        self,
        ticker: str | None = None,
        since: str | None = None,
        status: DecisionStatus | None = None,
    ) -> list[Decision]:
        """Most recent first. `since` is an inclusive ISO date filtered on
        asOfDate — the trading day a Decision is *about*, not the timestamp it
        was written. ISO dates sort lexicographically, so the comparison is a
        plain string one.

        An empty store is normal, not an error: a fresh clone has no history.
        """
        clauses: list[str] = []
        params: list[str] = []
        if ticker is not None:
            clauses.append("ticker = ?")
            params.append(ticker)
        if since is not None:
            clauses.append("asOfDate >= ?")
            params.append(since)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {_DECISION_COLUMNS} FROM decisions{where} "
                "ORDER BY asOfDate DESC, createdAt DESC",
                params,
            ).fetchall()
        return [_to_decision(row) for row in rows]

    def list_candidates(self, as_of_date: str) -> list[Candidate]:
        """Every Candidate screened on one date, most worth analyzing first."""
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT ticker, asOfDate, triggers, "rank", analyzed FROM candidates '
                'WHERE asOfDate = ? ORDER BY "rank" ASC',
                (as_of_date,),
            ).fetchall()
        return [_to_candidate(row) for row in rows]

    def update_outcome(self, decision_id: str, outcome: Outcome) -> None:
        """The one permitted mutation of a stored Decision."""
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE decisions SET outcome = ? WHERE id = ?",
                (outcome.model_dump_json(), decision_id),
            )
            if cursor.rowcount == 0:
                raise DecisionNotFoundError(f"no decision {decision_id!r} in the store")
