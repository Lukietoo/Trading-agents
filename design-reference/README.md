# Handoff: Paper Trading Dashboard

## Overview
A paper trading (simulated stock portfolio) dashboard with a distinctive **hand-drawn sketch aesthetic**. The design uses wobbly borders, handwriting fonts, cream-colored cards, and subtle animations to create a playful "drawn on paper" feel. It includes 4 tabbed views, an export dropdown, and mock portfolio data.

## About the Design Files
The files in this bundle are **design references created in HTML** — interactive prototypes showing intended look and behavior. The task is to **recreate these designs in your target codebase** (React, Next.js, etc.) using its established patterns and libraries. Do not ship the HTML directly.

Open `Paper Trading Dashboard.dc.html` in a browser (it needs `support.js` alongside it) to interact with all tabs, the export menu, and hover states.

## Fidelity
**High-fidelity.** Colors, typography, spacing, border styles, and interactions are final. Recreate the UI pixel-perfectly.

---

## Visual System — "Sketchy" Hand-Drawn Style

### The Sketchy Border Effect
The core visual identity uses **SVG filters** (`feTurbulence` + `feDisplacementMap`) to make borders, cards, and UI elements look hand-drawn with slight wobble/irregularity. Three filter variants are used:
- `sketchy` — subtle displacement (scale 1.5), used on chart elements and small UI
- `sketchy2` — slightly more displacement (scale 1.8), alternate seed for animation
- `sketchyBorder` — moderate displacement (scale 2), used on cards, buttons, tabs

In production, replicate via:
- SVG filter approach (same technique) — recommended
- Or a library like [Rough.js](https://roughjs.com/) for drawing hand-drawn shapes
- Or pre-rendered wobbly border images/SVGs

### Card Style (used everywhere)
```
background: #F7F3EA (warm cream)
border: 2.5px solid #1A1A1A
border-radius: 12px
box-shadow: 3px 4px 0px rgba(0,0,0,0.07)
filter: url(#sketchyBorder)
padding: 24px
```

### Button / Tab Style
```
background: #FEFDF9 (lighter cream)
border: 2.5px solid #1A1A1A
border-radius: 8px
box-shadow: 2px 3px 0px rgba(0,0,0,0.08)
filter: url(#sketchyBorder)
```
Active state: `background: #C9DFF5` (pastel blue), no shadow
Hover state: `background: #e8f0fb`

---

## Design Tokens

### Colors
| Token | Hex | Usage |
|-------|-----|-------|
| Page background | `#F5F6F8` | Full page base |
| Card background | `#F7F3EA` | All cards and panels |
| Button background | `#FEFDF9` | Buttons, tabs, inputs |
| Primary text | `#1A1A1A` | Titles, body, borders |
| Secondary text | `#6B7280` | Subtitles, axis labels, meta text |
| Positive green | `#3E9B6B` | All positive $/% values |
| Negative coral | `#D9695E` | All negative $/% values |
| Accent blue | `#3B6FE0` | Portfolio value, chart dots |
| Active blue tint | `#C9DFF5` | Active tab/button fill |
| Hover blue tint | `#e8f0fb` | Hover state |
| Divider dashed | `#d0cec6` | Dashed row separators |
| Badge blue | `#D6E8FB` | Portfolio value icon badge |
| Badge green | `#D4F0DE` | Cash / buy icon badge |
| Badge purple | `#E8DFFA` | P&L / dividend icon badge |
| Badge yellow | `#FBEFC7` | Today / sell icon badge |
| Divider gradient left | `#E8837A` | Header divider bar (coral) |
| Divider gradient right | `#8FB8E8` | Header divider bar (blue) |

### Typography
| Role | Font | Size | Weight |
|------|------|------|--------|
| Page title | Caveat | 38px | 700 |
| Card/panel titles | Caveat | 21-23px | 700 |
| Large stat numbers | Caveat | 38px | 700 |
| Ticker symbols | Caveat | 17-20px | 700 |
| Button/tab labels | Inter | 15-16px | 500-600 |
| Body text | Inter | 14px | 400-500 |
| Secondary/meta text | Inter | 11-13px | 400 |
| Table headers | Inter | 12px | 600, uppercase, 0.5px letter-spacing |

**Rule:** Caveat (handwriting) is used ONLY for: page title, card/panel titles, large stat numbers, and ticker symbols. Everything else uses Inter.

### Spacing
- Page padding: 28px top, 32px sides, 48px bottom
- Card gap: 24px
- Card internal padding: 24px (28px horizontal on chart panels)
- Tab gap: 8px
- Max width: 1440px, centered

---

## Screens / Views

### 1. Shared Header (all tabs)
- **Title:** "Paper Trading" — Caveat 38px bold, top-left
- **Export button:** top-right, cream fill, sketchy border, download-arrow SVG icon + "Export" text. Clicking opens a dropdown menu.
- **Decorative dashed lines:** faint horizontal dashed lines cluster (opacity 0.15-0.18) near top-right and between tabs/cards — purely decorative "notebook paper" texture
- **Divider bar:** 6px tall, full width. Gray track with 65% gradient fill (coral → blue)

### 2. Navigation Tabs
Four tabs: Overview, Positions, Activity Log, Settings
- Active: pastel blue fill `#C9DFF5`, bold text, no shadow
- Inactive: cream fill, sketchy border, shadow, medium text
- Hover: light blue tint

### 3. Overview Tab
**Stat Cards Row** — 4 equal-width cards in a grid:

| Card | Icon Badge Color | Label | Value | Value Color | Subtitle |
|------|-----------------|-------|-------|-------------|----------|
| Portfolio Value | Blue `#D6E8FB` | Portfolio Value | $104,820 | Blue `#3B6FE0` | +4.8% from last week |
| Cash | Green `#D4F0DE` | Cash | $18,340 | Green `#3E9B6B` | 17.5% of portfolio |
| Total P&L | Purple `#E8DFFA` | Total P&L | +$4,820 | Green `#3E9B6B` | +4.8% all-time |
| Daily Change | Yellow `#FBEFC7` | Today | -$312 | Coral `#D9695E` | -0.3% since open |

Each card has a 48px circular pastel icon badge with a black line-art SVG icon.

**Color rule:** Positive values → green `#3E9B6B`, negative → coral `#D9695E`. This is semantic, not tied to the card's badge color.

**Chart Panels Row** — 45/55 split:

**Left column (stacked):**
1. **Portfolio Value chart** — line chart with L-shaped axes, 3 dashed gridlines, smooth curve with 5 blue data dots, month labels. Toggle pills: 1M / 3M / 1Y (1Y active). SVG-based with sketchy filter on lines.
2. **Recent Trades** — 3 rows with circular icon badges (arrow-up for Buy in green, arrow-down for Sell in coral), ticker, description, amount, date. Dashed dividers between rows.

**Right column:**
- **Positions table** — 6 stock rows with: ticker (Caveat bold), shares count, inline sparkline SVG (40×16px, colored by gain/loss direction), value, gain/loss percentage. Dashed dividers. Hover highlights row with blue tint.

### 4. Positions Tab
- **Portfolio Allocation bar** — horizontal stacked bar showing position weights by color (AAPL blue, NVDA green, TSLA coral, MSFT purple, AMZN amber, META indigo)
- **All Positions table** — filter pills (All / Winners / Losers), table with columns: Ticker, Shares, Avg Cost, Current, Value, Gain/Loss. Table header has uppercase labels with 2px bottom border.

### 5. Activity Log Tab
- Filter pills: All / Buys / Sells / Dividends
- 8 activity entries with:
  - Circular icon badge (36px): arrow-up SVG for buys, arrow-down for sells, plus-circle for dividends
  - Title (Caveat bold) + subtitle (Inter gray)
  - Detail text
  - Amount (colored: green for credits, dark for debits) + date
  - Dashed dividers

### 6. Settings Tab
Two-column grid:

**Left — Account:**
- Account Name field: "My Paper Portfolio"
- Starting Balance field: "$100,000.00"
- Account Created field: "January 15, 2026"
- "Reset Account" button: coral fill `#D9695E`, white text

**Right — Preferences:**
- Toggle switches (sketchy pill shape): "Show sparklines" (on), "Show daily change card" (on), "Compact position rows" (off)
  - On state: green `#3E9B6B` background, knob right
  - Off state: gray `#e0e2e6` background, knob left
- Default chart period: segmented control (1M / 3M / 1Y)
- Currency display: dropdown showing "USD ($)"

### 7. Export Dropdown
Appears when Export button is clicked. Positioned absolutely below button.
- 4 items: Export as CSV, Export as PDF, Schedule Report, Share Dashboard
- Each with an SVG icon on the left
- Dashed separator between PDF and Schedule Report
- Hover: blue tint `#C9DFF5`
- Card styling with sketchy border, 4px shadow

---

## Interactions & Behavior

### Tab Navigation
- State: `activeTab` — one of `overview`, `positions`, `activity`, `settings`
- Clicking a tab sets it active and closes the export menu
- Content fades up on tab switch (fadeUp animation, 0.4s ease-out)

### Export Menu
- State: `showExport` — boolean toggle
- Click Export button to toggle
- Click outside or switch tab to close (currently closes on tab switch)

### Animations
- **Page load:** Cards fade up sequentially (0.1s staggered delays)
- **Chart line:** SVG stroke draw-in animation (1.2s ease-out, via `stroke-dasharray`/`stroke-dashoffset`)
- **Tab content:** fadeUp 0.4s on tab switch

### Hover States
- Buttons/tabs: background shifts to `#e8f0fb` or `#f0eddf`
- Position rows: blue tint background with rounded corners
- Export menu items: blue tint `#C9DFF5`

---

## Icons
All icons are inline SVGs with consistent style:
- Stroke-only (no fill), `#1A1A1A` for card icons
- stroke-width: 1.8 for card icons, 2.2 for activity icons, 1.6 for export menu icons
- stroke-linecap: round
- Activity icons use semantic colors: green for buy arrows, coral for sell arrows, purple for dividend

---

## Mock Data

### Positions
| Ticker | Shares | Avg Cost | Current | Value | Change |
|--------|--------|----------|---------|-------|--------|
| AAPL | 12 | $229.67 | $245.00 | $2,940 | +$184 (+6.7%) |
| NVDA | 8 | $1,065.00 | $1,220.00 | $9,760 | +$1,240 (+14.6%) |
| TSLA | 15 | $275.67 | $255.00 | $3,825 | -$310 (-7.5%) |
| MSFT | 10 | $411.50 | $421.00 | $4,210 | +$95 (+2.3%) |
| AMZN | 6 | $198.67 | $190.00 | $1,140 | -$52 (-4.4%) |
| META | 9 | $360.22 | $390.00 | $3,510 | +$268 (+8.3%) |

### Summary Stats
- Portfolio Value: $104,820 (+4.8% from last week)
- Cash Available: $18,340 (17.5% of portfolio)
- Total P&L: +$4,820 (+4.8% all-time)
- Daily Change: -$312 (-0.3% since open)

---

## Files
- `Paper Trading Dashboard.dc.html` — full interactive prototype (open in browser with `support.js`)
- `support.js` — runtime for the DC format
- `screenshots/overview.png` — overview tab screenshot

## Notes for Implementation
1. The SVG filter approach for sketchy borders is the most faithful; consider [Rough.js](https://roughjs.com/) as an alternative
2. Google Fonts: `Caveat:wght@400;700` and `Inter:wght@400;500;600`
3. The chart is SVG-based; in production use a charting library (e.g. Recharts, D3) with custom styling to match the hand-drawn aesthetic
4. Sparklines in position rows are tiny inline SVGs — libraries like `react-sparklines` could help
5. All data is mock/static in the prototype; wire to your data layer as needed
