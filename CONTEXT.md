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

## Conventions

- Positive amounts and percentages render green; negative render coral. This
  is semantic and independent of any decorative badge colors.
  - Exception (per the design reference): activity-log amounts color by
    credit/debit, not sign — credits render green, debit amounts render ink.
    A buy is spending, not a loss.
- The frontend's TypeScript types (`frontend/src/types/`) define the data
  contract the future backend (TradingAgents + Alpaca paper API service) must
  conform to — the frontend leads, the backend follows.
