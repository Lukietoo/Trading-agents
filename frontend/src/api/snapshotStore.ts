// Shared snapshot store: one poller feeding every hook that reads the
// snapshot, so the summary cards, positions views, and allocation bar share
// a single fetch cycle (60s interval + refetch on tab focus).

import { useSyncExternalStore } from "react"

import { fetchSnapshot, type Snapshot } from "@/api/snapshot"

const POLL_INTERVAL_MS = 60_000

let current: Snapshot | null = null
const listeners = new Set<() => void>()
let interval: ReturnType<typeof setInterval> | undefined

async function load() {
  try {
    current = await fetchSnapshot()
    listeners.forEach((notify) => notify())
  } catch {
    // Keep the last good snapshot (or null before the first success).
  }
}

const onFocus = () => load()
const onVisible = () => {
  if (document.visibilityState === "visible") load()
}

function subscribe(listener: () => void): () => void {
  if (listeners.size === 0) {
    load()
    interval = setInterval(load, POLL_INTERVAL_MS)
    window.addEventListener("focus", onFocus)
    document.addEventListener("visibilitychange", onVisible)
  }
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
    if (listeners.size === 0) {
      clearInterval(interval)
      window.removeEventListener("focus", onFocus)
      document.removeEventListener("visibilitychange", onVisible)
    }
  }
}

export function useSnapshot(): Snapshot | null {
  return useSyncExternalStore(subscribe, () => current)
}
