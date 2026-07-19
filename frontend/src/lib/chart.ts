// Derives the Portfolio Value chart geometry from a raw portfolio-history
// series (the wire carries timestamp/value pairs, never coordinates).
// Coordinates are normalized 0..1 within the plot area: x by timestamp, y
// mapping the equity range onto 0.9 (min) .. 0.1 (max) so the line keeps the
// inset look of the design reference.

import type { HistoryPoint, PortfolioChartData } from "@/types"

const Y_TOP = 0.1
const Y_BOTTOM = 0.9

/** Enough for the sketchy curve; real daily series can run to ~250 samples. */
const MAX_POINTS = 30
const DOT_COUNT = 5
const MAX_LABELS = 7

/** Spans longer than this get month-only labels; shorter get month + day. */
const MONTH_ONLY_SPAN_SECONDS = 180 * 86_400

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

function round4(n: number): number {
  return Math.round(n * 10_000) / 10_000
}

/** Evenly-spaced indices 0..n-1 (count clamped to n), always including both ends. */
function spreadIndices(n: number, count: number): number[] {
  const last = n - 1
  const picks = Math.min(count, n)
  const indices = Array.from({ length: picks }, (_, i) => Math.round((i * last) / (picks - 1)))
  return [...new Set(indices)]
}

function formatLabel(t: number, monthOnly: boolean): string {
  const date = new Date(t * 1000)
  const month = MONTHS[date.getUTCMonth()]
  return monthOnly ? month : `${month} ${date.getUTCDate()}`
}

/** Oldest-first history → chart geometry; empty geometry below two samples. */
export function toPortfolioChart(series: HistoryPoint[]): PortfolioChartData {
  if (series.length < 2) return { points: [], dotIndices: [], months: [] }

  const sampled = spreadIndices(series.length, MAX_POINTS).map((i) => series[i])
  const t0 = sampled[0].t
  const span = sampled[sampled.length - 1].t - t0
  const values = sampled.map((p) => p.v)
  const min = Math.min(...values)
  const max = Math.max(...values)

  const points = sampled.map(({ t, v }, i) => ({
    // Zero span (all samples share a timestamp) falls back to even spacing.
    x: span === 0 ? round4(i / (sampled.length - 1)) : round4((t - t0) / span),
    y: max === min ? 0.5 : round4(Y_BOTTOM - ((v - min) / (max - min)) * (Y_BOTTOM - Y_TOP)),
  }))

  const monthOnly = span > MONTH_ONLY_SPAN_SECONDS
  const labelCount = Math.min(MAX_LABELS, sampled.length)
  const months = Array.from({ length: labelCount }, (_, i) =>
    formatLabel(t0 + (i * span) / (labelCount - 1), monthOnly)
  )

  return { points, dotIndices: spreadIndices(points.length, DOT_COUNT), months }
}
