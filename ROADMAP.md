# ROADMAP.md

Build plan for the agentic paper-trading system. Complements `CONTEXT.md`
(domain glossary) — this file holds sequencing and decisions, not vocabulary.

## Objective

A daily-cadence pipeline that screens a universe of tickers, runs a multi-agent
LLM analysis on a small shortlist, records a decision with its reasoning, and
executes against the Alpaca paper account — with enough logging to answer the
only question that matters: **does this beat buy-and-hold?**

Success is not "the bot trades." Success is "we can prove whether it should."

---

## Current state

*Updated 2026-08-09, after Phase 1 merged.*

| Component | Status |
|---|---|
| Frontend dashboard (TS types lead the contract) | Exists |
| FastAPI backend wrapping Alpaca paper API | Exists |
| Domain glossary (`CONTEXT.md`) | Exists — decision vocabulary added in Phase 0 |
| Decision schema + store | Exists (Phase 0) — nothing constructs the store yet |
| Market/fundamental data layer | **Exists (Phase 1)** — `MarketData` over Alpaca, Finnhub, FRED, cached |
| Screener | Missing — Phase 2, next |
| Agent graph | Missing |
| Evaluation loop | Missing |

Phases 0 and 1 are complete, with their acceptance criteria ticked against
tests rather than manual checks (see the bottom of each spec).

**Nothing runs end to end yet.** The data layer is a library; no command
performs a full pass. The first runnable thing is Phase 2.

---

## Architectural decisions to make before writing code

These are cheap now and expensive later.

**1. Decide and execute are separate processes.**
The analysis pipeline writes a `Decision` record. A separate executor reads
pending decisions and places orders. This means a bug in the agent layer can
never place an order, the pipeline can run in dry-run indefinitely, and you can
replay decisions against different execution rules without re-running the LLMs.

**2. The decision record is the core artifact.**
Everything else is upstream or downstream of it. Minimum fields:

```
id, ticker, as_of_date, created_at
trigger          — what the screener flagged and its values
action           — BUY | SELL | HOLD
conviction       — model's own confidence
thesis           — short natural-language rationale
reports          — refs to the analyst/debate artifacts
model_config     — provider, models, debate rounds (for attribution)
token_cost       — input/output tokens, estimated $
status           — pending | executed | skipped | expired
outcome          — filled in later: forward return 1d/5d/20d, vs SPY
```

Store the full agent reports separately (blob/file, keyed by decision id) —
they're large and rarely queried.

**3. Every screened candidate is logged, not just analyzed ones.**
The names you *skip* are the control group. Without them you cannot tell whether
the screener selects for anything real. This is the single most important
logging decision in the project.

**4. Provider access goes through a proxy from day one.**
LiteLLM in front of Gemini / Cerebras / Groq / a paid fallback. Free tiers will
rate-limit mid-run; this turns that from a crash into a degrade.

**5. Cache is a first-class layer, not an afterthought.**
Fundamentals change quarterly. Price bars for a past date never change. Cache
by (source, ticker, date) with per-source TTL.

---

## Phases

### Phase 0 — Extend the domain glossary
*Small, do it first.*

Add decision-side terms to `CONTEXT.md`: **Universe**, **Candidate**,
**Trigger**, **Analysis Run**, **Decision**, **Thesis**, **Conviction**,
**Outcome**, **Reflection**. Then define the matching TypeScript types in
`frontend/src/types/` — per the existing convention, the frontend leads and the
backend conforms.

**Done when:** the types compile and the glossary has no word the code uses that
isn't defined.

---

### Phase 1 — Data layer (read-only, no LLMs)
*Foundation. Boring. Skipping it costs you later.*

- Alpaca client for bars, snapshots, account state (already partly present)
- Finnhub client: fundamentals, news, earnings calendar, insider
- FRED client: macro series
- Unified cache with TTL per source
- One config module holding all keys, loaded from `.env`

**Watch for:** Alpaca's free tier is real-time IEX with delayed SIP. Query bar
windows ending ~15 min in the past or the trailing window comes back sparse.

**Done when:** `get_bars("AAPL", 90)` and `get_fundamentals("AAPL")` return
clean data from cache on the second call.

---

### Phase 2 — Screener
*Cheap, deterministic, no LLM cost. The highest-leverage component.*

Start with Alpaca's built-in `ScreenerClient` (`get_most_actives`,
`get_market_movers`) to get the funnel working end-to-end in an afternoon.

Then replace with custom triggers over a defined universe (start ~100 liquid
names):
- Volume vs 20-day average
- Gap from previous close
- RSI extremes
- Price crossing 20/50-day MA
- Earnings within N days
- News-volume spike (Finnhub)

Output: ranked `Candidate` list with trigger metadata. **Ranked by "worth
analyzing," not by "best buy."** A stock down 8% on bad news ranks as high as
one up 8% — the agents decide direction, the screener only allocates attention.

**Done when:** it runs over the universe in under two minutes, costs nothing,
and every candidate is persisted with its trigger values.

---

### Phase 3 — Agent graph, single ticker, manual invocation
*The expensive part. Isolate it.*

Port or vendor the TradingAgents graph. Start deliberately minimal:
- 2 analysts (fundamentals + news), not 4
- `max_debate_rounds: 1`
- Cheap model on the quick-think slot

Instrument token usage per node from the first run — you need real numbers, not
the estimates.

**Done when:** one ticker produces a structured `Decision` with a readable
thesis, and you know exactly what it cost.

---

### Phase 4 — Wire the funnel, dry-run only
*No orders yet.*

Screener → top 3 candidates → agent graph → `Decision` written with
`status=pending`. Nothing executes. Run it daily for at least two weeks and read
every decision by hand.

**This is the phase where you find out if the thing works.** Specifically, check
whether the bull/bear debate ever changes the outcome, or whether the trader
lands on the same call regardless. If the debate is decorative, cut it and halve
your costs.

**Done when:** two weeks of decisions exist and you have an opinion, formed from
reading them, about whether the reasoning is real.

---

### Phase 5 — Execution against paper
- Executor reads pending decisions, applies position sizing and risk limits,
  places Alpaca paper orders
- Hard limits in code: max position size, max positions, no trade if a decision
  is older than N hours
- Reconciliation: every order maps back to a decision id

**Done when:** the paper account trades unattended for a week without manual
intervention, and every fill traces to a decision.

---

### Phase 6 — Evaluation loop
*The part that determines whether any of this was worth it.*

- Nightly job fills in `outcome` on past decisions (1d/5d/20d return, and alpha
  vs SPY)
- Same for **skipped** candidates — the control group
- Benchmark the portfolio against buy-and-hold on the same universe
- Reflection: feed recent outcomes back into the analysis prompt (this is the
  most interesting idea to steal from TradingAgents)

**Done when:** you can answer, with a number, whether the agent decisions beat
both buy-and-hold and a naive "trade every screener hit" baseline.

---

### Phase 7 — Dashboard extension
Surface decisions in the existing UI: candidate feed, decision detail with
thesis and reports, outcome attribution, cost-per-decision. Now the dashboard
you already built is doing the job it's best at.

---

## Cost plan

| Phase | Expected spend |
|---|---|
| 0–2 | $0 |
| 3–4 | $0–15/mo (free tiers + small paid fallback) |
| 5–6 | $10–30/mo at 3–5 decisions/day |
| Optional backtest sweep | $30–80 one-off, once config is stable |

Cost control levers, in order of impact: debate rounds → analyst count →
cache hit rate → model choice on the quick-think slot.

---

## Risks and kill criteria

Write these down now, while you're not emotionally invested in the answer.

- **The debate is decorative.** If bull/bear rounds don't change outcomes, cut
  them. Test explicitly in Phase 4.
- **The screener is noise.** If flagged candidates don't move more than
  unflagged ones, the agents are analyzing a random sample. Test in Phase 6.
- **Sample size fantasy.** Three months of decisions on 3–5 names is not
  statistically meaningful. Expect to be unable to distinguish skill from luck
  for a long time, and don't let a good month convince you otherwise.
- **Regime dependence.** The published results come from a strong tech tape in
  early 2024. A strategy that only works in a rising market hasn't been tested.
- **Overfitting to the backtest.** Every prompt tweak made after seeing results
  is a fitted parameter. Track how many you've made.

**Kill criterion:** if after Phase 6 the system doesn't beat buy-and-hold *and*
doesn't beat the naive screener-only baseline, the agent layer isn't earning its
cost. That's a real finding, not a failure.

---

## Immediate next actions

1. Write `specs/phase-2.md` — the screener. Fold in the carry-overs below.
2. Register the LLM keys not yet needed: Google AI Studio, Cerebras, Groq
3. Stand up Alpaca's built-in screener to prove the funnel (Phase 2, v0)
4. One `propagate()`-equivalent run on one ticker; measure real token cost

Do not connect real money at any point in this roadmap.

---

## Carried into the Phase 2 spec session

Open items from Phase 1, deliberately not fixed at the time. Decided on
2026-08-09 to settle them while specifying Phase 2 rather than as scattered
one-offs, since several change what Phase 2 should do.

**1. The decision store has no backup.** One SQLite file, one Mac, gitignored,
synced nowhere. Phase 6 answers "does this beat buy-and-hold?" only from
accumulated history, and that history cannot be recreated — the LLM outputs and
the data as it looked that day are gone. The file barely exists today, so this
is close to free now and expensive later. *Highest priority of these.*

**2. Nothing runs the tests but a human.** No CI, no `.github/`. A break can sit
in `main` until someone runs `pytest`. Thin for something that will run
unattended daily from Phase 5.

**3. Recorded fixtures cannot detect vendor drift.** Every test runs against
responses recorded on 2026-08-09. If Finnhub renames a field tomorrow all 260
tests still pass and the pipeline breaks on the next real run. Fixtures protect
against our regressions, not their changes. Wants a separate live contract
check, deliberately *not* in CI — it would be flaky and would burn quota.

**4. `Fundamentals.is_populated` is weaker than its name.** It only means
Finnhub returned something. Measured: AAPL 16/16 named fields, NVDA 16/16,
HTZ 12/16, but SPY 4/16 and the warrant ANSCW 3/16 — all reporting `True`.
Phase 2 will hand exactly these instruments downstream, so an agent gets a
green light on near-empty data. Ten-minute fix; shapes Phase 2.

**5. The decision store ignores the config rule.** `CLAUDE.md` says store paths
come from config with sensible defaults so a fresh clone runs. The cache
complies via `DATA_CACHE_PATH`; the store takes a bare path with no default and
no key, and nothing in `app/` constructs it. Phase 4 is where that bites.

**6. Only 7 of 260 tests are proven to catch bugs.** The Phase 1 acceptance
tests were mutation-checked; the rest were not. Two of those seven failed to
notice a deliberate break on the first attempt, which is a fair warning about
the 253 unchecked.

Already scheduled, listed so they are not rediscovered: the raw movers list is
unusable without a price/liquidity filter (warrants, sub-penny stocks), and
company news runs to ~250 items a week for a mega-cap, which is a Phase 3 token
cost problem.
