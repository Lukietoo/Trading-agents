// Data access hooks. Components consume these instead of importing mock data
// directly, so wiring the real backend (Claude Code + Alpaca service) only
// changes the hook internals. Summary, positions, allocation, and the chart
// are live; trades and activity are still mocks.

import { toAllocation, toPortfolioSummary, toPositions } from "@/api/snapshot"
import { useSnapshot } from "@/api/snapshotStore"
import { activityLog, recentTrades } from "@/data/mockData"
import { toPortfolioChart } from "@/lib/chart"
import type { ChartPeriod, PortfolioChartData, PortfolioSummary } from "@/types"

/** Rendered until the first snapshot arrives (or while the API is down). */
const loadingSummary: PortfolioSummary = {
  portfolioValue: { value: "—", note: "loading…" },
  cash: { value: "—", note: "loading…" },
  totalPnl: { value: "—", note: "loading…" },
  dailyChange: { value: "—", note: "loading…" },
}

export function usePortfolioSummary(): PortfolioSummary {
  const snapshot = useSnapshot()
  return snapshot ? toPortfolioSummary(snapshot) : loadingSummary
}

export function usePositions() {
  const snapshot = useSnapshot()
  return snapshot ? toPositions(snapshot) : []
}

export function useAllocation() {
  const snapshot = useSnapshot()
  return snapshot ? toAllocation(snapshot) : []
}

export function useRecentTrades() {
  return recentTrades
}

export function useActivityLog() {
  return activityLog
}

export function usePortfolioChart(period: ChartPeriod): PortfolioChartData {
  const snapshot = useSnapshot()
  return toPortfolioChart(snapshot?.history[period] ?? [])
}
