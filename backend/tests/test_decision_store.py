# Store behaviour, against a real SQLite file in tmp_path — no network, and no
# assumption that a store already exists or has history.

from collections.abc import Callable
from pathlib import Path

import pytest

from app.decisions.schema import Candidate, Decision, Outcome
from app.decisions.store import (
    DecisionExistsError,
    DecisionNotFoundError,
    DecisionStore,
)


@pytest.fixture
def store(tmp_path: Path) -> DecisionStore:
    return DecisionStore(tmp_path / "decisions.db")


def test_store_creates_its_file_and_starts_empty(tmp_path: Path):
    # A fresh clone has no decision history; that is normal, not an error.
    store = DecisionStore(tmp_path / "nested" / "decisions.db")

    assert store.list_decisions() == []
    assert store.list_candidates("2026-08-07") == []


def test_saved_decision_round_trips_through_sqlite(
    store: DecisionStore, make_decision: Callable[..., Decision], measured_outcome: Outcome
):
    decision = make_decision(outcome=measured_outcome)

    decision_id = store.save_decision(decision)

    assert decision_id == decision.id
    assert store.get_decision(decision.id) == decision


def test_get_decision_returns_none_when_absent(store: DecisionStore):
    assert store.get_decision("dec-does-not-exist") is None


def test_saving_an_existing_decision_id_raises(
    store: DecisionStore, make_decision: Callable[..., Decision]
):
    # A Decision is immutable once written. A correction is a new Decision.
    store.save_decision(make_decision())

    with pytest.raises(DecisionExistsError):
        store.save_decision(make_decision(action="SELL", conviction="low"))


def test_a_refused_overwrite_leaves_the_stored_decision_intact(
    store: DecisionStore, make_decision: Callable[..., Decision]
):
    store.save_decision(make_decision())

    with pytest.raises(DecisionExistsError):
        store.save_decision(make_decision(action="SELL"))

    stored = store.get_decision("dec-20260807-nvda")
    assert stored is not None
    assert stored.action == "BUY"


def test_update_outcome_is_the_permitted_mutation(
    store: DecisionStore, make_decision: Callable[..., Decision], measured_outcome: Outcome
):
    decision = make_decision()
    store.save_decision(decision)

    store.update_outcome(decision.id, measured_outcome)

    stored = store.get_decision(decision.id)
    assert stored is not None
    assert stored.outcome == measured_outcome
    # Nothing else moved.
    assert stored == decision.model_copy(update={"outcome": measured_outcome})


def test_update_outcome_on_an_unknown_decision_raises(
    store: DecisionStore, measured_outcome: Outcome
):
    with pytest.raises(DecisionNotFoundError):
        store.update_outcome("dec-does-not-exist", measured_outcome)


def test_list_decisions_filters_by_ticker(
    store: DecisionStore, make_decision: Callable[..., Decision]
):
    store.save_decision(make_decision(decision_id="a", ticker="NVDA"))
    store.save_decision(make_decision(decision_id="b", ticker="AAPL"))

    assert [d.id for d in store.list_decisions(ticker="AAPL")] == ["b"]


def test_list_decisions_filters_by_status(
    store: DecisionStore, make_decision: Callable[..., Decision]
):
    store.save_decision(make_decision(decision_id="a", status="pending"))
    store.save_decision(make_decision(decision_id="b", status="executed"))

    assert [d.id for d in store.list_decisions(status="executed")] == ["b"]


def test_list_decisions_since_is_an_inclusive_filter_on_as_of_date(
    store: DecisionStore, make_decision: Callable[..., Decision]
):
    # `since` filters the trading day a Decision is about, not when it was
    # written — a Decision written late still belongs to its as-of date.
    store.save_decision(
        make_decision(decision_id="old", as_of_date="2026-07-31", created_at="2026-08-06T13:00:00Z")
    )
    store.save_decision(make_decision(decision_id="edge", as_of_date="2026-08-01"))
    store.save_decision(make_decision(decision_id="new", as_of_date="2026-08-07"))

    assert {d.id for d in store.list_decisions(since="2026-08-01")} == {"edge", "new"}


def test_list_decisions_returns_most_recent_first(
    store: DecisionStore, make_decision: Callable[..., Decision]
):
    store.save_decision(make_decision(decision_id="older", as_of_date="2026-08-05"))
    store.save_decision(make_decision(decision_id="newer", as_of_date="2026-08-07"))

    assert [d.id for d in store.list_decisions()] == ["newer", "older"]


def test_list_decisions_combines_filters(
    store: DecisionStore, make_decision: Callable[..., Decision]
):
    store.save_decision(
        make_decision(decision_id="a", ticker="NVDA", as_of_date="2026-08-07", status="pending")
    )
    store.save_decision(
        make_decision(decision_id="b", ticker="NVDA", as_of_date="2026-07-01", status="pending")
    )
    store.save_decision(
        make_decision(decision_id="c", ticker="NVDA", as_of_date="2026-08-07", status="expired")
    )

    found = store.list_decisions(ticker="NVDA", since="2026-08-01", status="pending")

    assert [d.id for d in found] == ["a"]


def test_saved_candidate_round_trips_with_its_trigger_values(
    store: DecisionStore, make_candidate: Callable[..., Candidate]
):
    candidate = make_candidate()

    store.save_candidate(candidate)

    assert store.list_candidates("2026-08-07") == [candidate]


def test_skipped_candidates_are_persisted_too(
    store: DecisionStore, make_candidate: Callable[..., Candidate]
):
    # The names not analyzed are the control group — losing them is the one
    # logging mistake that cannot be undone after the fact.
    store.save_candidate(make_candidate(ticker="NVDA", rank=1, analyzed=True))
    store.save_candidate(make_candidate(ticker="AMD", rank=7, analyzed=False))

    assert [(c.ticker, c.analyzed) for c in store.list_candidates("2026-08-07")] == [
        ("NVDA", True),
        ("AMD", False),
    ]


def test_re_saving_a_candidate_marks_it_analyzed(
    store: DecisionStore, make_candidate: Callable[..., Candidate]
):
    # Candidates are not immutable: this is how the pipeline records that a
    # Candidate's Analysis Run has happened.
    store.save_candidate(make_candidate(analyzed=False))

    store.save_candidate(make_candidate(analyzed=True))

    assert [c.analyzed for c in store.list_candidates("2026-08-07")] == [True]


def test_list_candidates_is_ranked_most_worth_analyzing_first(
    store: DecisionStore, make_candidate: Callable[..., Candidate]
):
    store.save_candidate(make_candidate(ticker="AMD", rank=3))
    store.save_candidate(make_candidate(ticker="NVDA", rank=1))
    store.save_candidate(make_candidate(ticker="INTC", rank=2))

    assert [c.ticker for c in store.list_candidates("2026-08-07")] == ["NVDA", "INTC", "AMD"]


def test_list_candidates_is_scoped_to_one_date(
    store: DecisionStore, make_candidate: Callable[..., Candidate]
):
    store.save_candidate(make_candidate(as_of_date="2026-08-06"))
    store.save_candidate(make_candidate(as_of_date="2026-08-07"))

    assert [c.asOfDate for c in store.list_candidates("2026-08-07")] == ["2026-08-07"]


def test_decisions_persist_across_store_instances(
    tmp_path: Path, make_decision: Callable[..., Decision]
):
    path = tmp_path / "decisions.db"
    DecisionStore(path).save_decision(make_decision())

    reopened = DecisionStore(path)

    assert reopened.get_decision("dec-20260807-nvda") is not None
