import { useState } from "react"

import { ArrowDownIcon, ArrowUpIcon, DividendIcon } from "@/components/icons"
import { DashedDivider, IconBadge, SketchCard } from "@/components/sketch/SketchCard"
import { FilterPills } from "@/components/sketch/FilterPills"
import { useActivityLog } from "@/hooks/usePortfolio"
import type { ActivityEntry } from "@/types"

const FILTERS = ["All", "Buys", "Sells", "Dividends"] as const
type Filter = (typeof FILTERS)[number]

const filterToType: Record<Exclude<Filter, "All">, ActivityEntry["type"]> = {
  Buys: "buy",
  Sells: "sell",
  Dividends: "dividend",
}

function ActivityIcon({ type }: { type: ActivityEntry["type"] }) {
  if (type === "buy") return <ArrowUpIcon size={16} strokeWidth={2.2} />
  if (type === "sell") return <ArrowDownIcon size={16} strokeWidth={2.2} />
  return <DividendIcon />
}

export function ActivityTab() {
  const entries = useActivityLog()
  const [filter, setFilter] = useState<Filter>("All")

  const filtered = entries.filter(
    (entry) => filter === "All" || entry.type === filterToType[filter]
  )

  return (
    <SketchCard className="px-7">
      <div className="mb-6 flex items-center justify-between">
        <div className="font-hand text-[23px] font-bold text-ink">Activity Log</div>
        <FilterPills options={FILTERS} active={filter} onChange={setFilter} />
      </div>

      {filtered.map((entry, i) => (
        <div key={`${entry.ticker}-${entry.date}`}>
          <div className="-mx-3 flex items-center gap-4 rounded-md px-3 py-4 hover:bg-[rgba(201,223,245,0.2)]">
            <IconBadge color={entry.badge} size={36}>
              <ActivityIcon type={entry.type} />
            </IconBadge>
            <div className="flex-1">
              <div className="flex items-baseline gap-2">
                <span className="font-hand text-[19px] font-bold text-ink">{entry.ticker}</span>
                <span className="font-sans text-xs text-sub">{entry.subtitle}</span>
              </div>
              <div className="mt-0.5 font-sans text-[13px] text-sub">{entry.detail}</div>
            </div>
            <div className="text-right">
              <div className={`font-sans text-[15px] font-semibold ${entry.credit ? "text-positive" : "text-ink"}`}>
                {entry.amount}
              </div>
              <div className="font-sans text-xs text-sub">{entry.date}</div>
            </div>
          </div>
          {i < filtered.length - 1 && <DashedDivider />}
        </div>
      ))}
    </SketchCard>
  )
}
