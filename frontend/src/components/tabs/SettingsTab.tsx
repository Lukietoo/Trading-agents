import { useState } from "react"

import { ChevronDownIcon } from "@/components/icons"
import { DashedDivider, SketchCard } from "@/components/sketch/SketchCard"
import { CHART_PERIODS, SegmentedControl, type ChartPeriod } from "@/components/sketch/FilterPills"
import { Switch } from "@/components/ui/switch"

const fieldLabel = "mb-1.5 font-sans text-xs font-semibold text-sub uppercase tracking-[0.5px]"
const fieldBox = "sketchy-filter rounded-md border-2 border-ink bg-btn px-3.5 py-2.5 font-sans text-sm"

function PreferenceToggle({ label, defaultOn }: { label: string; defaultOn: boolean }) {
  const [on, setOn] = useState(defaultOn)
  return (
    <div className="flex items-center justify-between">
      <div className="font-sans text-sm text-ink">{label}</div>
      <Switch checked={on} onCheckedChange={setOn} />
    </div>
  )
}

export function SettingsTab() {
  const [period, setPeriod] = useState<ChartPeriod>("1Y")

  return (
    <div className="grid grid-cols-2 gap-6">
      <SketchCard className="px-7">
        <div className="mb-5 font-hand text-[23px] font-bold text-ink">Account</div>
        <div className="flex flex-col gap-4">
          <div>
            <div className={fieldLabel}>Account Name</div>
            <div className={`${fieldBox} text-ink`}>My Paper Portfolio</div>
          </div>
          <div>
            <div className={fieldLabel}>Starting Balance</div>
            <div className={`${fieldBox} text-ink`}>$100,000.00</div>
          </div>
          <div>
            <div className={fieldLabel}>Account Created</div>
            <div className={`${fieldBox} text-sub`}>January 15, 2026</div>
          </div>
          <div className="mt-2 flex gap-3">
            <button
              type="button"
              className="sketchy-border-filter cursor-pointer rounded-lg border-[2.5px] border-ink bg-negative px-5 py-2.5 font-sans text-sm font-medium text-white outline-none hover:opacity-90 focus-visible:ring-2 focus-visible:ring-accent-blue/50"
            >
              Reset Account
            </button>
          </div>
        </div>
      </SketchCard>

      <SketchCard className="px-7">
        <div className="mb-5 font-hand text-[23px] font-bold text-ink">Preferences</div>
        <div className="flex flex-col gap-[18px]">
          <PreferenceToggle label="Show sparklines in positions" defaultOn />
          <DashedDivider />
          <PreferenceToggle label="Show daily change card" defaultOn />
          <DashedDivider />
          <PreferenceToggle label="Compact position rows" defaultOn={false} />
          <DashedDivider />
          <div>
            <div className="mb-2 font-sans text-sm text-ink">Default chart period</div>
            <SegmentedControl options={CHART_PERIODS} active={period} onChange={setPeriod} size="md" />
          </div>
          <DashedDivider />
          <div>
            <div className="mb-2 font-sans text-sm text-ink">Currency display</div>
            <div className={`${fieldBox} flex cursor-pointer items-center justify-between text-ink`}>
              <span>USD ($)</span>
              <ChevronDownIcon />
            </div>
          </div>
        </div>
      </SketchCard>
    </div>
  )
}
