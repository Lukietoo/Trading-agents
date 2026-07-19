// Inline SVG icons, exact from the design reference. Stroke-only line art;
// stroke-width 1.8 for stat-card icons, 2.2/1.8 for activity icons,
// 2.5 for the small recent-trade arrows, 1.6 for export menu icons.
// Icons never receive the sketchy filter.

export function WalletIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#1A1A1A" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="6" width="18" height="13" rx="2" />
      <path d="M6 6V4a5 5 0 0 1 10 0v2" />
      <circle cx="11" cy="13" r="2" />
    </svg>
  )
}

export function CashIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#1A1A1A" strokeWidth="1.8" strokeLinecap="round">
      <circle cx="11" cy="11" r="8" />
      <path d="M11 6v10M8 9h6M8 13h6" />
    </svg>
  )
}

export function TrendIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#1A1A1A" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3,16 8,10 12,13 19,5" />
      <polyline points="14,5 19,5 19,10" />
    </svg>
  )
}

export function ClockIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#1A1A1A" strokeWidth="1.8" strokeLinecap="round">
      <circle cx="11" cy="11" r="8" />
      <path d="M11 7v4l3 2" />
    </svg>
  )
}

export function ArrowUpIcon({ size, strokeWidth }: { size: number; strokeWidth: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="#3E9B6B" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 13V3" />
      <path d="M3 8l5-5 5 5" />
    </svg>
  )
}

export function ArrowDownIcon({ size, strokeWidth }: { size: number; strokeWidth: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="#D9695E" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 3v10" />
      <path d="M3 8l5 5 5-5" />
    </svg>
  )
}

export function DividendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#8B5CF6" strokeWidth="1.8" strokeLinecap="round">
      <circle cx="8" cy="8" r="6" />
      <path d="M8 5v6" />
      <path d="M5.5 8h5" />
    </svg>
  )
}

export function DownloadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#1A1A1A" strokeWidth="2" strokeLinecap="round">
      <path d="M8 2v8M4 7l4 4 4-4M2 13h12" />
    </svg>
  )
}

export function CsvIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#1A1A1A" strokeWidth="1.6" strokeLinecap="round">
      <path d="M2 2h12v12H2z" />
      <path d="M5 1v3M11 1v3M2 6h12" />
    </svg>
  )
}

export function PdfIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#1A1A1A" strokeWidth="1.6" strokeLinecap="round">
      <rect x="2" y="2" width="12" height="12" rx="1" />
      <path d="M5 6h6M5 9h4" />
    </svg>
  )
}

export function ScheduleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#1A1A1A" strokeWidth="1.6" strokeLinecap="round">
      <circle cx="8" cy="8" r="6" />
      <path d="M8 5v3l2 1.5" />
    </svg>
  )
}

export function ShareIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#1A1A1A" strokeWidth="1.6" strokeLinecap="round">
      <path d="M6 2H3a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-3" />
      <path d="M9 2h5v5" />
      <path d="M14 2L7 9" />
    </svg>
  )
}

export function ChevronDownIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="#6B7280" strokeWidth="2" strokeLinecap="round">
      <path d="M3 5l3 3 3-3" />
    </svg>
  )
}
