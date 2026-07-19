// Portfolio chart geometry seam: raw timestamp/equity history → the
// normalized points, dot indices, and axis labels PortfolioChart renders.
// Expected values are worked out by hand from the scaling rules (x spread by
// timestamp over 0..1, y mapping min..max equity onto 0.9..0.1).

import { describe, expect, it } from "vitest"

import { toPortfolioChart } from "./chart"

const DAY = 86_400

/** n evenly-spaced daily samples starting 2026-07-01 UTC. */
function dailySeries(values: number[], startT = 1_782_864_000) {
  return values.map((v, i) => ({ t: startT + i * DAY, v }))
}

describe("toPortfolioChart", () => {
  it("maps min equity to y 0.9 and max to y 0.1, x by timestamp", () => {
    const { points } = toPortfolioChart(dailySeries([100_000, 102_000, 104_000]))

    expect(points).toEqual([
      { x: 0, y: 0.9 },
      { x: 0.5, y: 0.5 },
      { x: 1, y: 0.1 },
    ])
  })

  it("positions x by time, not sample index, when spacing is uneven", () => {
    // Gaps of 1 and 3 days: the middle sample sits a quarter of the way in.
    const t0 = 1_782_864_000
    const { points } = toPortfolioChart([
      { t: t0, v: 100_000 },
      { t: t0 + DAY, v: 104_000 },
      { t: t0 + 4 * DAY, v: 100_000 },
    ])

    expect(points.map((p) => p.x)).toEqual([0, 0.25, 1])
  })

  it("spreads x by index when every sample shares one timestamp", () => {
    // Degenerate series (e.g. duplicate same-day samples): no time span to
    // normalize by, so fall back to even spacing.
    const t = 1_782_864_000
    const { points } = toPortfolioChart([
      { t, v: 100_000 },
      { t, v: 102_000 },
      { t, v: 104_000 },
    ])

    expect(points.map((p) => p.x)).toEqual([0, 0.5, 1])
  })

  it("draws a flat series along the vertical midline", () => {
    const { points } = toPortfolioChart(dailySeries([100_000, 100_000, 100_000]))

    expect(points.map((p) => p.y)).toEqual([0.5, 0.5, 0.5])
  })

  it("returns empty geometry for fewer than two samples", () => {
    expect(toPortfolioChart([])).toEqual({ points: [], dotIndices: [], months: [] })
    expect(toPortfolioChart(dailySeries([100_000]))).toEqual({
      points: [],
      dotIndices: [],
      months: [],
    })
  })

  it("places five dots evenly across a long series", () => {
    const { dotIndices, points } = toPortfolioChart(
      dailySeries(Array.from({ length: 21 }, (_, i) => 100_000 + i))
    )

    expect(dotIndices).toEqual([0, 5, 10, 15, 20])
    expect(points).toHaveLength(21)
  })

  it("dedupes dots on tiny series instead of stacking them", () => {
    const { dotIndices } = toPortfolioChart(dailySeries([100_000, 104_000]))

    expect(dotIndices).toEqual([0, 1])
  })

  it("downsamples long series to at most 30 points, keeping the endpoints", () => {
    const values = Array.from({ length: 250 }, (_, i) => 100_000 + i)
    const { points } = toPortfolioChart(dailySeries(values))

    expect(points.length).toBeLessThanOrEqual(30)
    expect(points[0]).toEqual({ x: 0, y: 0.9 })
    expect(points[points.length - 1]).toEqual({ x: 1, y: 0.1 })
  })

  it("labels year-scale spans with month names only", () => {
    // 360 daily samples from 2026-07-01: first label Jul 2026, last Jun 2027.
    const values = Array.from({ length: 360 }, (_, i) => 100_000 + i)
    const { months } = toPortfolioChart(dailySeries(values))

    expect(months).toHaveLength(7)
    expect(months[0]).toBe("Jul")
    expect(months[6]).toBe("Jun")
  })

  it("labels short spans with month and day", () => {
    // 2026-07-01 through 2026-07-30 UTC.
    const values = Array.from({ length: 30 }, (_, i) => 100_000 + i)
    const { months } = toPortfolioChart(dailySeries(values))

    expect(months[0]).toBe("Jul 1")
    expect(months[months.length - 1]).toBe("Jul 30")
  })
})
