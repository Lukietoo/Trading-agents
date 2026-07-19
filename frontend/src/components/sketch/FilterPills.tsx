import { cn } from "@/lib/utils"

// Small sketchy filter pills (All/Winners/Losers etc.). Separate rounded
// buttons with 8px gap; active pill is pastel blue and semibold.
export function FilterPills<T extends string>({
  options,
  active,
  onChange,
}: {
  options: readonly T[]
  active: T
  onChange: (value: T) => void
}) {
  return (
    <div className="flex gap-2">
      {options.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={cn(
            "sketchy-filter cursor-pointer rounded-md border-2 border-ink px-3.5 py-1.5 font-sans text-[13px] text-ink outline-none focus-visible:ring-2 focus-visible:ring-accent-blue/50",
            option === active
              ? "bg-active-tint font-semibold"
              : "bg-btn font-medium hover:bg-hover-tint"
          )}
        >
          {option}
        </button>
      ))}
    </div>
  )
}

// Joined segmented control (1M/3M/1Y): shared borders, outer corners rounded.
export function SegmentedControl<T extends string>({
  options,
  active,
  onChange,
  size = "sm",
}: {
  options: readonly T[]
  active: T
  onChange: (value: T) => void
  size?: "sm" | "md"
}) {
  return (
    <div className="flex">
      {options.map((option, i) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={cn(
            "sketchy-filter cursor-pointer border-2 border-ink font-sans text-[13px] text-ink outline-none focus-visible:ring-2 focus-visible:ring-accent-blue/50",
            size === "sm" ? "px-3.5 py-1.5" : "px-4 py-2",
            i === 0 && "rounded-l-md",
            i > 0 && "border-l-0",
            i === options.length - 1 && "rounded-r-md",
            option === active ? "bg-active-tint font-semibold" : "bg-btn font-medium hover:bg-hover-tint"
          )}
        >
          {option}
        </button>
      ))}
    </div>
  )
}
