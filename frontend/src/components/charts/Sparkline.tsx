// Tiny inline position sparkline (44x16 rendered, 40x16 viewBox), colored by
// gain/loss direction, wobbled by the sketchy filter — exact per reference.
export function Sparkline({ path, positive }: { path: string; positive: boolean }) {
  return (
    <svg width={44} height={16} viewBox="0 0 40 16" className="ml-2 shrink-0">
      <path
        d={path}
        fill="none"
        stroke={positive ? "var(--color-positive)" : "var(--color-negative)"}
        strokeWidth={2}
        strokeLinecap="round"
        style={{ filter: "url(#sketchy)" }}
      />
    </svg>
  )
}
