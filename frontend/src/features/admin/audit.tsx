import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ScrollText } from 'lucide-react'
import { api } from '@/lib/api'
import type { Paginated, AuditRow } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { ErrorState } from '@/components/shared/error-state'
import { Pagination } from '@/components/shared/pagination'
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { formatRelative } from '@/lib/utils'

export function AdminAuditPage() {
  const [page, setPage] = useState(1)
  const [category, setCategory] = useState('')
  const [query, setQuery] = useState('')
  const [debounced, setDebounced] = useState('')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'audit', page, category, debounced],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: '25' })
      if (category) params.set('category', category)
      if (debounced) params.set('q', debounced)
      return api.get<Paginated<AuditRow>>(`/admin/audit?${params}`)
    },
  })

  const categories = ['user', 'auth', 'cvx', 'server', 'offer', 'admin', 'support', 'security']

  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-4">
      <PageHeader title="Audit Log" description="Every sensitive action across the platform, with actor and IP" />

      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="max-w-xs"
          placeholder="Search actor / target…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            window.setTimeout(() => setDebounced(e.target.value), 400)
          }}
        />
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={category}
          onChange={(e) => { setCategory(e.target.value); setPage(1) }}
        >
          <option value="">All categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="rounded-xl surface">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Action</TableHead>
              <TableHead>Actor</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Target</TableHead>
              <TableHead>Change</TableHead>
              <TableHead>IP</TableHead>
              <TableHead>Result</TableHead>
              <TableHead>When</TableHead>
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
              <TableRow><TableCell colSpan={8} className="py-10 text-center text-muted-foreground">No audit entries found.</TableCell></TableRow>
            ) : (
              data.items.map((a) => (
                <TableRow key={a.id}>
                  <TableCell>
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <ScrollText className="h-4 w-4 text-muted-foreground" />
                      {a.action}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs">{a.actor_name || 'system'}</TableCell>
                  <TableCell><span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{a.category}</span></TableCell>
                  <TableCell className="font-mono text-[11px] text-muted-foreground">
                    {a.target_type}{a.target_id ? `:${a.target_id.slice(0, 8)}` : ''}
                  </TableCell>
                  <TableCell className="max-w-[200px]">
                    <div className="truncate text-xs text-muted-foreground">
                      {a.old_value && <span className="text-rose-300/80 line-through">{a.old_value}</span>}
                      {a.old_value && a.new_value && <span className="mx-1">→</span>}
                      {a.new_value && <span className="text-emerald-300/90">{a.new_value}</span>}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-[11px] text-muted-foreground">{a.ip || '—'}</TableCell>
                  <TableCell>
                    <span className={`status-dot ${a.result === 'success' ? 'bg-emerald-400' : a.result === 'failure' ? 'bg-rose-400' : 'bg-muted'}`} />
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{formatRelative(a.created_at || '')}</TableCell>
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
