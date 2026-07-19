import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Semantic gain/loss color per CONTEXT.md: positive green, negative coral.
export function gainLossClass(positive: boolean) {
  return positive ? "text-positive" : "text-negative"
}
