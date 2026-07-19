// Expected strings are transcribed from the design reference stat cards
// (design-reference/README.md), not recomputed.

import { describe, expect, it } from "vitest"

import { formatMoney, formatPercent, formatSignedMoney, formatSignedPercent } from "./format"

describe("formatMoney", () => {
  it("renders whole dollars with thousands separators", () => {
    expect(formatMoney(104820)).toBe("$104,820")
    expect(formatMoney(18340)).toBe("$18,340")
  })

  it("rounds cents away", () => {
    expect(formatMoney(18340.49)).toBe("$18,340")
    expect(formatMoney(18340.5)).toBe("$18,341")
  })
})

describe("formatSignedMoney", () => {
  it("prefixes gains with +", () => {
    expect(formatSignedMoney(4820)).toBe("+$4,820")
  })

  it("keeps the sign outside the dollar amount for losses", () => {
    expect(formatSignedMoney(-312)).toBe("-$312")
  })

  it("treats zero as a gain", () => {
    expect(formatSignedMoney(0)).toBe("+$0")
  })
})

describe("formatPercent", () => {
  it("renders one decimal place", () => {
    expect(formatPercent(17.5)).toBe("17.5%")
    expect(formatPercent(17.49)).toBe("17.5%")
  })
})

describe("formatSignedPercent", () => {
  it("prefixes positive percentages with +", () => {
    expect(formatSignedPercent(4.82)).toBe("+4.8%")
  })

  it("renders negative percentages with -", () => {
    expect(formatSignedPercent(-0.3)).toBe("-0.3%")
  })
})
