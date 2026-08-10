# Phase 0 — Decision vocabulary and type contract

**Goal:** give the codebase words for *decisions*, not just *state*. Nothing in
`CONTEXT.md` currently describes a candidate, an analysis, or a rationale — so
there is no contract for the agent layer to fill. This phase closes that gap.

**No behaviour changes. No new endpoints. Types and vocabulary only.**

---

## Task 1 — Extend `CONTEXT.md`

Append a section to the existing glossary, in the same voice and format. Do not
alter existing entries. Add:

- **Universe** — the set of tickers eligible for consideration.
- **Candidate** — a ticker the screener flagged on a given date as worth
  analysing. Being a candidate implies nothing about direction.
- **Trigger** — the specific condition that made a ticker a candidate (e.g.
  volume spike, RSI extreme), with the values that fired it.
- **Analysis Run** — one execution of the agent pipeline over one candidate,
  producing exactly one Decision.
- **Decision** — the pipeline's recorded output for one ticker on one date: an
  Action, a Thesis, and supporting metadata. A Decision is a record, not an
  order; it may never be executed.
- **Action** — `BUY`, `SELL`, or `HOLD`.
- **Conviction** — the pipeline's own confidence in a Decision, `low` |
  `medium` | `high`.
- **Thesis** — the short natural-language rationale for a Decision.
- **Outcome** — the realised result of a Decision, measured after the fact:
  forward return over fixed horizons, and the same relative to a benchmark.
- **Alpha** — a return measured relative to the benchmark (SPY), not absolute.
- **Skipped Candidate** — a Candidate that was not analysed. Retained
  deliberately as a control group.

Add to Conventions:
- A Decision is immutable once written. Corrections are new Decisions.
- Every Candidate is persisted, analysed or not.

---

## Task 2 — TypeScript types

In `frontend/src/types/`, following existing file naming and export style
(read the directory first — match what's there, don't impose a new pattern).

Raw numbers only, no display strings. Percentages as numbers rounded to two
decimals.

```ts
export type Action = 'BUY' | 'SELL' | 'HOLD';
export type Conviction = 'low' | 'medium' | 'high';
export type DecisionStatus = 'pending' | 'executed' | 'skipped' | 'expired';

export interface Trigger {
  name: string;          // e.g. 'volume_spike'
  value: number;         // observed value
  threshold: number;     // value that had to be crossed
}

export interface Candidate {
  ticker: string;
  asOfDate: string;      // ISO date
  triggers: Trigger[];
  rank: number;          // 1 = most worth analysing
  analysed: boolean;
}

export interface Outcome {
  return1d: number | null;   // percent
  return5d: number | null;
  return20d: number | null;
  alpha1d: number | null;    // vs SPY, percent
  alpha5d: number | null;
  alpha20d: number | null;
  measuredAt: string | null;
}

export interface ModelConfig {
  provider: string;
  deepModel: string;
  quickModel: string;
  debateRounds: number;
}

export interface RunCost {
  inputTokens: number;
  outputTokens: number;
  estimatedUsd: number;
}

export interface Decision {
  id: string;
  ticker: string;
  asOfDate: string;
  createdAt: string;
  triggers: Trigger[];
  action: Action;
  conviction: Conviction;
  thesis: string;
  reportsRef: string | null;   // pointer to stored agent reports
  modelConfig: ModelConfig;
  cost: RunCost;
  status: DecisionStatus;
  outcome: Outcome | null;
}
```

Adjust field naming if the existing types use a different case convention —
consistency with the repo wins over the draft above.

---

## Task 3 — Pydantic models

`backend/decisions/schema.py`. Mirror the TS types exactly, using the repo's
existing snake_case/camelCase serialisation approach so the wire format matches
what the frontend expects. Include a serialisation test proving a round-trip
produces the field names the TS interfaces declare.

---

## Task 4 — Persistence stub

`backend/decisions/store.py`. A minimal interface only — no agent code yet.

```
save_candidate(candidate) -> None
save_decision(decision) -> id
get_decision(id) -> Decision | None
list_decisions(ticker=None, since=None, status=None) -> list[Decision]
list_candidates(as_of_date) -> list[Candidate]
update_outcome(id, outcome) -> None
```

SQLite is fine. Agent reports go to files keyed by decision id, not into the
database — they're large and rarely queried.

Enforce immutability: `save_decision` on an existing id raises. `update_outcome`
is the only permitted mutation.

---

## Acceptance criteria

- [x] `CONTEXT.md` defines every term above; no new term used in code is absent
- [x] TS types compile (`npm run typecheck`)
- [x] Pydantic models import and validate
- [x] Round-trip serialisation test passes and asserts wire field names
- [x] `pytest` passes; `ruff check` clean
- [x] Store enforces decision immutability (test asserts the raise)
- [x] No API route changes, no frontend component changes, no network calls

Verified 2026-08-09, in order: all eleven glossary terms present in
`CONTEXT.md`; `npx tsc -b` exits 0; `tests/test_decision_schema.py` and
`tests/test_decision_store.py` pass (26 tests);
`test_decision_json_field_names_match_the_typescript_interface` asserts the
wire names field by field; `pytest` green and `ruff check` clean;
`test_saving_an_existing_decision_id_raises` asserts the immutability raise;
`app/main.py` still exposes only `/api/snapshot`, `app/decisions/` contains no
networking import, and no frontend file has changed.

One wording note: the second criterion names `npm run typecheck`, which does
not exist in this repo — type checking is `tsc -b`, as `CLAUDE.md` records.
That is what was run.

## Out of scope

Screener logic, LLM calls, data clients, order placement, UI components.
