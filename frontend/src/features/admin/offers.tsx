import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { RefreshCw, Plus, Search } from 'lucide-react'
import { api, showError } from '@/lib/api'
import type { Paginated, OfferOut } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { StatusBadge } from '@/components/shared/status-badge'
import { CvxBadge } from '@/components/shared/cvx-badge'
import { Pagination } from '@/components/shared/pagination'
import { ErrorState } from '@/components/shared/error-state'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table'
import { Switch } from '@/components/ui/switch'
import { categoryLabels } from '@/lib/labels'
import { formatCompact } from '@/lib/utils'

export function AdminOffersPage() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  const params = new URLSearchParams({ page: String(page), page_size: '25' })
  if (search) params.set('search', search)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'offers', { search, page }],
    queryFn: () => api.get<Paginated<OfferOut>>(`/admin/offers?${params.toString()}`),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.patch(`/admin/offers/${id}`, { status: enabled ? 'active' : 'paused' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'offers'] })
    },
    onError: (err) => showError(err),
  })

  const syncMutation = useMutation({
    mutationFn: () => api.post('/admin/providers/sync'),
    onSuccess: () => {
      toast.success('Offer sync started')
      qc.invalidateQueries({ queryKey: ['admin', 'offers'] })
    },
    onError: (err) => showError(err),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-6">
      <PageHeader
        title="Offers & Tasks"
        description="Manage offer feed, rewards, and availability"
        actions={
          <Button onClick={() => syncMutation.mutate()} loading={syncMutation.isPending}>
            <RefreshCw className="h-4 w-4" /> Sync offers
          </Button>
        }
      />

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          placeholder="Search offers…"
          className="pl-9"
        />
      </div>

      <div className="rounded-xl surface">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Offer</TableHead>
              <TableHead>Provider</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Reward</TableHead>
              <TableHead>Payout</TableHead>
              <TableHead>Conv.</TableHead>
              <TableHead>Approval</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Enabled</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 9 }).map((__, j) => (
                    <TableCell key={j}><div className="h-4 animate-pulse rounded bg-muted" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : !data || data.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="py-10 text-center text-muted-foreground">No offers found.</TableCell>
              </TableRow>
            ) : (
              data.items.map((o) => (
                <TableRow key={o.id}>
                  <TableCell>
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-md bg-muted text-sm font-bold text-muted-foreground">
                        {o.icon_url ? <img src={o.icon_url} alt="" className="h-full w-full object-cover" /> : o.title.charAt(0)}
                      </div>
                      <div>
                        <div className="font-medium">{o.title}</div>
                        <div className="text-xs text-muted-foreground">{o.provider_name}</div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-xs">{o.provider_code}</TableCell>
                  <TableCell className="text-xs capitalize">{categoryLabels[o.category] || o.category}</TableCell>
                  <TableCell><CvxBadge value={o.effective_reward} /></TableCell>
                  <TableCell className="tabular text-muted-foreground">₹{o.reward?.toFixed(2)}</TableCell>
                  <TableCell className="tabular text-muted-foreground">{Math.round((o.conversion_rate || 0) * 100)}%</TableCell>
                  <TableCell className="tabular text-muted-foreground">{Math.round((o.approval_rate || 0) * 100)}%</TableCell>
                  <TableCell><StatusBadge status={o.status} /></TableCell>
                  <TableCell className="text-right">
                    <Switch
                      checked={o.status === 'active'}
                      onCheckedChange={(checked) => toggleMutation.mutate({ id: o.id, enabled: checked })}
                    />
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
