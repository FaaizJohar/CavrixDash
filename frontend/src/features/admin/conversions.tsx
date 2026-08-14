import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api, showError } from '@/lib/api'
import type { ConversionOut, Paginated } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { StatusBadge } from '@/components/shared/status-badge'
import { Pagination } from '@/components/shared/pagination'
import { ErrorState } from '@/components/shared/error-state'
import { Button } from '@/components/ui/button'
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table'
import { formatCvx, formatDate } from '@/lib/utils'

export function AdminConversionsPage() {
  const qc = useQueryClient()
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)

  const params = new URLSearchParams({ page: String(page), page_size: '25' })
  if (status) params.set('status', status)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'conversions', { status, page }],
    queryFn: () => api.get<Paginated<ConversionOut>>(`/admin/conversions?${params.toString()}`),
  })

  const reviewMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.patch(`/admin/conversions/${id}`, { status, review_note: `Reviewed by admin → ${status}` }),
    onSuccess: () => {
      toast.success('Conversion updated')
      qc.invalidateQueries({ queryKey: ['admin', 'conversions'] })
    },
    onError: (err) => showError(err),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  const tabs = [
    { value: '', label: 'All' },
    { value: 'pending', label: 'Pending' },
    { value: 'approved', label: 'Approved' },
    { value: 'rejected', label: 'Rejected' },
    { value: 'held', label: 'Held' },
  ]

  return (
    <div className="space-y-6">
      <PageHeader title="Conversions" description="Review and manage conversion events" />

      <div className="flex flex-wrap gap-2">
        {tabs.map((t) => (
          <Button
            key={t.value}
            size="sm"
            variant={status === t.value ? 'default' : 'outline'}
            onClick={() => { setStatus(t.value); setPage(1) }}
          >
            {t.label}
          </Button>
        ))}
      </div>

      <div className="rounded-xl surface">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Offer</TableHead>
              <TableHead>Provider</TableHead>
              <TableHead>Conversion ID</TableHead>
              <TableHead>Reward</TableHead>
              <TableHead>Risk</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Date</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 8 }).map((__, j) => (
                    <TableCell key={j}><div className="h-4 animate-pulse rounded bg-muted" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : !data || data.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="py-10 text-center text-muted-foreground">No conversions found.</TableCell>
              </TableRow>
            ) : (
              data.items.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="max-w-[200px]">
                    <div className="truncate font-medium">{c.offer_title}</div>
                  </TableCell>
                  <TableCell className="text-xs">{c.provider_code}</TableCell>
                  <TableCell className="max-w-[140px] truncate font-mono text-xs text-muted-foreground">
                    {c.conversion_id}
                  </TableCell>
                  <TableCell className="tabular">{formatCvx(c.reward_amount)}</TableCell>
                  <TableCell className={`tabular ${c.risk_score >= 60 ? 'text-red-400' : c.risk_score >= 30 ? 'text-amber-400' : ''}`}>
                    {Math.round(c.risk_score)}
                  </TableCell>
                  <TableCell><StatusBadge status={c.status} /></TableCell>
                  <TableCell className="tabular text-muted-foreground">{formatDate(c.created_at || '')}</TableCell>
                  <TableCell className="text-right">
                    {(c.status === 'pending' || c.status === 'held') && (
                      <div className="flex justify-end gap-1.5">
                        <Button size="sm" variant="success" className="h-7 text-xs" onClick={() => reviewMutation.mutate({ id: c.id, status: 'approved' })}>
                          Approve
                        </Button>
                        <Button size="sm" variant="destructive" className="h-7 text-xs" onClick={() => reviewMutation.mutate({ id: c.id, status: 'rejected' })}>
                          Reject
                        </Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && (
        <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onChange={setPage} />
      )}
    </div>
  )
}
