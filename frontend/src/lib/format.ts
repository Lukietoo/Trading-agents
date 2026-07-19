// Display formatting for API numbers (numeric wire contract: the backend
// sends raw numbers, all formatting happens here).

/** Whole dollars with thousands separators, e.g. 104820 → "$104,820".
    Drops the sign — use formatSignedMoney for signed amounts. */
export function formatMoney(amount: number): string {
  return `$${Math.round(Math.abs(amount)).toLocaleString("en-US")}`
}

/** Signed whole dollars, sign outside the amount: 4820 → "+$4,820", -312 → "-$312". */
export function formatSignedMoney(amount: number): string {
  return `${amount < 0 ? "-" : "+"}${formatMoney(amount)}`
}

/** Per-share price with cents, e.g. 1065 → "$1,065.00". Drops the sign. */
export function formatPrice(amount: number): string {
  return `$${Math.abs(amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

/** One decimal place, e.g. 17.49 → "17.5%". */
export function formatPercent(pct: number): string {
  return `${Math.abs(pct).toFixed(1)}%`
}

/** Signed, one decimal place: 4.82 → "+4.8%", -0.3 → "-0.3%". */
export function formatSignedPercent(pct: number): string {
  return `${pct < 0 ? "-" : "+"}${formatPercent(pct)}`
}
