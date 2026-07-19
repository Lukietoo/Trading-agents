import { cn } from "@/lib/utils"
import type { CSSProperties, ReactNode } from "react"

// Cream card/panel with sketchy border. `delay` staggers the fadeUp
// load animation (seconds), per the exact delays in the design reference.
export function SketchCard({
  children,
  className,
  delay,
}: {
  children: ReactNode
  className?: string
  delay?: number
}) {
  const style: CSSProperties | undefined =
    delay !== undefined ? { animationDelay: `${delay}s` } : undefined
  return (
    <div
      className={cn("sketch-card p-6", delay !== undefined && "fade-up", className)}
      style={style}
    >
      {children}
    </div>
  )
}

export function DashedDivider({ className }: { className?: string }) {
  return <div className={cn("border-b-[1.5px] border-dashed border-divider", className)} />
}

// List rows with dashed dividers between them (none after the last row).
export function DividedList<T>({
  items,
  itemKey,
  renderItem,
}: {
  items: readonly T[]
  itemKey: (item: T) => string
  renderItem: (item: T) => ReactNode
}) {
  return (
    <>
      {items.map((item, i) => (
        <div key={itemKey(item)}>
          {renderItem(item)}
          {i < items.length - 1 && <DashedDivider />}
        </div>
      ))}
    </>
  )
}

const badgeColors = {
  blue: "bg-badge-blue",
  green: "bg-badge-green",
  purple: "bg-badge-purple",
  yellow: "bg-badge-yellow",
} as const

// Circular pastel icon badge (48px stat cards, 36px activity, 28px trades).
export function IconBadge({
  color,
  size,
  children,
}: {
  color: keyof typeof badgeColors
  size: number
  children: ReactNode
}) {
  return (
    <div
      className={cn("flex shrink-0 items-center justify-center rounded-full", badgeColors[color])}
      style={{ width: size, height: size }}
    >
      {children}
    </div>
  )
}
