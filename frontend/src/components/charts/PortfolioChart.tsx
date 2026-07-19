import { usePortfolioChart } from "@/hooks/portfolio"
import type { ChartPeriod } from "@/types"

// Hand-rolled SVG line chart, an exact port of the reference prototype:
// L-shaped ink axes, 3 dashed gridlines, smooth cubic curve with blue dots,
// month labels, stroke draw-in animation on mount. Geometry constants and
// the curve-smoothing math match the reference verbatim; the line itself is
// derived from real portfolio history for the selected period.
const CHART_W = 480
const CHART_H = 220
const MX = 40
const MY = 20
const CW = CHART_W - MX - 20
const CH = CHART_H - MY - 35

export function PortfolioChart({ period }: { period: ChartPeriod }) {
  const { points, dotIndices, months } = usePortfolioChart(period)

  const pts = points.map(({ x, y }) => [MX + x * CW, MY + y * CH] as const)
  let pathD = pts.length ? `M${pts[0][0]},${pts[0][1]}` : ""
  for (let i = 1; i < pts.length; i++) {
    const [px, py] = pts[i - 1]
    const [cx, cy] = pts[i]
    pathD += ` C${px + (cx - px) * 0.4},${py} ${px + (cx - px) * 0.6},${cy} ${cx},${cy}`
  }
  const gridYs = [0.25, 0.5, 0.75].map((f) => MY + f * CH)

  return (
    <svg width="100%" viewBox={`0 0 ${CHART_W} ${CHART_H}`} className="block">
      {gridYs.map((gy, i) => (
        <line
          key={`g${i}`}
          x1={MX}
          y1={gy}
          x2={MX + CW}
          y2={gy}
          stroke="#b0ada5"
          strokeWidth={1.2}
          strokeDasharray="8,6"
          opacity={0.4}
          style={{ filter: "url(#sketchy)" }}
        />
      ))}
      <line x1={MX} y1={MY - 5} x2={MX} y2={MY + CH} stroke="#1A1A1A" strokeWidth={2.2} strokeLinecap="round" style={{ filter: "url(#sketchy)" }} />
      <line x1={MX} y1={MY + CH} x2={MX + CW + 5} y2={MY + CH} stroke="#1A1A1A" strokeWidth={2.2} strokeLinecap="round" style={{ filter: "url(#sketchy)" }} />
      <path
        key={period} // remount on period switch so the draw-in animation replays
        d={pathD}
        fill="none"
        stroke="#1A1A1A"
        strokeWidth={2.5}
        strokeLinecap="round"
        style={{
          filter: "url(#sketchy)",
          strokeDasharray: 1000,
          strokeDashoffset: 0,
          animation: "drawIn 1.2s ease-out",
        }}
      />
      {dotIndices.map((di) => (
        <circle key={`d${di}`} cx={pts[di][0]} cy={pts[di][1]} r={5} fill="#3B6FE0" />
      ))}
      {months.map((m, i) => (
        <text
          key={`l${i}`}
          x={MX + (i / (months.length - 1)) * CW}
          y={MY + CH + 22}
          textAnchor="middle"
          style={{ fontFamily: "'Inter',sans-serif", fontSize: 13, fill: "#6B7280" }}
        >
          {m}
        </text>
      ))}
    </svg>
  )
}
