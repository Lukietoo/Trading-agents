"use client"

import * as React from "react"
import { Switch as SwitchPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"

// Sketch-styled toggle per design-reference: 44x24 pill, 2px ink border,
// green (#3E9B6B) on / gray (#e0e2e6) off, 18px white knob with 1.5px ink border.
function Switch({
  className,
  ...props
}: React.ComponentProps<typeof SwitchPrimitive.Root>) {
  return (
    <SwitchPrimitive.Root
      data-slot="switch"
      className={cn(
        "peer sketchy-filter relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-xl border-2 border-ink transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent-blue/50 data-checked:bg-positive data-unchecked:bg-toggle-off",
        className
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb
        data-slot="switch-thumb"
        className="pointer-events-none block size-[18px] rounded-full border-[1.5px] border-ink bg-white transition-transform data-checked:translate-x-[21px] data-unchecked:translate-x-[1px]"
      />
    </SwitchPrimitive.Root>
  )
}

export { Switch }
