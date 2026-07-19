// Mapping seam: API snapshot numbers → the SummaryStat view models the
// Overview stat cards already render. Expected display strings come from the
// design reference.

import { describe, expect, it } from "vitest"

import { toPortfolioSummary, type Snapshot } from "./snapshot"

const designReferenceSnapshot: Snapshot = {
  portfolioValue: 104820,
  cash: 18340,
  totalPnl: 4820,
  totalPnlPct: 4.82,
  dailyChange: -312,
  dailyChangePct: -0.3,
  cashPct: 17.5,
  weekChangePct: 4.8,
}

describe("toPortfolioSummary", () => {
  const summary = toPortfolioSummary(designReferenceSnapshot)

  it("maps portfolio value with the weekly note", () => {
    expect(summary.portfolioValue).toEqual({
      value: "$104,820",
      note: "+4.8% from last week",
    })
  })

  it("maps cash with its share of the portfolio", () => {
    expect(summary.cash).toEqual({
      value: "$18,340",
      note: "17.5% of portfolio",
    })
  })

  it("maps total P&L with sign-derived direction", () => {
    expect(summary.totalPnl).toEqual({
      value: "+$4,820",
      positive: true,
      note: "+4.8% all-time",
    })
  })

  it("maps daily change with sign-derived direction", () => {
    expect(summary.dailyChange).toEqual({
      value: "-$312",
      positive: false,
      note: "-0.3% since open",
    })
  })

  it("derives negative direction for a losing account", () => {
    const losing = toPortfolioSummary({
      ...designReferenceSnapshot,
      totalPnl: -1500,
      totalPnlPct: -1.5,
    })
    expect(losing.totalPnl.positive).toBe(false)
    expect(losing.totalPnl.value).toBe("-$1,500")
  })

  it("omits the weekly note when there is no week-ago equity yet", () => {
    const fresh = toPortfolioSummary({ ...designReferenceSnapshot, weekChangePct: null })
    expect(fresh.portfolioValue.note).toBe("no weekly data yet")
  })
})
