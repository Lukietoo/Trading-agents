// Core data shapes for the paper trading dashboard.
// These types define the contract the future backend API must conform to
// (custom Python service wrapping TradingAgents + Alpaca paper trading).

export type BadgeColor = "blue" | "green" | "purple" | "yellow"

/** One headline stat card: display value, direction, and the note beneath. */
export interface SummaryStat {
  value: string
  /** Omitted for stats rendered in a fixed color (Portfolio Value, Cash). */
  positive?: boolean
  note: string
}

export interface PortfolioSummary {
  portfolioValue: SummaryStat
  cash: SummaryStat
  totalPnl: SummaryStat
  dailyChange: SummaryStat
}

export interface Position {
  ticker: string
  shares: number
  avgCost: string
  currentPrice: string
  value: string
  /** e.g. "+$184 (+6.7%)" */
  change: string
  positive: boolean
  /** SVG path in a 40x16 viewBox */
  sparklinePath: string
}

export type TradeSide = "buy" | "sell"

/** Compact row in the Overview "Recent Trades" panel. */
export interface TradeEntry {
  ticker: string
  side: TradeSide
  /** Display line under the ticker, e.g. "Buy · 3 shares". */
  summary: string
  amount: string
  date: string
  badge: BadgeColor
}

export type ActivityType = "buy" | "sell" | "dividend"

export interface ActivityEntry {
  type: ActivityType
  ticker: string
  subtitle: string
  detail: string
  amount: string
  /** Credits (sells, dividends) render green; debit amounts render ink —
      the documented exception to the green/coral rule (CONTEXT.md). */
  credit: boolean
  date: string
  badge: BadgeColor
}

/** Normalized 0..1 coordinates within the chart plot area. */
export interface ChartDataPoint {
  x: number
  y: number
}

export interface PortfolioChartData {
  points: ChartDataPoint[]
  /** Indices into `points` that get a blue dot. */
  dotIndices: number[]
  months: string[]
}

export interface AllocationSlice {
  ticker: string
  widthPct: number
  color: string
  /** Slices too narrow for a label omit it (e.g. AMZN at 4.4%). */
  showLabel: boolean
}
