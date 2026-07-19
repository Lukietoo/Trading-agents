import { useState } from "react"

import { AllocationBar } from "@/components/charts/AllocationBar"
import { DashedDivider, SketchCard } from "@/components/sketch/SketchCard"
import { FilterPills } from "@/components/sketch/FilterPills"
import { usePositions } from "@/hooks/usePortfolio"

const FILTERS = ["All", "Winners", "Losers"] as const
type Filter = (typeof FILTERS)[number]

const headerCell = "font-sans text-xs font-semibold text-sub uppercase tracking-[0.5px]"

export function PositionsTab() {
  const positions = usePositions()
  const [filter, setFilter] = useState<Filter>("All")

  const filtered = positions.filter((pos) =>
    filter === "All" ? true : filter === "Winners" ? pos.positive : !pos.positive
  )

  return (
    <div>
      <SketchCard className="mb-6 px-7">
        <div className="mb-4 font-hand text-[23px] font-bold text-ink">Portfolio Allocation</div>
        <AllocationBar />
      </SketchCard>

      <SketchCard className="px-7">
        <div className="mb-5 flex items-center justify-between">
          <div className="font-hand text-[23px] font-bold text-ink">All Positions</div>
          <FilterPills options={FILTERS} active={filter} onChange={setFilter} />
        </div>

        <div className="mb-1 flex items-center border-b-2 border-ink py-2.5">
          <div className={`flex-[0_0_90px] ${headerCell}`}>Ticker</div>
          <div className={`flex-[0_0_90px] ${headerCell}`}>Shares</div>
          <div className={`flex-[0_0_100px] ${headerCell}`}>Avg Cost</div>
          <div className={`flex-[0_0_100px] ${headerCell}`}>Current</div>
          <div className="flex-1" />
          <div className={`flex-[0_0_100px] text-right ${headerCell}`}>Value</div>
          <div className={`flex-[0_0_140px] text-right ${headerCell}`}>Gain/Loss</div>
        </div>

        {filtered.map((pos, i) => (
          <div key={pos.ticker}>
            <div className="-mx-3 flex items-center rounded-md px-3 py-4 hover:bg-[rgba(201,223,245,0.2)]">
              <div className="flex-[0_0_90px]">
                <div className="font-hand text-xl font-bold text-ink">{pos.ticker}</div>
              </div>
              <div className="flex-[0_0_90px] font-sans text-sm text-ink">{pos.shares}</div>
              <div className="flex-[0_0_100px] font-sans text-sm text-sub">{pos.avgCost}</div>
              <div className="flex-[0_0_100px] font-sans text-sm text-ink">{pos.current}</div>
              <div className="flex-1" />
              <div className="flex-[0_0_100px] text-right font-sans text-[15px] font-medium text-ink">{pos.value}</div>
              <div className="flex-[0_0_140px] text-right font-sans text-sm font-semibold">
                <span className={pos.positive ? "text-positive" : "text-negative"}>{pos.change}</span>
              </div>
            </div>
            {i < filtered.length - 1 && <DashedDivider />}
          </div>
        ))}
      </SketchCard>
    </div>
  )
}
