// Mapping seam: API snapshot numbers → the SummaryStat view models the
// Overview stat cards already render. Expected display strings come from the
// design reference.

import { describe, expect, it } from "vitest"

import { toAllocation, toPortfolioSummary, toPositions, type Snapshot } from "./snapshot"

const designReferenceSnapshot: Snapshot = {
  portfolioValue: 104820,
  cash: 18340,
  totalPnl: 4820,
  totalPnlPct: 4.82,
  dailyChange: -312,
  dailyChangePct: -0.3,
  cashPct: 17.5,
  weekChangePct: 4.8,
  positions: [],
  allocation: [],
}

// Design-reference rows: AAPL up $184 (+6.7%), TSLA down $310 (-7.5%).
const aaplPosition = {
  ticker: "AAPL",
  shares: 12,
  avgCost: 229.67,
  currentPrice: 245,
  value: 2940,
  gain: 184,
  gainPct: 6.7,
  closes: [238, 245],
}
const tslaPosition = {
  ticker: "TSLA",
  shares: 15,
  avgCost: 275.67,
  currentPrice: 255,
  value: 3825,
  gain: -310,
  gainPct: -7.5,
  closes: [265, 255],
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

describe("toPositions", () => {
  const [aapl, tsla] = toPositions({
    ...designReferenceSnapshot,
    positions: [aaplPosition, tslaPosition],
  })

  it("formats prices with cents and value in whole dollars", () => {
    expect(aapl.ticker).toBe("AAPL")
    expect(aapl.shares).toBe(12)
    expect(aapl.avgCost).toBe("$229.67")
    expect(aapl.currentPrice).toBe("$245.00")
    expect(aapl.value).toBe("$2,940")
  })

  it("renders gain/loss as signed money with signed percent, direction by sign", () => {
    expect(aapl.change).toBe("+$184 (+6.7%)")
    expect(aapl.positive).toBe(true)
    expect(tsla.change).toBe("-$310 (-7.5%)")
    expect(tsla.positive).toBe(false)
  })

  it("derives sparkline geometry from the raw closes", () => {
    expect(aapl.sparklinePath).toBe("M0,15 L40,1")
    expect(tsla.sparklinePath).toBe("M0,1 L40,15")
  })
})

describe("toAllocation", () => {
  const slices = toAllocation({
    ...designReferenceSnapshot,
    allocation: [
      { ticker: "NVDA", weightPct: 37.5 },
      { ticker: "AMZN", weightPct: 4.4 },
    ],
  })

  it("maps weights to slice widths with the ticker color map", () => {
    expect(slices[0]).toEqual({
      ticker: "NVDA",
      widthPct: 37.5,
      color: "#3E9B6B",
      showLabel: true,
    })
  })

  it("omits labels for slices too narrow, per the design", () => {
    expect(slices[1].showLabel).toBe(false)
  })

  it("assigns a stable fallback color to tickers outside the design set", () => {
    const [unknown] = toAllocation({
      ...designReferenceSnapshot,
      allocation: [{ ticker: "PLTR", weightPct: 100 }],
    })
    expect(unknown.color).toMatch(/^#[0-9A-Fa-f]{6}$/)

    // Stable: same ticker, same color, regardless of slice order.
    const [, reordered] = toAllocation({
      ...designReferenceSnapshot,
      allocation: [
        { ticker: "AAPL", weightPct: 50 },
        { ticker: "PLTR", weightPct: 50 },
      ],
    })
    expect(reordered.color).toBe(unknown.color)
  })
})
