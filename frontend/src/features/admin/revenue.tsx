import { useQuery } from '@tanstack/react-query'
import { IndianRupee } from 'lucide-react'
import { api } from '@/lib/api'
import type { Paginated, ProviderOut, Kpi } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { MetricCard } from '@/components/shared/metric-card'
import { ErrorState } from '@/components/shared/error-state'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table'
import { formatCurrency, formatRelative } from '@/lib/utils'

interface RevenueBreakdown {
  total: number
  today: number
  pending: number
  paid: number
  by_provider: Array<Record<string, unknown>>
  by_day: Array<Record<string, unknown>>
  payouts: Array<{
    id: string
    user_id: string
    amount: number
    status: string
    method: string
    ref: string
    created_at?: string | null
  }>
}

export function AdminRevenuePage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'revenue'],
    queryFn: () => api.get<RevenueBreakdown>('/admin/revenue'),
  })

  const kpisQ = useQuery({
    queryKey: ['admin', 'overview'],
    queryFn: () => api.get<{ kpis: Kpi[] }>('/admin/overview'),
  })

  const providersQ = useQuery({
    queryKey: ['admin', 'providers'],
    queryFn: () => api.get<Paginated<ProviderOut>>('/admin/providers?page=1&page_size=100'),
  })

  if (error || kpisQ.error) {
    return <ErrorState onRetry={() => { refetch(); kpisQ.refetch() }} />
  }

  const kpis = kpisQ.data?.kpis || []
  const revenueKpis = kpis.filter((k) => /revenue/i.test(k.label)).slice(0, 4)
  const providers = providersQ.data?.items || []

  return (
    <div className="space-y-6">
      <PageHeader title="Revenue" description="Offer earnings, pending payouts, and provider breakdown" />

      {revenueKpis.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {revenueKpis.map((k) => (
            <MetricCard key={k.key} label={k.label} value={formatCurrency(Number(k.value) || 0)} />
          ))}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Total revenue" value={formatCurrency(data?.total || 0)} />
          <MetricCard label="Today" value={formatCurrency(data?.today || 0)} />
          <MetricCard label="Pending payout" value={formatCurrency(data?.pending || 0)} />
          <MetricCard label="Paid out" value={formatCurrency(data?.paid || 0)} />
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>By provider</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {providers.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">No provider data.</div>
            ) : (
              providers.map((p) => {
                const row = data?.by_provider?.find((r) => (r as Record<string, unknown>).provider === p.code) as Record<string, unknown> | undefined
                const amount = Number((row?.revenue as number) ?? p.revenue_tracked ?? 0)
                return (
                  <div key={p.id} className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">{p.name}</div>
                      <div className="text-xs text-muted-foreground">{p.code} · {p.kind}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                        {Math.round(p.reliability * 100)}% reliability
                      </span>
                      <span className="text-sm font-semibold tabular">{formatCurrency(amount)}</span>
                    </div>
                  </div>
                )
              })
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Payout requests</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ref</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {!data || data.payouts.length === 0 ? (
                  <TableRow><TableCell colSpan={6} className="py-8 text-center text-muted-foreground">No payouts yet.</TableCell></TableRow>
                ) : (
                  data.payouts.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="font-mono text-xs">{p.ref}</TableCell>
                      <TableCell className="font-mono text-xs">{p.user_id.slice(0, 8)}</TableCell>
                      <TableCell className="tabular">{formatCurrency(p.amount)}</TableCell>
                      <TableCell className="text-xs">{p.method}</TableCell>
                      <TableCell>
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                          p.status === 'paid' ? 'bg-emerald-400/10 text-emerald-300' :
                          p.status === 'pending' ? 'bg-amber-400/10 text-amber-300' :
                          p.status === 'rejected' ? 'bg-rose-400/10 text-rose-300' : 'bg-muted text-muted-foreground'
                        }`}>{p.status}</span>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">{formatRelative(p.created_at || '')}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
