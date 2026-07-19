// Mock data transcribed verbatim from design-reference — do not invent numbers.
// Sources: design-reference/README.md tables and the reference prototype's
// data arrays in "Paper Trading Dashboard.dc.html".

import type {
  ActivityEntry,
  PortfolioChartData,
  TradeEntry,
} from "@/types"

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
