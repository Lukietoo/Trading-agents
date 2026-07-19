// Dashboard snapshot API: wire types, fetch, and mapping to the SummaryStat
// view models the Overview stat cards render.

import { formatMoney, formatPercent, formatPrice, formatSignedMoney, formatSignedPercent } from "@/lib/format"
import { closesToSparklinePath } from "@/lib/sparkline"
import type { AllocationSlice, PortfolioSummary, Position, Snapshot } from "@/types"

export type { Snapshot }

// Design-reference slice colors; tickers outside the set cycle the palette.
const TICKER_COLORS: Record<string, string> = {
  AAPL: "#3B6FE0",
  NVDA: "#3E9B6B",
  TSLA: "#D9695E",
  MSFT: "#8B5CF6",
  AMZN: "#F59E0B",
  META: "#6366F1",
}
const FALLBACK_COLORS = Object.values(TICKER_COLORS)

/** Slices narrower than this get no label, per the design (AMZN at 4.4%). */
const MIN_LABEL_WIDTH_PCT = 6

export function toPortfolioSummary(snapshot: Snapshot): PortfolioSummary {
  return {
    portfolioValue: {
      value: formatMoney(snapshot.portfolioValue),
      note:
        snapshot.weekChangePct === null
          ? "no weekly data yet"
          : `${formatSignedPercent(snapshot.weekChangePct)} from last week`,
    },
    cash: {
      value: formatMoney(snapshot.cash),
      note: `${formatPercent(snapshot.cashPct)} of portfolio`,
    },
    totalPnl: {
      value: formatSignedMoney(snapshot.totalPnl),
      positive: snapshot.totalPnl >= 0,
      note: `${formatSignedPercent(snapshot.totalPnlPct)} all-time`,
    },
    dailyChange: {
      value: formatSignedMoney(snapshot.dailyChange),
      positive: snapshot.dailyChange >= 0,
      note: `${formatSignedPercent(snapshot.dailyChangePct)} since open`,
    },
  }
}

export function toPositions(snapshot: Snapshot): Position[] {
  return snapshot.positions.map((p) => ({
    ticker: p.ticker,
    shares: p.shares,
    avgCost: formatPrice(p.avgCost),
    currentPrice: formatPrice(p.currentPrice),
    value: formatMoney(p.value),
    change: `${formatSignedMoney(p.gain)} (${formatSignedPercent(p.gainPct)})`,
    positive: p.gain >= 0,
    sparklinePath: closesToSparklinePath(p.closes),
  }))
}

/** Stable per ticker, independent of slice order. */
function fallbackColor(ticker: string): string {
  let hash = 0
  for (const char of ticker) hash = (hash * 31 + char.charCodeAt(0)) % 997
  return FALLBACK_COLORS[hash % FALLBACK_COLORS.length]
}

export function toAllocation(snapshot: Snapshot): AllocationSlice[] {
  return snapshot.allocation.map((entry) => ({
    ticker: entry.ticker,
    widthPct: entry.weightPct,
    color: TICKER_COLORS[entry.ticker] ?? fallbackColor(entry.ticker),
    showLabel: entry.weightPct >= MIN_LABEL_WIDTH_PCT,
  }))
}

export async function fetchSnapshot(): Promise<Snapshot> {
  const response = await fetch("/api/snapshot")
  if (!response.ok) {
    throw new Error(`snapshot request failed: ${response.status}`)
  }
  return response.json()
}
