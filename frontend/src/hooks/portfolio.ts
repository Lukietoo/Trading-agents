// Data access hooks. Components consume these instead of importing mock data
// directly, so wiring the real backend (Claude Code + Alpaca service) only
// changes the hook internals. The summary is live; the rest are still mocks.

import { useEffect, useState } from "react"

import { fetchSnapshot, toPortfolioSummary } from "@/api/snapshot"
import {
  activityLog,
  allocation,
  portfolioChart,
  positions,
  recentTrades,
} from "@/data/mockData"
import type { PortfolioSummary } from "@/types"

const POLL_INTERVAL_MS = 60_000

/** Rendered until the first snapshot arrives (or while the API is down). */
const loadingSummary: PortfolioSummary = {
  portfolioValue: { value: "—", note: "loading…" },
  cash: { value: "—", note: "loading…" },
  totalPnl: { value: "—", note: "loading…" },
  dailyChange: { value: "—", note: "loading…" },
}

export function usePortfolioSummary(): PortfolioSummary {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const snapshot = await fetchSnapshot()
        if (!cancelled) setSummary(toPortfolioSummary(snapshot))
      } catch {
        // Keep showing the last good snapshot (or the loading placeholder).
      }
    }

    load()
    const interval = setInterval(load, POLL_INTERVAL_MS)
    const onFocus = () => load()
    const onVisible = () => {
      if (document.visibilityState === "visible") load()
    }
    window.addEventListener("focus", onFocus)
    document.addEventListener("visibilitychange", onVisible)
    return () => {
      cancelled = true
      clearInterval(interval)
      window.removeEventListener("focus", onFocus)
      document.removeEventListener("visibilitychange", onVisible)
    }
  }, [])

  return summary ?? loadingSummary
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
