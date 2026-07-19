import { useAllocation } from "@/hooks/usePortfolio"

// Horizontal stacked allocation bar: 28px tall, 2px ink border, sketchy
// wobble, white 10px semibold labels inside each wide-enough segment.
export function AllocationBar() {
  const slices = useAllocation()
  return (
    <div className="sketchy-filter flex h-7 overflow-hidden rounded-md border-2 border-ink">
      {slices.map((slice) => (
        <div
          key={slice.ticker}
          className="flex items-center justify-center font-sans text-[10px] font-semibold text-white"
          style={{ width: `${slice.widthPct}%`, background: slice.color }}
        >
          {slice.showLabel ? slice.ticker : null}
        </div>
      ))}
    </div>
  )
}
