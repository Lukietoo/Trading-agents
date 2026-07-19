// Mock data transcribed verbatim from design-reference — do not invent numbers.
// Sources: design-reference/README.md tables and the reference prototype's
// data arrays in "Paper Trading Dashboard.dc.html".

import type {
  ActivityEntry,
  AllocationSlice,
  PortfolioChartData,
  Position,
  TradeEntry,
} from "@/types"

const sparklinePaths = [
  "M0,12 Q5,10 10,8 T20,5 T30,3 T40,2",
  "M0,14 Q8,12 12,8 T24,4 T32,2 T40,1",
  "M0,3 Q8,4 14,7 T24,10 T32,12 T40,14",
  "M0,8 Q8,7 14,7 T24,6 T32,6 T40,5",
  "M0,4 Q8,5 14,7 T24,9 T32,11 T40,13",
  "M0,13 Q6,11 12,8 T22,5 T32,3 T40,2",
]

export const positions: Position[] = [
  { ticker: "AAPL", shares: 12, avgCost: "$229.67", currentPrice: "$245.00", value: "$2,940", change: "+$184 (+6.7%)", positive: true, sparklinePath: sparklinePaths[0] },
  { ticker: "NVDA", shares: 8, avgCost: "$1,065.00", currentPrice: "$1,220.00", value: "$9,760", change: "+$1,240 (+14.6%)", positive: true, sparklinePath: sparklinePaths[1] },
  { ticker: "TSLA", shares: 15, avgCost: "$275.67", currentPrice: "$255.00", value: "$3,825", change: "-$310 (-7.5%)", positive: false, sparklinePath: sparklinePaths[2] },
  { ticker: "MSFT", shares: 10, avgCost: "$411.50", currentPrice: "$421.00", value: "$4,210", change: "+$95 (+2.3%)", positive: true, sparklinePath: sparklinePaths[3] },
  { ticker: "AMZN", shares: 6, avgCost: "$198.67", currentPrice: "$190.00", value: "$1,140", change: "-$52 (-4.4%)", positive: false, sparklinePath: sparklinePaths[4] },
  { ticker: "META", shares: 9, avgCost: "$360.22", currentPrice: "$390.00", value: "$3,510", change: "+$268 (+8.3%)", positive: true, sparklinePath: sparklinePaths[5] },
]

export const recentTrades: TradeEntry[] = [
  { ticker: "NVDA", side: "buy", summary: "Buy · 3 shares", amount: "$3,660", date: "Today", badge: "green" },
  { ticker: "TSLA", side: "sell", summary: "Sell · 5 shares", amount: "$1,275", date: "Yesterday", badge: "yellow" },
  { ticker: "AAPL", side: "buy", summary: "Buy · 4 shares", amount: "$980", date: "Jul 15", badge: "blue" },
]

export const activityLog: ActivityEntry[] = [
  { type: "buy", ticker: "NVDA", subtitle: "Market Buy", detail: "Bought 3 shares at $1,220.00", amount: "-$3,660.00", credit: false, date: "Jul 18, 2026", badge: "green" },
  { type: "sell", ticker: "TSLA", subtitle: "Market Sell", detail: "Sold 5 shares at $255.00", amount: "+$1,275.00", credit: true, date: "Jul 17, 2026", badge: "yellow" },
  { type: "buy", ticker: "AAPL", subtitle: "Market Buy", detail: "Bought 4 shares at $245.00", amount: "-$980.00", credit: false, date: "Jul 15, 2026", badge: "blue" },
  { type: "dividend", ticker: "MSFT", subtitle: "Dividend", detail: "Quarterly dividend · $0.75/share", amount: "+$7.50", credit: true, date: "Jul 12, 2026", badge: "purple" },
  { type: "buy", ticker: "META", subtitle: "Limit Buy", detail: "Bought 9 shares at $360.22", amount: "-$3,241.98", credit: false, date: "Jul 8, 2026", badge: "green" },
  { type: "sell", ticker: "AMZN", subtitle: "Market Sell", detail: "Sold 2 shares at $195.50", amount: "+$391.00", credit: true, date: "Jul 5, 2026", badge: "yellow" },
  { type: "buy", ticker: "NVDA", subtitle: "Market Buy", detail: "Bought 5 shares at $1,065.00", amount: "-$5,325.00", credit: false, date: "Jun 28, 2026", badge: "blue" },
  { type: "dividend", ticker: "AAPL", subtitle: "Dividend", detail: "Quarterly dividend · $0.25/share", amount: "+$3.00", credit: true, date: "Jun 20, 2026", badge: "purple" },
]

export const portfolioChart: PortfolioChartData = {
  points: [
    { x: 0, y: 0.85 }, { x: 0.08, y: 0.78 }, { x: 0.16, y: 0.72 }, { x: 0.22, y: 0.55 }, { x: 0.3, y: 0.45 },
    { x: 0.38, y: 0.32 }, { x: 0.45, y: 0.22 }, { x: 0.52, y: 0.18 }, { x: 0.58, y: 0.24 }, { x: 0.65, y: 0.28 },
    { x: 0.72, y: 0.35 }, { x: 0.8, y: 0.42 }, { x: 0.86, y: 0.38 }, { x: 0.92, y: 0.3 }, { x: 1, y: 0.25 },
  ],
  dotIndices: [0, 3, 7, 12, 14],
  months: ["Jul", "Sep", "Nov", "Jan", "Mar", "May", "Jul"],
}

export const allocation: AllocationSlice[] = [
  { ticker: "AAPL", widthPct: 11.3, color: "#3B6FE0", showLabel: true },
  { ticker: "NVDA", widthPct: 37.5, color: "#3E9B6B", showLabel: true },
  { ticker: "TSLA", widthPct: 14.7, color: "#D9695E", showLabel: true },
  { ticker: "MSFT", widthPct: 16.2, color: "#8B5CF6", showLabel: true },
  { ticker: "AMZN", widthPct: 4.4, color: "#F59E0B", showLabel: false },
  { ticker: "META", widthPct: 13.5, color: "#6366F1", showLabel: true },
]
