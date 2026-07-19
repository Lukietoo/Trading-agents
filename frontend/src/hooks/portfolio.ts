// Data access hooks. Components consume these instead of importing mock data
// directly, so wiring the real backend later only changes the hook internals
// (e.g. fetch + cache against the TradingAgents/Alpaca service).

import {
  activityLog,
  allocation,
  portfolioChart,
  portfolioSummary,
  positions,
  recentTrades,
} from "@/data/mockData"

export function usePortfolioSummary() {
  return portfolioSummary
}

export function usePositions() {
  return positions
}

export function useRecentTrades() {
  return recentTrades
}

export function useActivityLog() {
  return activityLog
}

export function usePortfolioChart() {
  return portfolioChart
}

export function useAllocation() {
  return allocation
}
