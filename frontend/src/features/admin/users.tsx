import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Search } from 'lucide-react'
import { api, showError } from '@/lib/api'
import type { AdminUserRow, Paginated } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { StatusBadge } from '@/components/shared/status-badge'
import { Pagination } from '@/components/shared/pagination'
import { ErrorState } from '@/components/shared/error-state'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { StepUpDialog, useStepUp } from '@/components/shared/step-up'
import { formatCvx, formatDate, formatCompact } from '@/lib/utils'

export function AdminUsersPage() {
  const qc = useQueryClient()
  const stepUp = useStepUp()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<AdminUserRow | null>(null)
  const [newStatus, setNewStatus] = useState('')
  const [adjustment, setAdjustment] = useState('')
  const [adjustReason, setAdjustReason] = useState('')
  const [saving, setSaving] = useState(false)

  const params = new URLSearchParams({ page: String(page), page_size: '25' })
  if (search) params.set('search', search)
  if (status) params.set('status', status)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'users', { search, status, page }],
    queryFn: () => api.get<Paginated<AdminUserRow>>(`/admin/users?${params.toString()}`),
    placeholderData: (prev) => prev,
  })

  const doUpdate = async (body: Record<string, unknown>, token?: string) => {
    setSaving(true)
    try {
      const opts = token ? { headers: { 'X-Step-Up-Token': token } as Record<string, string> } : undefined
      await api.patch(`/admin/users/${selected!.id}`, body, opts)
      toast.success('User updated')
      qc.invalidateQueries({ queryKey: ['admin', 'users'] })
      setSelected(null)
      setAdjustment('')
      setAdjustReason('')
    } finally {
      setSaving(false)
    }
  }

  const openDialog = (u: AdminUserRow) => {
    setSelected(u)
    setNewStatus(u.status)
  }

  const apply = () => {
    const body: Record<string, unknown> = {}
    if (newStatus !== selected!.status) body.status = newStatus
    const hasAdjustment = !!adjustment && Number(adjustment) !== 0
    if (hasAdjustment) {
      body.cvx_adjustment = Number(adjustment)
      body.cvx_adjustment_reason = adjustReason || 'Admin adjustment'
    }
    if (!Object.keys(body).length) {
      setSelected(null)
      return
    }
    if (hasAdjustment) {
      stepUp.confirm((token) => doUpdate(body, token))
      return
    }
    doUpdate(body).catch(showError)
  }

  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-6">
      <PageHeader title="Users" description="Search, manage, and moderate accounts" />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            placeholder="Search email, username…"
            className="pl-9"
          />
        </div>
        <Select value={status} onValueChange={(v) => { setStatus(v); setPage(1) }}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All statuses</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="suspended">Suspended</SelectItem>
            <SelectItem value="banned">Banned</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-xl surface">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>User</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>CVX</TableHead>
              <TableHead>Tasks</TableHead>
              <TableHead>Approved</TableHead>
              <TableHead>Servers</TableHead>
              <TableHead>Risk</TableHead>
              <TableHead>Joined</TableHead>
              <TableHead className="text-right">Actions</TableHead>
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
                <TableCell colSpan={9} className="py-10 text-center text-muted-foreground">No users found.</TableCell>
              </TableRow>
            ) : (
              data.items.map((u) => (
                <TableRow key={u.id} className="cursor-pointer" onClick={() => openDialog(u)}>
                  <TableCell>
                    <div className="font-medium">{u.display_name || u.username}</div>
                    <div className="text-xs text-muted-foreground">{u.email}</div>
                  </TableCell>
                  <TableCell><StatusBadge status={u.status} /></TableCell>
                  <TableCell className="tabular">{formatCvx(u.cvx_balance)}</TableCell>
                  <TableCell className="tabular">{formatCompact(u.tasks_completed)}</TableCell>
                  <TableCell className="tabular">{formatCompact(u.conversions_approved)}</TableCell>
                  <TableCell className="tabular">{u.active_servers}</TableCell>
                  <TableCell>
                    <span className={`tabular ${u.risk_score >= 60 ? 'text-red-400' : u.risk_score >= 30 ? 'text-amber-400' : 'text-muted-foreground'}`}>
                      {Math.round(u.risk_score)}
                    </span>
                  </TableCell>
                  <TableCell className="tabular">{formatDate(u.created_at || '')}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); openDialog(u) }}>
                      Manage
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && (
        <Pagination
          page={data.page}
          pages={data.pages}
          total={data.total}
          pageSize={data.page_size}
          onChange={setPage}
        />
      )}

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Manage user</DialogTitle>
            <DialogDescription>
              {selected?.email} · {selected?.username}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Account status</Label>
              <Select value={newStatus} onValueChange={setNewStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="suspended">Suspended</SelectItem>
                  <SelectItem value="banned">Banned</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>CVX adjustment (positive = credit, negative = debit)</Label>
              <Input
                type="number"
                value={adjustment}
                onChange={(e) => setAdjustment(e.target.value)}
                placeholder="0"
              />
            </div>
            <div className="space-y-2">
              <Label>Adjustment reason</Label>
              <Input value={adjustReason} onChange={(e) => setAdjustReason(e.target.value)} placeholder="Support adjustment" />
            </div>
            <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
              Risk score: <span className="tabular text-foreground">{selected ? Math.round(selected.risk_score) : '—'}</span> ·
              Current balance: <span className="tabular text-foreground">{selected ? formatCvx(selected.cvx_balance) : '—'}</span>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelected(null)}>Cancel</Button>
            <Button onClick={apply} loading={saving}>Apply changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <StepUpDialog handle={stepUp} />
    </div>
  )
}
