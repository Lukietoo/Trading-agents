// Dashboard snapshot API: wire types, fetch, and mapping to the SummaryStat
// view models the Overview stat cards render.

import { formatMoney, formatPercent, formatSignedMoney, formatSignedPercent } from "@/lib/format"
import type { PortfolioSummary, Snapshot } from "@/types"

export type { Snapshot }

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

export async function fetchSnapshot(): Promise<Snapshot> {
  const response = await fetch("/api/snapshot")
  if (!response.ok) {
    throw new Error(`snapshot request failed: ${response.status}`)
  }
  return response.json()
}
