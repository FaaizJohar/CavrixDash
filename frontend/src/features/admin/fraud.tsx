import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ShieldAlert, Save } from 'lucide-react'
import { api, showError } from '@/lib/api'
import type { Paginated, FraudEventOut, AdminUserRow } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { ErrorState } from '@/components/shared/error-state'
import { StatusBadge } from '@/components/shared/status-badge'
import { Pagination } from '@/components/shared/pagination'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { formatRelative } from '@/lib/utils'

interface FraudRule {
  key: string
  label: string
  description: string
  value: string
}

export function AdminFraudPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Fraud Protection"
        description="Risk events, flagged users, and detection thresholds"
      />
      <Tabs defaultValue="events">
        <TabsList>
          <TabsTrigger value="events">Events</TabsTrigger>
          <TabsTrigger value="users">Flagged users</TabsTrigger>
          <TabsTrigger value="rules">Rules</TabsTrigger>
        </TabsList>
        <TabsContent value="events" className="mt-4"><EventsTab /></TabsContent>
        <TabsContent value="users" className="mt-4"><UsersTab /></TabsContent>
        <TabsContent value="rules" className="mt-4"><RulesTab /></TabsContent>
      </Tabs>
    </div>
  )
}

function EventsTab() {
  const [page, setPage] = useState(1)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'fraud', 'events', page],
    queryFn: () => api.get<Paginated<FraudEventOut>>(`/admin/fraud/events?page=${page}&page_size=25`),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-4">
      <div className="rounded-xl surface">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Event</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>User</TableHead>
              <TableHead>When</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 5 }).map((__, j) => (
                    <TableCell key={j}><div className="h-4 animate-pulse rounded bg-muted" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : !data || data.items.length === 0 ? (
              <TableRow><TableCell colSpan={5} className="py-10 text-center text-muted-foreground">No risk events. All clear.</TableCell></TableRow>
            ) : (
              data.items.map((e) => (
                <TableRow key={e.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <ShieldAlert className="h-4 w-4 text-muted-foreground" />
                      <span className="font-mono text-xs">{e.event_type}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      e.severity === 'critical' || e.severity === 'high' ? 'bg-rose-400/10 text-rose-300' :
                      e.severity === 'medium' ? 'bg-amber-400/10 text-amber-300' : 'bg-muted text-muted-foreground'
                    }`}>{e.severity}</span>
                  </TableCell>
                  <TableCell className="max-w-md text-xs text-muted-foreground">{e.description}</TableCell>
                  <TableCell className="font-mono text-xs">{e.user_id.slice(0, 8)}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{formatRelative(e.created_at || '')}</TableCell>
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

function UsersTab() {
  const [page, setPage] = useState(1)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'fraud', 'users', page],
    queryFn: () => api.get<Paginated<AdminUserRow>>(`/admin/fraud/users?page=${page}&page_size=25`),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-4">
      <div className="rounded-xl surface">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>User</TableHead>
              <TableHead>Risk score</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Tasks</TableHead>
              <TableHead>Servers</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 5 }).map((__, j) => (
                    <TableCell key={j}><div className="h-4 animate-pulse rounded bg-muted" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : !data || data.items.length === 0 ? (
              <TableRow><TableCell colSpan={5} className="py-10 text-center text-muted-foreground">No flagged users.</TableCell></TableRow>
            ) : (
              data.items.map((u) => (
                <TableRow key={u.id}>
                  <TableCell>
                    <div className="font-medium">{u.display_name || u.username}</div>
                    <div className="text-xs text-muted-foreground">{u.email}</div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 overflow-hidden rounded bg-muted">
                        <div
                          className={`h-full rounded ${u.risk_score > 70 ? 'bg-rose-400' : u.risk_score > 40 ? 'bg-amber-400' : 'bg-emerald-400'}`}
                          style={{ width: `${Math.min(u.risk_score, 100)}%` }}
                        />
                      </div>
                      <span className="tabular text-xs">{Math.round(u.risk_score)}</span>
                    </div>
                  </TableCell>
                  <TableCell><StatusBadge status={u.status} /></TableCell>
                  <TableCell className="tabular text-xs">{u.tasks_completed}</TableCell>
                  <TableCell className="tabular text-xs">{u.active_servers}</TableCell>
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

function RulesTab() {
  const qc = useQueryClient()
  const [values, setValues] = useState<Record<string, string>>({})

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'fraud', 'rules'],
    queryFn: () => api.get<FraudRule[]>('/admin/fraud/rules'),
  })

  const save = useMutation({
    mutationFn: () => api.patch('/admin/fraud/rules', { rules: values }),
    onSuccess: () => {
      toast.success('Fraud rules updated')
      qc.invalidateQueries({ queryKey: ['admin', 'fraud', 'rules'] })
    },
    onError: (err) => showError(err),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  const rules = data || []

  return (
    <Card>
      <CardHeader>
        <CardTitle>Detection thresholds</CardTitle>
        <CardDescription>Tune sensitivity for automatic fraud detection</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-14 animate-pulse rounded bg-muted" />)}
          </div>
        ) : rules.length === 0 ? (
          <div className="py-8 text-center text-sm text-muted-foreground">No rules configured.</div>
        ) : (
          rules.map((r) => (
            <div key={r.key} className="space-y-1.5">
              <Label htmlFor={r.key}>{r.label}</Label>
              <Input
                id={r.key}
                value={values[r.key] ?? r.value}
                onChange={(e) => setValues((v) => ({ ...v, [r.key]: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">{r.description}</p>
            </div>
          ))
        )}
        <Button onClick={() => save.mutate()} loading={save.isPending} disabled={rules.length === 0}>
          <Save className="h-4 w-4" /> Save thresholds
        </Button>
      </CardContent>
    </Card>
  )
}
