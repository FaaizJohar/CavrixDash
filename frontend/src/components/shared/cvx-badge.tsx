import { Coins } from 'lucide-react'
import { formatNumber } from '@/lib/utils'
import { cn } from '@/lib/utils'

interface CvxBadgeProps {
  value: number
  symbol?: string
  className?: string
  iconClassName?: string
}

export function CvxBadge({ value, symbol = 'CVX', className, iconClassName }: CvxBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border border-amber-400/25 bg-amber-400/10 px-2.5 py-0.5 text-xs font-semibold text-amber-300',
        className,
      )}
    >
      <Coins className={cn('h-3.5 w-3.5', iconClassName)} />
      {formatNumber(value)}
      <span className="text-amber-400/70">{symbol}</span>
    </span>
  )
}
