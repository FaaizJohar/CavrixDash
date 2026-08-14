import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Link2, Plus, Save, Pencil, Trash2 } from 'lucide-react'
import { api, showError } from '@/lib/api'
import type { Paginated, PlanOut, RegionOut, NodeOut, TemplateOut } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { StatusBadge } from '@/components/shared/status-badge'
import { Pagination } from '@/components/shared/pagination'
import { ErrorState } from '@/components/shared/error-state'
import { Button } from '@/components/ui/button'
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { formatCvx } from '@/lib/utils'

export function AdminMinecraftPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Minecraft Infrastructure"
        description="Server plans, nodes, regions, and templates"
        actions={<PterodactylTestButton />}
      />
      <Tabs defaultValue="plans">
        <TabsList>
          <TabsTrigger value="plans">Plans</TabsTrigger>
          <TabsTrigger value="nodes">Nodes</TabsTrigger>
          <TabsTrigger value="regions">Regions</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="pterodactyl">Pterodactyl</TabsTrigger>
        </TabsList>
        <TabsContent value="plans" className="mt-4"><PlansTab /></TabsContent>
        <TabsContent value="nodes" className="mt-4"><NodesTab /></TabsContent>
        <TabsContent value="regions" className="mt-4"><RegionsTab /></TabsContent>
        <TabsContent value="templates" className="mt-4"><TemplatesTab /></TabsContent>
        <TabsContent value="pterodactyl" className="mt-4"><PterodactylTab /></TabsContent>
      </Tabs>
    </div>
  )
}

function PterodactylTestButton() {
  const test = useMutation({
    mutationFn: () => api.post<{ ok: boolean; message: string }>('/admin/pterodactyl/test'),
    onSuccess: (res) => toast.success(res.ok ? 'Pterodactyl connected' : res.message || 'Test result'),
    onError: (err) => showError(err),
  })
  return (
    <Button variant="outline" onClick={() => test.mutate()} loading={test.isPending}>
      <Link2 className="h-4 w-4" /> Test Connection
    </Button>
  )
}

function PlansTab() {
  const [page, setPage] = useState(1)
  const qc = useQueryClient()
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'plans', page],
    queryFn: () => api.get<Paginated<PlanOut>>(`/admin/plans?page=${page}&page_size=25`),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.patch(`/admin/plans/${id}`, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'plans'] }),
    onError: (err) => showError(err),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-4">
      <div className="rounded-xl surface">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Plan</TableHead>
              <TableHead>CPU</TableHead>
              <TableHead>RAM</TableHead>
              <TableHead>Disk</TableHead>
              <TableHead>Backups</TableHead>
              <TableHead>Region</TableHead>
              <TableHead>CVX Cost</TableHead>
              <TableHead>Renewal</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 11 }).map((__, j) => (
                    <TableCell key={j}><div className="h-4 animate-pulse rounded bg-muted" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : !data || data.items.length === 0 ? (
              <TableRow><TableCell colSpan={11} className="py-10 text-center text-muted-foreground">No plans found.</TableCell></TableRow>
            ) : (
              data.items.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>
                    <div className="font-medium">{p.name}</div>
                    <div className="text-xs text-muted-foreground">{p.description}</div>
                  </TableCell>
                  <TableCell className="tabular">{p.cpu}</TableCell>
                  <TableCell className="tabular">{p.ram_mb >= 1024 ? `${p.ram_mb / 1024} GB` : `${p.ram_mb} MB`}</TableCell>
                  <TableCell className="tabular">{p.disk_mb >= 1024 ? `${p.disk_mb / 1024} GB` : `${p.disk_mb} MB`}</TableCell>
                  <TableCell className="tabular">{p.backups}</TableCell>
                  <TableCell className="text-xs">{p.region}</TableCell>
                  <TableCell className="tabular">{formatCvx(p.cvx_cost)}</TableCell>
                  <TableCell className="tabular">{p.renewal_cost ? formatCvx(p.renewal_cost) : '—'}</TableCell>
                  <TableCell className="tabular text-xs">{p.duration_days}d</TableCell>
                  <TableCell><StatusBadge status={p.status} /></TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 text-xs"
                      onClick={() => toggleMutation.mutate({ id: p.id, status: p.status === 'active' ? 'paused' : 'active' })}
                    >
                      {p.status === 'active' ? 'Pause' : 'Activate'}
                    </Button>
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

function NodesTab() {
  const qc = useQueryClient()
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'nodes'],
    queryFn: () => api.get<NodeOut[]>('/admin/nodes'),
  })
  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => api.patch(`/admin/nodes/${id}`, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'nodes'] }),
    onError: (err) => showError(err),
  })
  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="rounded-xl surface">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Node</TableHead>
            <TableHead>Region</TableHead>
            <TableHead>Memory</TableHead>
            <TableHead>Disk</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Enabled</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <TableRow key={i}>
                {Array.from({ length: 6 }).map((__, j) => (
                  <TableCell key={j}><div className="h-4 animate-pulse rounded bg-muted" /></TableCell>
                ))}
              </TableRow>
            ))
          ) : !data || data.length === 0 ? (
            <TableRow><TableCell colSpan={6} className="py-10 text-center text-muted-foreground">No nodes found.</TableCell></TableRow>
          ) : (
            data.map((n) => (
              <TableRow key={n.id}>
                <TableCell>
                  <div className="font-medium">{n.name}</div>
                  <div className="font-mono text-xs text-muted-foreground">{n.fqdn}</div>
                </TableCell>
                <TableCell className="text-xs">{n.region}</TableCell>
                <TableCell className="tabular text-xs">
                  {fmtMb(n.memory_allocated)} / {fmtMb(n.memory_limit)}
                </TableCell>
                <TableCell className="tabular text-xs">
                  {fmtMb(n.disk_allocated)} / {fmtMb(n.disk_limit)}
                </TableCell>
                <TableCell><StatusBadge status={n.status} /></TableCell>
                <TableCell className="text-right">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={() => toggleMutation.mutate({ id: n.id, enabled: !n.enabled })}
                  >
                    {n.enabled ? 'Disable' : 'Enable'}
                  </Button>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}

function RegionsTab() {
  const qc = useQueryClient()
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'regions'],
    queryFn: () => api.get<RegionOut[]>('/admin/regions'),
  })
  const toggleMutation = useMutation({
    mutationFn: ({ code, enabled }: { code: string; enabled: boolean }) => api.patch(`/admin/regions/${code}`, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'regions'] }),
    onError: (err) => showError(err),
  })
  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {isLoading ? (
        Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-xl bg-muted" />)
      ) : !data || data.length === 0 ? (
        <div className="col-span-full rounded-xl surface p-10 text-center text-sm text-muted-foreground">No regions found.</div>
      ) : (
        data.map((r) => (
          <Card key={r.code}>
            <CardContent className="flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                <div className="text-2xl">{r.flag || '🌍'}</div>
                <div>
                  <div className="text-sm font-semibold">{r.name}</div>
                  <div className="font-mono text-xs text-muted-foreground">{r.code}</div>
                </div>
              </div>
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={() => toggleMutation.mutate({ code: r.code, enabled: !r.enabled })}
              >
                {r.enabled ? 'Disable' : 'Enable'}
              </Button>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  )
}

function TemplatesTab() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'templates'],
    queryFn: () => api.get<TemplateOut[]>('/admin/templates'),
  })
  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {isLoading ? (
        Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-28 animate-pulse rounded-xl bg-muted" />)
      ) : !data || data.length === 0 ? (
        <div className="col-span-full rounded-xl surface p-10 text-center text-sm text-muted-foreground">No templates found.</div>
      ) : (
        data.map((t) => (
          <Card key={t.id}>
            <CardContent className="p-4">
              <div className="text-sm font-semibold">{t.name}</div>
              <div className="text-xs text-muted-foreground">{t.software}</div>
              <div className="mt-2 flex flex-wrap gap-1">
                {t.versions.slice(0, 4).map((v) => (
                  <span key={v} className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">{v}</span>
                ))}
              </div>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  )
}

function PterodactylTab() {
  const qc = useQueryClient()
  const [config, setConfig] = useState<Record<string, string>>({})

  const save = useMutation({
    mutationFn: () => api.patch('/admin/pterodactyl', config),
    onSuccess: () => {
      toast.success('Pterodactyl configuration saved')
      qc.invalidateQueries({ queryKey: ['admin', 'pterodactyl'] })
    },
    onError: (err) => showError(err),
  })

  const fields = [
    { key: 'pterodactyl_panel_url', label: 'Panel URL', placeholder: 'https://panel.example.com' },
    { key: 'pterodactyl_default_nest', label: 'Default Nest' },
    { key: 'pterodactyl_default_egg', label: 'Default Egg' },
    { key: 'pterodactyl_default_node', label: 'Default Node' },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pterodactyl Panel</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3 text-sm text-emerald-300">
          <span className="status-dot mr-2 bg-emerald-400" />
          API key and connection settings are managed under Secrets. Apply key updates there, then test the connection.
        </div>
        {fields.map((f) => (
          <div key={f.key} className="space-y-1.5">
            <Label htmlFor={f.key}>{f.label}</Label>
            <Input
              id={f.key}
              placeholder={f.placeholder}
              value={config[f.key] ?? ''}
              onChange={(e) => setConfig((c) => ({ ...c, [f.key]: e.target.value }))}
            />
          </div>
        ))}
        <Button onClick={() => save.mutate()} loading={save.isPending}>
          <Save className="h-4 w-4" /> Save configuration
        </Button>
      </CardContent>
    </Card>
  )
}

function fmtMb(mb: number | undefined): string {
  if (!mb && mb !== 0) return '—'
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb} MB`
}
