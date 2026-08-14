import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api, showError } from '@/lib/api'
import type { Paginated, TicketOut } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { ErrorState } from '@/components/shared/error-state'
import { StatusBadge } from '@/components/shared/status-badge'
import { Pagination } from '@/components/shared/pagination'
import { Button } from '@/components/ui/button'
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table'
import { formatRelative } from '@/lib/utils'

export function AdminSupportPage() {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState('open')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'support', filter, page],
    queryFn: () => api.get<Paginated<TicketOut>>(`/admin/support?status=${filter}&page=${page}&page_size=25`),
  })

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { status?: string; priority?: string; assignee_id?: string } }) =>
      api.patch(`/admin/support/${id}`, payload),
    onSuccess: () => {
      toast.success('Ticket updated')
      qc.invalidateQueries({ queryKey: ['admin', 'support'] })
    },
    onError: (err) => showError(err),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  const tabs = [
    { key: 'open', label: 'Open' },
    { key: 'pending', label: 'Pending' },
    { key: 'resolved', label: 'Resolved' },
    { key: 'closed', label: 'Closed' },
  ]

  return (
    <div className="space-y-4">
      <PageHeader title="Support Queue" description="Manage user tickets" />

      <div className="flex gap-2">
        {tabs.map((t) => (
          <Button
            key={t.key}
            variant={filter === t.key ? 'default' : 'ghost'}
            size="sm"
            className="h-8"
            onClick={() => { setFilter(t.key); setPage(1) }}
          >
            {t.label}
          </Button>
        ))}
      </div>

      <div className="rounded-xl surface">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ticket</TableHead>
              <TableHead>Last message</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Updated</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 7 }).map((__, j) => (
                    <TableCell key={j}><div className="h-4 animate-pulse rounded bg-muted" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : !data || data.items.length === 0 ? (
              <TableRow><TableCell colSpan={7} className="py-10 text-center text-muted-foreground">No {filter} tickets.</TableCell></TableRow>
            ) : (
              data.items.map((t) => (
                <TableRow key={t.id}>
                  <TableCell>
                    <div className="max-w-[240px] truncate text-sm font-medium">{t.subject}</div>
                    <div className="font-mono text-[10px] text-muted-foreground">{t.id.slice(0, 8)}</div>
                  </TableCell>
                  <TableCell className="max-w-[220px] truncate text-xs text-muted-foreground">{t.last_message}</TableCell>
                  <TableCell className="text-xs">{t.category}</TableCell>
                  <TableCell>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      t.priority === 'urgent' || t.priority === 'high' ? 'bg-rose-400/10 text-rose-300' :
                      t.priority === 'medium' ? 'bg-amber-400/10 text-amber-300' : 'bg-muted text-muted-foreground'
                    }`}>{t.priority}</span>
                  </TableCell>
                  <TableCell><StatusBadge status={t.status} /></TableCell>
                  <TableCell className="text-xs text-muted-foreground">{formatRelative(t.updated_at || t.created_at || '')}</TableCell>
                  <TableCell className="text-right">
                    {t.status === 'open' ? (
                      <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => update.mutate({ id: t.id, payload: { status: 'pending' } })}>
                        Claim
                      </Button>
                    ) : t.status === 'pending' ? (
                      <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => update.mutate({ id: t.id, payload: { status: 'resolved' } })}>
                        Resolve
                      </Button>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onChange={setPage} />}
    </div>
  )
}
