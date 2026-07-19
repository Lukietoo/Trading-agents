import { useEffect, useState } from "react"

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { CsvIcon, DownloadIcon, PdfIcon, ScheduleIcon, ShareIcon } from "@/components/icons"

// Decorative "notebook paper" dashed-line clusters, exact from reference.
function DashedTexture({ lines, width, height }: { lines: number[][]; width: number; height: number }) {
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      {lines.map(([x1, y, x2, sw, dashA, dashB], i) => (
        <line key={i} x1={x1} y1={y} x2={x2} y2={y} stroke="#888" strokeWidth={sw} strokeDasharray={`${dashA},${dashB}`} />
      ))}
    </svg>
  )
}

const headerTexture = [
  [8, 4, 52, 1.5, 6, 4], [5, 9, 55, 1.2, 5, 5], [10, 14, 50, 1.5, 7, 3], [7, 19, 53, 1.3, 4, 5],
  [9, 24, 48, 1.4, 6, 4], [6, 29, 54, 1.2, 5, 4], [11, 34, 49, 1.5, 7, 3], [8, 39, 52, 1.3, 4, 6],
]

const belowDividerTexture = [
  [5, 4, 58, 1.5, 5, 5], [8, 9, 55, 1.3, 6, 4], [3, 14, 60, 1.5, 4, 5], [7, 19, 56, 1.2, 7, 3],
  [4, 24, 59, 1.4, 5, 4], [9, 29, 53, 1.3, 6, 5], [6, 34, 57, 1.5, 4, 4], [5, 39, 58, 1.2, 7, 4],
]

// Shared header: page title, export button + dropdown, decorative dashed
// texture, and the coral→blue gradient divider bar. The export menu closes
// on outside click (Radix) and on tab switch (via the activeTab prop).
export function Header({ activeTab }: { activeTab: string }) {
  const [exportOpen, setExportOpen] = useState(false)

  useEffect(() => {
    setExportOpen(false)
  }, [activeTab])

  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <h1 className="font-hand text-[38px] leading-[1.1] font-bold text-ink">Paper Trading</h1>
        <div className="relative flex items-center">
          <div className="absolute -top-8 right-0 opacity-[0.18]">
            <DashedTexture lines={headerTexture} width={60} height={40} />
          </div>
          {/* modal={false} so a click on a tab while the menu is open both
              closes the menu and switches tabs, matching the reference. */}
          <DropdownMenu modal={false} open={exportOpen} onOpenChange={setExportOpen}>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="sketch-btn flex cursor-pointer items-center gap-2 px-5 py-2.5 font-sans text-[15px] font-medium text-ink outline-none hover:bg-hover-cream hover:shadow-[1px_2px_0px_rgba(0,0,0,0.06)] focus-visible:ring-2 focus-visible:ring-accent-blue/50"
              >
                <DownloadIcon />
                Export
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" sideOffset={6}>
              <DropdownMenuItem>
                <CsvIcon />
                Export as CSV
              </DropdownMenuItem>
              <DropdownMenuItem>
                <PdfIcon />
                Export as PDF
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <ScheduleIcon />
                Schedule Report
              </DropdownMenuItem>
              <DropdownMenuItem>
                <ShareIcon />
                Share Dashboard
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="relative mb-6 h-1.5">
        <div className="absolute inset-0 rounded-[3px] bg-[#e0e2e6]" />
        <div className="absolute top-0 bottom-0 left-0 w-[65%] rounded-[3px] bg-[linear-gradient(to_right,#E8837A_0%,#E8837A_35%,#8FB8E8_100%)]" />
      </div>

      <div className="relative">
        <div className="absolute top-0 right-10 opacity-[0.15]">
          <DashedTexture lines={belowDividerTexture} width={65} height={44} />
        </div>
      </div>
    </>
  )
}
