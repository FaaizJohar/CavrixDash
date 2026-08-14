import { statusOf } from '@/lib/labels'
import { cn } from '@/lib/utils'

interface StatusBadgeProps {
  status: string
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const cfg = statusOf(status)
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
        cfg.className,
        className,
      )}
    >
      <span className={cn('status-dot', cfg.dot)} />
      {cfg.label}
    </span>
  )
}
