// Sparkline geometry seam: raw closing prices → an SVG path in the 40x16
// viewBox the Sparkline component renders. Expected coordinates are worked
// out by hand from the scaling rule (x spread evenly over 0..40, y mapping
// the min..max close range onto 15..1, top-padded).

import { describe, expect, it } from "vitest"

import { closesToSparklinePath } from "./sparkline"

describe("closesToSparklinePath", () => {
  it("spreads closes evenly across the viewBox and scales min to 15, max to 1", () => {
    // 100 (min) → y 15, 110 (max) → y 1, 105 (midpoint) → y 8.
    expect(closesToSparklinePath([100, 105, 110])).toBe("M0,15 L20,8 L40,1")
  })

  it("draws a rising line for ascending closes", () => {
    expect(closesToSparklinePath([1, 2, 3, 4, 5])).toBe(
      "M0,15 L10,11.5 L20,8 L30,4.5 L40,1"
    )
  })

  it("draws a flat midline when every close is equal", () => {
    expect(closesToSparklinePath([250, 250, 250])).toBe("M0,8 L20,8 L40,8")
  })

  it("returns an empty path for fewer than two closes", () => {
    expect(closesToSparklinePath([])).toBe("")
    expect(closesToSparklinePath([245])).toBe("")
  })

  it("rounds coordinates to two decimals", () => {
    // Three equal steps over thirds of the width: 40/3 = 13.333…
    expect(closesToSparklinePath([0, 1, 2, 3])).toBe(
      "M0,15 L13.33,10.33 L26.67,5.67 L40,1"
    )
  })
})
