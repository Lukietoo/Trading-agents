# CLAUDE.md

Operating instructions for Claude Code in this repository.

> **⚠️ VERIFY BEFORE FIRST USE.** The lines marked `[CONFIRM]` were assumed, not
> read from the repo. Correct them to match reality, then delete the markers.
> Wrong conventions here are worse than none.

---

## What this project is

An agentic paper-trading system. A screener selects candidates from a ticker
universe, a multi-agent LLM pipeline analyses a small shortlist, decisions are
recorded with their reasoning, and a separate executor places orders against the
**Alpaca paper API**.

Read `CONTEXT.md` for domain vocabulary and `ROADMAP.md` for sequencing.
Work is specified one phase at a time in `specs/phase-N.md`.

---

## Hard rules — never violate

1. **No real money. Ever.** Only the Alpaca *paper* endpoints
   (`paper-api.alpaca.markets`). Never the live trading host. If a task seems to
   require live credentials, stop and ask.
2. **Only the executor module places orders.** No other module may call an
   order-placement endpoint. Analysis code writes `Decision` records; it does
   not trade.
3. **Never commit secrets.** Keys live in `.env` (gitignored). Add new keys to
   `.env.example` with placeholder values.
4. **Stay in scope.** Implement what the current `specs/phase-N.md` asks for.
   Do not start later phases, add LLM providers not listed, or refactor the
   frontend unless the spec says to.
5. **Don't touch `frontend/` unless the spec says to.** The dashboard is
   working code; Phase 7 is when it changes.
6. **No look-ahead in any backtest or evaluation path.** Data used for a
   decision dated D must not include anything published after D.

---

## Conventions

**Stack** `[CONFIRM]`
- Backend: Python 3.12, FastAPI, Pydantic v2
- Frontend: React + TypeScript
- Package management: `uv` (fall back to `pip` if not present)
- Tests: `pytest`
- Lint/format: `ruff`

**Layout**
```
backend/
  api/          FastAPI routes (existing)
  data/         market/fundamental data clients + cache   [Phase 1]
  screener/     candidate selection                        [Phase 2]
  agents/       LLM analysis graph                         [Phase 3]
  decisions/    Decision store and schema                  [Phase 0/4]
  executor/     the ONLY module that places orders         [Phase 5]
  evaluation/   outcome backfill, benchmarks               [Phase 6]
frontend/src/types/   TypeScript contract — frontend leads
specs/                one work order per phase
tests/
```

**The contract direction.** Per `CONTEXT.md`, the frontend's TypeScript types
define the data contract; the backend conforms. When adding a shared entity,
write the TS type first, then the matching Pydantic model.

**Wire format.** The API sends raw numbers — never display strings. Percentages
rounded to two decimals. All currency/percent formatting and sign-based
colouring lives in the frontend.

**Naming.** Use the exact terms from `CONTEXT.md`. If you need a concept that
isn't in the glossary, add it to `CONTEXT.md` in the same change rather than
inventing a synonym.

---

## Commands `[CONFIRM]`

```bash
# backend
uv run uvicorn backend.main:app --reload
uv run pytest
uv run ruff check . && uv run ruff format .

# frontend
npm run dev
npm run typecheck
```

---

## Working style

- **Ask before assuming.** If a spec is ambiguous on schema, naming, or an
  external API's behaviour, ask rather than picking. A wrong guess propagates.
- **Small commits, one concern each.** Conventional commit messages.
- **Tests alongside code**, not after. Every external API client gets a test
  with a recorded/mocked response — never one that hits the network in CI.
- **No silent fallbacks.** If a data source fails, raise or return an explicit
  error state. Never substitute stale or synthetic data without marking it.
- **Log costs.** Any code path that calls an LLM records input/output tokens.
- **Don't mark a phase done** until its spec's acceptance criteria actually
  pass. Say what's incomplete rather than declaring success.

---

## External services

| Service | Purpose | Notes |
|---|---|---|
| Alpaca | Paper trading, bars, screener | Free tier: real-time IEX, delayed SIP |
| Finnhub | Fundamentals, news, earnings, insider | 60 req/min free |
| FRED | Macro series | Free |
| Google AI Studio | Deep-think LLM | Free tier |
| Cerebras / Groq | Quick-think LLM | Free tier |
| LiteLLM proxy | Provider routing + failover | Local |

**Alpaca gotcha:** on the free IEX feed the trailing ~15 minutes of bars can be
sparse. When requesting a window ending "now", set the end timestamp ~15 minutes
in the past.

**Rate limits are expected, not exceptional.** Every external call needs retry
with backoff. LLM calls route through the LiteLLM proxy so a exhausted free tier
degrades to a fallback instead of crashing the run.
