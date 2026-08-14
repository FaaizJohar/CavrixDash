import { useQuery } from '@tanstack/react-query'
import { TrendingUp, Coins, CheckCircle2, Clock } from 'lucide-react'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/shared/page-header'
import { MetricCard } from '@/components/shared/metric-card'
import { GlassCard } from '@/components/shared/glass-card'
import { ErrorState } from '@/components/shared/error-state'
import { RevenueAreaChart } from '@/components/dashboard/charts'
import { formatCvx, formatNumber } from '@/lib/utils'

interface UserAnalytics {
  totals: {
    tasks_completed: number
    conversions_approved: number
    conversions_pending: number
    cvx_earned: number
    cvx_spent: number
  }
  earning_history: Array<{ label: string; value: number }>
  conversion_history: Array<{ label: string; value: number }>
}

export function AnalyticsPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['user-analytics'],
    queryFn: () => api.get<UserAnalytics>('/analytics/overview'),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  const totals = data?.totals
  const history = (data?.earning_history || []).map((d) => ({ label: d.label, value: d.value }))

  return (
    <div className="space-y-6">
      <PageHeader title="Analytics" description="Your earning and activity over time" />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <MetricCard label="Tasks Completed" value={totals?.tasks_completed ?? null} icon={TrendingUp} loading={isLoading} />
        <MetricCard label="Approved" value={totals?.conversions_approved ?? null} icon={CheckCircle2} iconClassName="bg-emerald-400/10 text-emerald-300" loading={isLoading} />
        <MetricCard label="Pending" value={totals?.conversions_pending ?? null} icon={Clock} iconClassName="bg-amber-400/10 text-amber-300" loading={isLoading} />
        <MetricCard label="CVX Earned" value={totals ? formatCvx(totals.cvx_earned) : '—'} icon={Coins} iconClassName="bg-amber-400/10 text-amber-300" loading={isLoading} />
        <MetricCard label="CVX Spent" value={totals ? formatCvx(totals.cvx_spent) : '—'} icon={TrendingUp} loading={isLoading} />
      </div>

      <GlassCard className="p-5">
        <h3 className="mb-4 text-sm font-semibold">CVX earned over time</h3>
        {isLoading ? (
          <div className="h-60 animate-pulse rounded-lg bg-muted" />
        ) : history.length ? (
          <RevenueAreaChart data={history} formatter={(v) => formatNumber(v)} height={260} />
        ) : (
          <div className="py-10 text-center text-sm text-muted-foreground">
            Not enough data yet. Start earning to see trends.
          </div>
        )}
      </GlassCard>
    </div>
  )
}
