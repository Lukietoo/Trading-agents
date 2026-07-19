import { useState } from "react"

import { PortfolioChart } from "@/components/charts/PortfolioChart"
import { Sparkline } from "@/components/charts/Sparkline"
import { ArrowDownIcon, ArrowUpIcon, CashIcon, ClockIcon, TrendIcon, WalletIcon } from "@/components/icons"
import { DividedList, IconBadge, SketchCard } from "@/components/sketch/SketchCard"
import { CHART_PERIODS, SegmentedControl, type ChartPeriod } from "@/components/sketch/FilterPills"
import { usePortfolioSummary, usePositions, useRecentTrades } from "@/hooks/portfolio"
import { cn, gainLossClass } from "@/lib/utils"
import type { BadgeColor, SummaryStat } from "@/types"
import type { ReactNode } from "react"

function StatCard({
  delay,
  badge,
  icon,
  label,
  stat,
  valueClass,
}: {
  delay: number
  badge: BadgeColor
  icon: ReactNode
  label: string
  stat: SummaryStat
  /** Overrides the semantic gain/loss color for fixed-color stats. */
  valueClass?: string
}) {
  return (
    <SketchCard delay={delay}>
      <div className="mb-5 flex items-center gap-3">
        <IconBadge color={badge} size={48}>
          {icon}
        </IconBadge>
        <div className="font-hand text-[21px] font-bold text-ink">{label}</div>
      </div>
      <div
        className={cn(
          "font-hand text-[38px] leading-none font-bold",
          valueClass ?? gainLossClass(stat.positive ?? true)
        )}
      >
        {stat.value}
      </div>
      <div className="mt-1.5 font-sans text-[13px] text-sub">{stat.note}</div>
    </SketchCard>
  )
}

export function OverviewTab() {
  const summary = usePortfolioSummary()
  const positions = usePositions()
  const trades = useRecentTrades()
  // Visual-only toggle: the spec defines a single chart dataset.
  const [period, setPeriod] = useState<ChartPeriod>("1Y")

  return (
    <div>
      <div className="mb-6 grid grid-cols-4 gap-6">
        <StatCard delay={0.1} badge="blue" icon={<WalletIcon />} label="Portfolio Value" stat={summary.portfolioValue} valueClass="text-accent-blue" />
        <StatCard delay={0.2} badge="green" icon={<CashIcon />} label="Cash" stat={summary.cash} valueClass="text-positive" />
        <StatCard delay={0.3} badge="purple" icon={<TrendIcon />} label="Total P&L" stat={summary.totalPnl} />
        <StatCard delay={0.4} badge="yellow" icon={<ClockIcon />} label="Today" stat={summary.dailyChange} />
      </div>

      <div className="grid grid-cols-[45fr_55fr] gap-6">
        <div className="flex flex-col gap-6">
          <SketchCard delay={0.5} className="px-7">
            <div className="mb-6 flex items-center justify-between">
              <div className="font-hand text-[23px] font-bold text-ink">Portfolio Value</div>
              <SegmentedControl options={CHART_PERIODS} active={period} onChange={setPeriod} />
            </div>
            <PortfolioChart />
          </SketchCard>

          <SketchCard delay={0.7} className="flex-1 px-6 py-5">
            <div className="mb-3.5 font-hand text-[21px] font-bold text-ink">Recent Trades</div>
            <DividedList
              items={trades}
              itemKey={(trade) => `${trade.ticker}-${trade.date}`}
              renderItem={(trade) => (
                <div className="flex items-center justify-between py-2.5">
                  <div className="flex items-center gap-2.5">
                    <IconBadge color={trade.badge} size={28}>
                      {trade.side === "buy" ? <ArrowUpIcon size={12} strokeWidth={2.5} /> : <ArrowDownIcon size={12} strokeWidth={2.5} />}
                    </IconBadge>
                    <div>
                      <div className="font-hand text-[17px] font-bold text-ink">{trade.ticker}</div>
                      <div className="font-sans text-[11px] text-sub">{trade.summary}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-sans text-sm font-medium text-ink">{trade.amount}</div>
                    <div className="font-sans text-[11px] text-sub">{trade.date}</div>
                  </div>
                </div>
              )}
            />
          </SketchCard>
        </div>

        <SketchCard delay={0.6} className="px-7">
          <div className="mb-5 flex items-center justify-between">
            <div className="font-hand text-[23px] font-bold text-ink">Positions</div>
            <div className="flex items-center gap-2">
              <span className="font-sans text-[13px] text-sub">View:</span>
              <div className="sketchy-filter rounded-md border-2 border-ink bg-btn px-3.5 py-1.5 font-sans text-[13px] font-medium text-ink">Table</div>
            </div>
          </div>
          <DividedList
            items={positions}
            itemKey={(pos) => pos.ticker}
            renderItem={(pos) => (
              <div className="-mx-3 flex items-center rounded-md px-3 py-3.5 hover:bg-[rgba(201,223,245,0.25)]">
                <div className="flex-[0_0_80px]">
                  <div className="font-hand text-xl font-bold text-ink">{pos.ticker}</div>
                  <div className="font-sans text-xs text-sub">{pos.shares} shares</div>
                </div>
                <div className="flex-1" />
                <Sparkline path={pos.sparklinePath} positive={pos.positive} />
                <div className="ml-3 flex-[0_0_90px] text-right font-sans text-[15px] font-medium text-ink">{pos.value}</div>
                <div className="ml-2 flex-[0_0_130px] text-right font-sans text-sm font-semibold">
                  <span className={gainLossClass(pos.positive)}>{pos.change}</span>
                </div>
              </div>
            )}
          />
        </SketchCard>
      </div>
    </div>
  )
}
