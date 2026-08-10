# Phase 1 — Data layer

**Goal:** one reliable, cached interface to all market and fundamental data.
Every later phase reads through it. No LLM calls in this phase.

**Prerequisite:** Phase 0 complete.

---

## Task 1 — Config

`backend/config.py`. Load all keys from `.env`, fail loudly at startup with a
clear message naming any missing required key. Add every new key to
`.env.example` with a placeholder.

Required: `ALPACA_API_KEY_ID`, `ALPACA_API_SECRET_KEY`, `FINNHUB_API_KEY`,
`FRED_API_KEY`.

The two Alpaca names are **not** the `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`
this spec originally drafted. `app/main.py` already reads `ALPACA_API_KEY_ID`
and `ALPACA_API_SECRET_KEY`, `.env.example` declares them, and the live `.env`
on each machine uses them. Renaming would mean hand-editing `.env` on every
machine — and local state does not sync — for no functional gain. The running
code wins; the config module adopts the existing names.

Also already in use, optional with defaults, and not to be dropped:
`ALPACA_PAPER_BASE_URL` (defaults to the paper host) and `PNL_BASELINE`.

---

## Task 2 — Cache

`backend/data/cache.py`. Keyed by `(source, method, ticker, params_hash)`,
with per-source TTL. SQLite or on-disk JSON — simple is fine.

Rules:
- Historical data for a **past** date never expires. It cannot change.
- Fundamentals: TTL ~7 days.
- News/sentiment: TTL ~1 hour.
- Quotes/snapshots: not cached.
- A cache miss that fails upstream raises — it never returns stale data
  silently. If stale data is served deliberately, mark it on the response.

---

## Task 3 — Alpaca client

`backend/data/alpaca_client.py`. Read-only market data. **No order placement in
this module or any other module in this phase.**

```
get_bars(ticker, start, end, timeframe='1Day') -> DataFrame
get_snapshot(ticker) -> Snapshot
get_account() -> Account          # delegate to app/alpaca.py — see below
get_most_actives(top=20) -> list[Candidate-ish]
get_market_movers(top=20) -> {gainers, losers}
```

**Wrap `app/alpaca.py`, do not absorb it.** `HttpAlpacaClient` already exists
and serves the dashboard's `/api/snapshot`. The data-layer client composes it
for account state rather than reimplementing or moving it, and adds bars,
snapshots and the screener endpoints alongside. Rewriting working dashboard
code is not in this phase's scope, and the `AlpacaClient` protocol is the seam
the existing HTTP tests fake — keep it intact.

**Free-tier handling:** the feed is real-time IEX with delayed SIP. When an
end timestamp is `now`, clamp it to ~15 minutes in the past, or the trailing
window returns sparse/empty bars. Make this explicit and tested — it is the
single most common source of "the API returned nothing".

The screener endpoints are documented as SIP-based. Verify they return data on a
free key; if they don't, log clearly and let Phase 2 fall back to custom
triggers over bars.

---

## Task 4 — Finnhub client

`backend/data/finnhub_client.py`

```
get_fundamentals(ticker) -> Fundamentals
get_company_news(ticker, start, end) -> list[NewsItem]
get_earnings_calendar(ticker) -> list[EarningsEvent]
get_insider_transactions(ticker) -> list[InsiderTx]
```

60 req/min free tier. Implement a rate limiter, not just retry-on-429.

---

## Task 5 — FRED client

`backend/data/fred_client.py`. `get_series(series_id, start, end)`. Start with a
small set: `DFF`, `CPIAUCSL`, `UNRATE`, `T10Y2Y`. Cache aggressively — these
update monthly at most.

---

## Task 6 — Indicators

`backend/data/indicators.py`. Use `pandas-ta` or `TA-Lib` — do not hand-roll.
Compute over a bars DataFrame: RSI, MACD, SMA(20/50/200), ATR, Bollinger Bands,
volume vs 20-day average.

Pure functions over a DataFrame. No network calls, no caching. Fully unit
testable on fixture data.

---

## Task 7 — Unified accessor

`backend/data/__init__.py` exposing a single `MarketData` facade so downstream
code never imports a vendor client directly. Swapping a vendor later should
touch one file.

---

## Testing

- Every client tested against **recorded fixtures**, never live network in CI
- Cache test: second call within TTL makes zero network calls (assert on a mock)
- Indicator tests on a known fixture with hand-checked expected values
- Explicit test for the Alpaca 15-minute end-clamp behaviour
- Rate limiter test: N+1 rapid calls do not exceed the limit

---

## Acceptance criteria

- [ ] `MarketData().get_bars('AAPL', 90)` returns clean data; second call hits cache
- [ ] `MarketData().get_fundamentals('AAPL')` returns populated fields
- [ ] Indicators compute correctly on fixtures
- [ ] Missing config key produces a clear startup error naming the key
- [ ] `pytest` passes with no network access; `ruff check` clean
- [ ] `.env.example` lists every key
- [ ] Grep confirms no order-placement call anywhere in `backend/data/`

## Out of scope

Screener logic, LLM providers, decision-making, UI, order placement.

## Note

This phase is unglamorous and there will be a pull to rush it to get to the
agents. Don't. Every bug here shows up later as an agent making a confident
argument from wrong numbers, which is far harder to notice.
