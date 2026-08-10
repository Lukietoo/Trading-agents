# CLAUDE.md

Operating instructions for Claude Code in this repository.

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

**Stack**
- Backend: Python ≥3.13 (`backend/pyproject.toml`), FastAPI, Pydantic v2, httpx.
  Pydantic is used throughout but is only a *transitive* dependency via FastAPI
  — declare it explicitly the first time a phase depends on it directly.
- Frontend: React + TypeScript, built with Vite
- Package management: `venv` + `pip -e '.[dev]'` for the backend, `npm` for the
  frontend. There is no `uv` lockfile — don't introduce one without asking.
- Tests: `pytest` (backend), `vitest` (frontend)
- Lint: `oxlint` (frontend). **The backend has no linter or formatter
  configured** — `ruff` is not a dependency and there is no config for it.
  Adding one is its own change, not a side effect of another task.

**Layout** — what exists today:
```
backend/
  pyproject.toml      packages = ["app"] — `app` is the installed package
  app/
    main.py           FastAPI app + `app_from_env()` factory
    alpaca.py         Alpaca paper API client
    snapshot.py       assembles the dashboard snapshot
  tests/              pytest, fake Alpaca client, no network
frontend/src/
  types/              TypeScript contract — frontend leads (single index.ts)
  api/ components/ data/ hooks/ lib/
specs/                one work order per phase
design-reference/
```

Backend modules added by later phases go **inside `backend/app/`** —
`app.decisions`, `app.data`, `app.screener`, `app.agents`, `app.executor`,
`app.evaluation` — because `packages = ["app"]` is what gets installed and
imports are absolute from `app.` (e.g. `from app.alpaca import ...`). A
top-level `backend/decisions/` would not be importable without changing
packaging. Some phase specs write the shorter `backend/<module>/` path; that
means `backend/app/<module>/`.

**The contract direction.** Per `CONTEXT.md`, the frontend's TypeScript types
define the data contract; the backend conforms. When adding a shared entity,
write the TS type first, then the matching Pydantic model.

**Wire format.** The API sends raw numbers — never display strings. Percentages
rounded to two decimals. All currency/percent formatting and sign-based
colouring lives in the frontend.

**Serialisation.** Pydantic models declare **camelCase attribute names
directly** (`avgCost`, `weightPct`, `totalPnlPct` — see `app/snapshot.py`).
There is no alias generator and no snake_case layer; the Python attribute name
*is* the wire name. Match this in new models rather than adding aliases.

**Naming.** Use the exact terms from `CONTEXT.md`. If you need a concept that
isn't in the glossary, add it to `CONTEXT.md` in the same change rather than
inventing a synonym.

---

## Commands

Backend commands run from `backend/`. The app is created by a factory, so
`--factory` is required; credentials come from the root `.env`.

```bash
# backend — first-time setup
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'

# backend — run
set -a; source ../.env; set +a
.venv/bin/uvicorn app.main:app_from_env --factory --port 8000

# backend — test
.venv/bin/pytest
```

Frontend commands run from `frontend/`. **There is no `typecheck` script** —
type checking is `tsc -b`, which `npm run build` also runs.

```bash
npm run dev        # vite dev server, proxies /api to 127.0.0.1:8000
npx tsc -b         # type check
npm run lint       # oxlint
npm run test       # vitest run
npm run build      # tsc -b && vite build
```

---

## Working style

- **Stop and ask, always.** If a spec is ambiguous on anything — schema, naming,
  file placement, library choice, an external API's behaviour — stop and ask.
  Do not pick a reasonable option and continue. A wrong guess propagates through
  every later phase, and a short question now is cheaper than a refactor later.
  This applies even when the answer seems obvious.
- **Conflicts stop work.** If a spec contradicts existing code, existing types,
  or `CONTEXT.md`, do not resolve it yourself in either direction. Stop, show me
  both sides, and wait. The spec is not automatically right — it was written
  without reading every file.
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

---

## Machines and local state

Development happens on more than one machine (macOS and Windows). Code syncs
via git; **local state does not**.

Machine-local, never committed, never assumed to exist:
- `.env`
- the decision store (SQLite)
- the data cache
- stored agent reports

Consequences for how code is written:
- Never hardcode absolute paths or platform-specific path separators. Use
  `pathlib`. Code must run on both macOS and Windows.
- Never assume the decision store already has history. Handle an empty store.
- Store paths come from config, with sensible defaults, so a fresh clone runs.

**Runner machine: not yet chosen.** Once the pipeline runs daily it will execute
on exactly one machine, because split execution fragments the decision history
and makes evaluation meaningless. Until that's decided, do not write anything
that assumes a specific host, OS, or filesystem layout.

**Scheduling (Phase 5+):** plain cron, or Task Scheduler on Windows. Do not
introduce Celery, Airflow, or a job queue for one pre-market job per day.

---

**Rate limits are expected, not exceptional.** Every external call needs retry
with backoff. LLM calls route through the LiteLLM proxy so a exhausted free tier
degrades to a fallback instead of crashing the run.