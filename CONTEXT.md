# Domain Glossary

Ubiquitous language for the paper trading dashboard. Implementation details do
not belong here.

## Terms

**Paper account** — A simulated trading account. No real money is ever
involved. "Reset Account" restores it to its starting balance.

**Portfolio** — Everything the paper account holds: cash plus all positions.
*Portfolio Value* is their combined worth.

**Position** — A holding of one stock: ticker, share count, average cost,
current price, current value, and gain/loss. A position is a *Winner* when its
gain/loss is positive, a *Loser* otherwise.

**Trade** — A single buy or sell of shares. *Recent Trades* is the compact
list of the latest trades.

**Activity entry** — One event in the account's history: a *buy*, a *sell*, or
a *dividend*. Buys are debits (money out of cash); sells and dividends are
credits (money into cash).

**Dividend** — A cash payment received per share held; a credit, never a debit.

**Total P&L** — All-time profit or loss of the portfolio relative to the
starting balance.

**Daily change ("Today")** — The portfolio's change since market open.

**Allocation** — How the invested portion of the portfolio is split across
positions, expressed as percentage weights.

## Decision terms

The vocabulary of the analysis pipeline: how a ticker becomes worth looking at,
what the pipeline concludes about it, and how that conclusion is scored later.

**Universe** — The set of tickers eligible for consideration.

**Candidate** — A ticker the screener flagged on a given date as worth
analyzing. Being a candidate implies nothing about direction: a name down 8% on
bad news is as much a candidate as one up 8%.

**Trigger** — The specific condition that made a ticker a candidate (e.g. a
volume spike, an RSI extreme), carried with the values that fired it.

**Analysis Run** — One execution of the agent pipeline over one Candidate,
producing exactly one Decision.

**Decision** — The pipeline's recorded output for one ticker on one date: an
Action, a Thesis, and supporting metadata. A Decision is a record, not an
order — it may never be executed.

**Action** — The call a Decision makes: `BUY`, `SELL`, or `HOLD`. Distinct from
a Trade's *side*, which is what an order actually sends to Alpaca.

**Conviction** — The pipeline's own confidence in a Decision: low, medium, or
high.

**Thesis** — The short natural-language rationale for a Decision.

**Outcome** — The realized result of a Decision, measured after the fact:
forward return over fixed horizons, and the same relative to the benchmark.

**Alpha** — A return measured relative to the benchmark (SPY), not absolute.

**Skipped Candidate** — A Candidate that was not analyzed. Retained
deliberately: the names not analyzed are the control group for judging whether
the screener selects for anything real.

## Conventions

- Positive amounts and percentages render green; negative render coral. This
  is semantic and independent of any decorative badge colors.
  - Exception (per the design reference): activity-log amounts color by
    credit/debit, not sign — credits render green, debit amounts render ink.
    A buy is spending, not a loss.
- The frontend's TypeScript types (`frontend/src/types/`) define the data
  contract the backend (a Claude Code–driven FastAPI service wrapping the
  Alpaca paper API) must conform to — the frontend leads, the backend follows.
- Numeric wire contract: the API sends raw numbers (percentages rounded to
  two decimals), never display strings. All formatting — currency and percent
  strings, sign-derived green/coral color — lives in the frontend's
  formatting layer.
- A Decision is immutable once written. Corrections are new Decisions; the
  only field filled in after the fact is its Outcome.
- Every Candidate is persisted, analyzed or not.
