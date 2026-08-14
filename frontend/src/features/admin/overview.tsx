import { useQuery } from '@tanstack/react-query'
import {
  IndianRupee,
  Users,
  Server,
  CheckCircle2,
  XCircle,
  Coins,
  ShieldAlert,
} from 'lucide-react'
import { api } from '@/lib/api'
import type { AdminOverview } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { MetricCard } from '@/components/shared/metric-card'
import { GlassCard } from '@/components/shared/glass-card'
import { ErrorState } from '@/components/shared/error-state'
import { RevenueBarChart } from '@/components/dashboard/charts'
import { formatCurrency, formatCompact, formatCvx } from '@/lib/utils'

export function AdminOverviewPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'overview'],
    queryFn: () => api.get<AdminOverview>('/admin/overview'),
    refetchInterval: 60_000,
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  const revenue7d = (data?.revenue_7d || []).map((d) => ({
    label: String(d.label || ''),
    revenue: Number(d.revenue || 0),
    cost: Number(d.cost || 0),
  }))

  return (
    <div className="space-y-6">
      <PageHeader title="Overview" description="Platform health at a glance" />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="Total Revenue" value={data ? formatCurrency(data.total_revenue) : '—'} icon={IndianRupee} iconClassName="bg-emerald-400/10 text-emerald-300" loading={isLoading} />
        <MetricCard label="Today" value={data ? formatCurrency(data.today_revenue) : '—'} icon={IndianRupee} iconClassName="bg-cyan-400/10 text-cyan-300" loading={isLoading} />
        <MetricCard label="Pending Revenue" value={data ? formatCurrency(data.pending_revenue) : '—'} icon={Coins} iconClassName="bg-amber-400/10 text-amber-300" loading={isLoading} />
        <MetricCard label="Risk Events (24h)" value={data?.risk_events_24h ?? null} icon={ShieldAlert} iconClassName="bg-red-400/10 text-red-300" loading={isLoading} />
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="Users" value={data ? formatCompact(data.users) : '—'} icon={Users} loading={isLoading} />
        <MetricCard label="Active Users" value={data ? formatCompact(data.active_users) : '—'} icon={Users} iconClassName="bg-emerald-400/10 text-emerald-300" loading={isLoading} />
        <MetricCard label="Active Servers" value={data ? formatCompact(data.active_servers) : '—'} icon={Server} iconClassName="bg-violet-400/10 text-violet-300" loading={isLoading} />
        <MetricCard label="Tasks Completed" value={data ? formatCompact(data.tasks_completed) : '—'} icon={CheckCircle2} loading={isLoading} />
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="Approved" value={data ? formatCompact(data.approved) : '—'} icon={CheckCircle2} iconClassName="bg-emerald-400/10 text-emerald-300" loading={isLoading} />
        <MetricCard label="Rejected" value={data ? formatCompact(data.rejected) : '—'} icon={XCircle} iconClassName="bg-red-400/10 text-red-300" loading={isLoading} />
        <MetricCard label="CVX Issued" value={data ? formatCvx(data.cvx_issued) : '—'} icon={Coins} iconClassName="bg-amber-400/10 text-amber-300" loading={isLoading} />
        <MetricCard label="CVX Outstanding" value={data ? formatCvx(data.cvx_outstanding) : '—'} icon={Coins} loading={isLoading} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <GlassCard className="p-5 lg:col-span-2">
          <h3 className="mb-4 text-sm font-semibold">Revenue · last 7 days</h3>
          {isLoading ? (
            <div className="h-64 animate-pulse rounded-lg bg-muted" />
          ) : revenue7d.length ? (
            <RevenueBarChart data={revenue7d} formatter={(v) => formatCurrency(v)} />
          ) : (
            <div className="py-12 text-center text-sm text-muted-foreground">No revenue data yet.</div>
          )}
        </GlassCard>

        <GlassCard className="p-5">
          <h3 className="mb-4 text-sm font-semibold">Revenue by provider</h3>
          {(data?.provider_revenue || []).length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">No provider revenue yet.</div>
          ) : (
            <div className="space-y-3">
              {(data?.provider_revenue || []).map((p) => {
                const row = p as { name: string; revenue: number; conversions: number }
                return (
                  <div key={row.name} className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">{row.name}</div>
                      <div className="text-xs text-muted-foreground">{row.conversions} conversions</div>
                    </div>
                    <div className="text-sm font-semibold tabular">{formatCurrency(row.revenue)}</div>
                  </div>
                )
              })}
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  )
}
