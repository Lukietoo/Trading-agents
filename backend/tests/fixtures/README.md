# Recorded API fixtures

Real responses from the three Phase 1 data sources, recorded once on
**2026-08-09** against a free-tier key for each. Tests read these instead of the
network — nothing in the suite makes a live call.

Every file is the response body exactly as the API returned it: no keys were
renamed, no values rewritten, no fields invented. Where a response was large,
**lists were sliced** — see the table. Nothing else was changed, so the shapes
are trustworthy even where the volume isn't.

| File | Endpoint | Trimming |
|---|---|---|
| `alpaca_bars_aapl_1day.json` | `GET data/v2/stocks/bars` `AAPL 1Day`, 120d, `feed=iex` | none — 82 bars |
| `alpaca_snapshot_aapl.json` | `GET data/v2/stocks/snapshots` `feed=iex` | none |
| `alpaca_most_actives.json` | `GET data/v1beta1/screener/stocks/most-actives?top=20` | none |
| `alpaca_movers.json` | `GET data/v1beta1/screener/stocks/movers?top=20` | none |
| `finnhub_metrics_aapl.json` | `GET stock/metric?metric=all` | all 133 `metric` fields kept; each `series.{annual,quarterly}` history cut to 3 periods |
| `finnhub_profile_aapl.json` | `GET stock/profile2` | none |
| `finnhub_company_news_aapl.json` | `GET company-news`, 7d | 248 items → first 10 |
| `finnhub_earnings_calendar_aapl.json` | `GET calendar/earnings`, ±180d | none |
| `finnhub_earnings_surprises_aapl.json` | `GET stock/earnings` | none |
| `finnhub_insider_transactions_aapl.json` | `GET stock/insider-transactions`, 180d | none |
| `fred_{dff,cpiaucsl,unrate,t10y2y}.json` | `GET fred/series/observations`, 730d | `DFF`/`T10Y2Y` daily series → 60 observations |

No credentials appear in any file. None of these endpoints echoes the key back,
and FRED — the one API that takes its key in the query string — returns it in
neither the body nor any recorded field.

## What the recording established

Two things the spec asked us to find out, now answered by evidence rather than
assumption:

- **The Alpaca screener endpoints work on a free key.** `most-actives` and
  `movers` both returned `200` with full payloads, despite being documented as
  SIP-based. Phase 2 does not need the custom-trigger fallback on day one.
- **FRED uses `"."` for a missing observation, and it really occurs.**
  `fred_t10y2y.json` retains 3 such rows — the slice was centred on them
  deliberately. A client that calls `float(value)` on an observation crashes on
  real data.

Two further notes for anyone reading the numbers:

- **IEX volume is a fraction of consolidated volume.** AAPL shows ~1.1M shares a
  day in `alpaca_bars_aapl_1day.json`, not the ~50M it actually trades. That is
  the free feed reporting one venue's share, not bad data. Any volume-based
  trigger must compare IEX against IEX.
- **`next_page_token` is `null` here** because 82 bars fit in one page. It is
  not always null, so the client pages regardless.

## Re-recording

These are point-in-time. Refreshing them is a deliberate act — a re-record
changes what the tests assert against, so do it in its own commit, and expect
hand-checked indicator values to need recomputing.
