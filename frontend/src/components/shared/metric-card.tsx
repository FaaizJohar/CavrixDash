import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'

interface MetricCardProps {
  label: string
  value: React.ReactNode
  sub?: React.ReactNode
  icon?: LucideIcon
  iconClassName?: string
  loading?: boolean
  className?: string
}

export function MetricCard({
  label,
  value,
  sub,
  icon: Icon,
  iconClassName,
  loading,
  className,
}: MetricCardProps) {
  return (
    <div className={cn('rounded-xl surface p-4 flex flex-col gap-2', className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</span>
        {Icon && (
          <div
            className={cn(
              'flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary',
              iconClassName,
            )}
          >
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      {loading ? (
        <Skeleton className="h-7 w-24" />
      ) : (
        <div className="text-2xl font-semibold tabular tracking-tight">{value}</div>
      )}
      {sub && <div className="text-xs text-muted-foreground">{sub}</div>}
    </div>
  )
}
