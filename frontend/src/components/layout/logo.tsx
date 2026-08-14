export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cavrix-500 to-cyan-500 shadow-soft">
        <svg viewBox="0 0 24 24" className="h-5 w-5 text-white" fill="none">
          <path d="M5 7l7 4 7-4M5 13l7 4 7-4" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="12" cy="12" r="1.8" fill="currentColor" />
        </svg>
      </div>
      {!compact && (
        <div className="leading-none">
          <div className="text-sm font-bold tracking-tight">Cavrix<span className="text-gradient"> Cloud</span></div>
          <div className="text-[10px] text-muted-foreground">Earn. Build. Play.</div>
        </div>
      )}
    </div>
  )
}
