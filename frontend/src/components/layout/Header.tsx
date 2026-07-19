import { useEffect, useState } from "react"

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { CsvIcon, DownloadIcon, PdfIcon, ScheduleIcon, ShareIcon } from "@/components/icons"

// One horizontal dashed stroke in a decorative texture cluster.
interface DashedLine {
  x1: number
  x2: number
  y: number
  strokeWidth: number
  /** SVG stroke-dasharray, e.g. "6,4" */
  dash: string
}

// Decorative "notebook paper" dashed-line clusters, exact from reference.
function DashedTexture({ lines, width, height }: { lines: DashedLine[]; width: number; height: number }) {
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      {lines.map((l, i) => (
        <line key={i} x1={l.x1} y1={l.y} x2={l.x2} y2={l.y} stroke="#888" strokeWidth={l.strokeWidth} strokeDasharray={l.dash} />
      ))}
    </svg>
  )
}

const headerTexture: DashedLine[] = [
  { x1: 8, y: 4, x2: 52, strokeWidth: 1.5, dash: "6,4" },
  { x1: 5, y: 9, x2: 55, strokeWidth: 1.2, dash: "5,5" },
  { x1: 10, y: 14, x2: 50, strokeWidth: 1.5, dash: "7,3" },
  { x1: 7, y: 19, x2: 53, strokeWidth: 1.3, dash: "4,5" },
  { x1: 9, y: 24, x2: 48, strokeWidth: 1.4, dash: "6,4" },
  { x1: 6, y: 29, x2: 54, strokeWidth: 1.2, dash: "5,4" },
  { x1: 11, y: 34, x2: 49, strokeWidth: 1.5, dash: "7,3" },
  { x1: 8, y: 39, x2: 52, strokeWidth: 1.3, dash: "4,6" },
]

const belowDividerTexture: DashedLine[] = [
  { x1: 5, y: 4, x2: 58, strokeWidth: 1.5, dash: "5,5" },
  { x1: 8, y: 9, x2: 55, strokeWidth: 1.3, dash: "6,4" },
  { x1: 3, y: 14, x2: 60, strokeWidth: 1.5, dash: "4,5" },
  { x1: 7, y: 19, x2: 56, strokeWidth: 1.2, dash: "7,3" },
  { x1: 4, y: 24, x2: 59, strokeWidth: 1.4, dash: "5,4" },
  { x1: 9, y: 29, x2: 53, strokeWidth: 1.3, dash: "6,5" },
  { x1: 6, y: 34, x2: 57, strokeWidth: 1.5, dash: "4,4" },
  { x1: 5, y: 39, x2: 58, strokeWidth: 1.2, dash: "7,4" },
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
