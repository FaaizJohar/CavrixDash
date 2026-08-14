import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Kpi } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { MetricCard } from '@/components/shared/metric-card'
import { ErrorState } from '@/components/shared/error-state'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function AdminAnalyticsPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'overview'],
    queryFn: () => api.get<{ kpis: Kpi[] }>('/admin/kpis'),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  const kpis = data?.kpis || []

  const sectionKeys = [
    'total_revenue', 'today_revenue', 'pending_revenue',
    'users', 'active_users', 'active_servers',
    'tasks_completed', 'approved', 'rejected',
    'cvx_issued', 'cvx_spent', 'cvx_outstanding',
  ]
  const kpiMap = Object.fromEntries(kpis.map((k) => [k.key, k]))
  const sections: Array<{ title: string; keys: string[] }> = [
    { title: 'Revenue', keys: ['total_revenue', 'today_revenue', 'pending_revenue'] },
    { title: 'Users', keys: ['users', 'active_users'] },
    { title: 'Servers', keys: ['active_servers'] },
    { title: 'Tasks & CVX', keys: ['tasks_completed', 'approved', 'rejected', 'cvx_issued', 'cvx_spent', 'cvx_outstanding'] },
  ]

  return (
    <div className="space-y-6">
      <PageHeader title="Analytics" description="Platform-wide performance metrics" />

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-xl bg-muted" />)}
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {kpis.map((k) => (
              <MetricCard key={k.key} label={k.label} value={fmt(k.value)} />
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {sections.map((s) => {
              const metrics = s.keys.filter((key) => kpiMap[key]).map((key) => ({ key, label: labelOf(key), value: kpiMap[key].value }))
              return (
                <Card key={s.title}>
                  <CardHeader><CardTitle className="text-base">{s.title}</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    {metrics.map((m) => (
                      <div key={m.key} className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">{m.label}</span>
                        <span className="text-sm font-semibold tabular">{fmt(m.value)}</span>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )
            })}
          </div>

          <div className="flex justify-end">
            <Button variant="outline" size="sm" onClick={() => refetch()}>Refresh</Button>
          </div>
        </>
      )}
    </div>
  )
}

function labelOf(key: string): string {
  const map: Record<string, string> = {
    total_revenue: 'Total revenue',
    today_revenue: 'Today',
    pending_revenue: 'Pending payout',
    users: 'Registered users',
    active_users: 'Active users',
    active_servers: 'Active servers',
    tasks_completed: 'Tasks completed',
    approved: 'Conversions approved',
    rejected: 'Conversions rejected',
    cvx_issued: 'CVX issued',
    cvx_spent: 'CVX spent',
    cvx_outstanding: 'CVX outstanding',
  }
  return map[key] || key.replace(/_/g, ' ')
}

function fmt(value: unknown): string {
  if (typeof value === 'number') return value.toLocaleString('en-IN')
  return String(value ?? '—')
}
