// Derives sparkline SVG geometry from raw closing prices (the wire carries
// numbers, never path strings). Coordinates live in the Sparkline component's
// 40x16 viewBox, with 1px vertical padding so the 2px stroke isn't clipped.

const WIDTH = 40
const TOP = 1
const BOTTOM = 15

function round2(n: number): string {
  return String(Math.round(n * 100) / 100)
}

/** Oldest-first closes → "M x,y L x,y …"; "" when there's nothing to draw. */
export function closesToSparklinePath(closes: number[]): string {
  if (closes.length < 2) return ""
  const min = Math.min(...closes)
  const max = Math.max(...closes)
  const midline = (TOP + BOTTOM) / 2
  return closes
    .map((close, i) => {
      const x = (i / (closes.length - 1)) * WIDTH
      const y = max === min ? midline : TOP + ((max - close) / (max - min)) * (BOTTOM - TOP)
      return `${i === 0 ? "M" : "L"}${round2(x)},${round2(y)}`
    })
    .join(" ")
}
