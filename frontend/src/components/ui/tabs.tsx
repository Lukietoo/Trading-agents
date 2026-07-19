import * as React from "react"
import { Tabs as TabsPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"

// Sketch-styled tabs per design-reference: cream buttons with 2.5px ink
// borders + offset shadow; active tab is pastel blue with no shadow.
function Tabs({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Root>) {
  return (
    <TabsPrimitive.Root
      data-slot="tabs"
      className={cn("flex flex-col", className)}
      {...props}
    />
  )
}

function TabsList({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      data-slot="tabs-list"
      className={cn("flex gap-2", className)}
      {...props}
    />
  )
}

function TabsTrigger({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      data-slot="tabs-trigger"
      className={cn(
        "sketchy-border-filter cursor-pointer rounded-lg border-[2.5px] border-ink px-6 py-3 font-sans text-base whitespace-nowrap text-ink outline-none focus-visible:ring-2 focus-visible:ring-accent-blue/50",
        "bg-btn font-medium shadow-[2px_3px_0px_rgba(0,0,0,0.08)] hover:bg-hover-tint",
        "data-active:bg-active-tint data-active:font-semibold data-active:shadow-none data-active:hover:bg-active-tint",
        className
      )}
      {...props}
    />
  )
}

function TabsContent({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content
      data-slot="tabs-content"
      className={cn("outline-none", className)}
      {...props}
    />
  )
}

export { Tabs, TabsList, TabsTrigger, TabsContent }
