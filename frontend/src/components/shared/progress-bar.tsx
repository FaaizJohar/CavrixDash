import { cn } from '@/lib/utils'

interface ProgressBarProps {
  value: number
  max?: number
  className?: string
  indicatorClassName?: string
  showLabel?: boolean
  label?: string
}

export function ProgressBar({
  value,
  max = 100,
  className,
  indicatorClassName,
  showLabel = false,
  label,
}: ProgressBarProps) {
  const pct = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0
  return (
    <div className="w-full">
      <div className={cn('relative h-2 w-full overflow-hidden rounded-full bg-muted', className)}>
        <div
          className={cn(
            'h-full rounded-full bg-gradient-to-r from-cavrix-500 to-cyan-400 transition-all duration-500',
            indicatorClassName,
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <div className="mt-1 flex justify-between text-xs text-muted-foreground">
          <span>{label}</span>
          <span className="tabular">{Math.round(pct)}%</span>
        </div>
      )}
    </div>
  )
}
