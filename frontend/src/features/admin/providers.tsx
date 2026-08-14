import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plus, RefreshCw, Zap, Link2, Unplug, Save } from 'lucide-react'
import { api, showError } from '@/lib/api'
import type { ProviderOut, Paginated } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { GlassCard } from '@/components/shared/glass-card'
import { StatusBadge } from '@/components/shared/status-badge'
import { ErrorState } from '@/components/shared/error-state'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { formatCurrency, formatCompact } from '@/lib/utils'

export function AdminProvidersPage() {
  const qc = useQueryClient()
  const [editing, setEditing] = useState<ProviderOut | null>(null)
  const [credValues, setCredValues] = useState<Record<string, string>>({})
  const [multiplier, setMultiplier] = useState('1.0')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'providers'],
    queryFn: () => api.get<Paginated<ProviderOut>>('/admin/providers?page=1&page_size=100'),
  })

  const providers = data?.items ?? []

  const testMutation = useMutation({
    mutationFn: (id: string) => api.post<{ ok: boolean; message: string }>(`/admin/providers/${id}/test`),
    onSuccess: (res, id) => {
      toast.success(res.ok ? 'Provider reachable' : res.message || 'Test completed')
      qc.invalidateQueries({ queryKey: ['admin', 'providers'] })
    },
    onError: (err) => showError(err),
  })

  const syncMutation = useMutation({
    mutationFn: (id: string) => api.post(`/admin/providers/${id}/sync`),
    onSuccess: () => {
      toast.success('Offer sync started')
      qc.invalidateQueries({ queryKey: ['admin', 'providers'] })
      qc.invalidateQueries({ queryKey: ['admin', 'offers'] })
    },
    onError: (err) => showError(err),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => api.patch(`/admin/providers/${id}`, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'providers'] }),
    onError: (err) => showError(err),
  })

  const saveMutation = useMutation({
    mutationFn: () =>
      api.patch(`/admin/providers/${editing!.id}`, {
        reward_multiplier: Number(multiplier),
        credentials: Object.fromEntries(Object.entries(credValues).filter(([, v]) => v)),
      }),
    onSuccess: () => {
      toast.success('Provider updated')
      setEditing(null)
      qc.invalidateQueries({ queryKey: ['admin', 'providers'] })
    },
    onError: (err) => showError(err),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-6">
      <PageHeader title="Providers" description="Connect offer providers and manage integrations" />

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-44 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      ) : providers.length === 0 ? (
        <div className="rounded-xl surface p-8 text-center text-sm text-muted-foreground">
          No providers configured. Create one from the backend or seed script.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {providers.map((p) => (
            <Card key={p.id}>
              <CardHeader className="flex-row items-start justify-between space-y-0 p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gradient-to-br from-cavrix-500 to-cyan-500 text-white">
                    <Zap className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold">{p.name}</div>
                    <div className="text-xs text-muted-foreground">{p.code} · {p.kind}</div>
                  </div>
                </div>
                <StatusBadge status={p.enabled ? (p.status || 'connected') : 'disabled'} />
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <div className="grid grid-cols-3 gap-2">
                  <div className="rounded-lg bg-muted/50 p-2.5 text-center">
                    <div className="text-xs text-muted-foreground">Revenue</div>
                    <div className="mt-0.5 text-sm font-semibold tabular">{formatCurrency(p.revenue_tracked)}</div>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-2.5 text-center">
                    <div className="text-xs text-muted-foreground">Multiplier</div>
                    <div className="mt-0.5 text-sm font-semibold tabular">{p.reward_multiplier.toFixed(2)}×</div>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-2.5 text-center">
                    <div className="text-xs text-muted-foreground">Reliability</div>
                    <div className="mt-0.5 text-sm font-semibold tabular">{Math.round(p.reliability * 100)}%</div>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" onClick={() => testMutation.mutate(p.id)} loading={testMutation.isPending}>
                    <Link2 className="h-3.5 w-3.5" /> Test
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => syncMutation.mutate(p.id)} loading={syncMutation.isPending}>
                    <RefreshCw className="h-3.5 w-3.5" /> Sync offers
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setEditing(p)
                      setMultiplier(String(p.reward_multiplier))
                      setCredValues({})
                    }}
                  >
                    <Save className="h-3.5 w-3.5" /> Configure
                  </Button>
                  <Button
                    size="sm"
                    variant={p.enabled ? 'secondary' : 'success'}
                    className="ml-auto"
                    onClick={() => toggleMutation.mutate({ id: p.id, enabled: !p.enabled })}
                  >
                    {p.enabled ? <><Unplug className="h-3.5 w-3.5" /> Disable</> : <><Plus className="h-3.5 w-3.5" /> Enable</>}
                  </Button>
                </div>
                {p.last_error && (
                  <div className="mt-3 rounded-lg border border-red-400/20 bg-red-400/5 p-2.5 text-xs text-red-300">
                    {p.last_error}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Configure {editing?.name}</DialogTitle>
            <DialogDescription>API credentials are encrypted at rest and never shown after saving.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Reward multiplier</Label>
              <Input value={multiplier} onChange={(e) => setMultiplier(e.target.value)} inputMode="decimal" />
              <p className="text-xs text-muted-foreground">
                Applied on top of the global CVX multiplier for this provider's offers.
              </p>
            </div>
            <div className="space-y-3">
              <Label>Credentials (leave blank to keep current)</Label>
              {editing && Object.keys(editing.credentials_masked || {}).length > 0 ? (
                Object.keys(editing.credentials_masked).map((key) => (
                  <div key={key} className="space-y-1.5">
                    <Label className="text-xs capitalize">{key.replace(/_/g, ' ')}</Label>
                    <Input
                      type="password"
                      placeholder={editing.credentials_masked[key] || '••••••••'}
                      value={credValues[key] || ''}
                      onChange={(e) => setCredValues((v) => ({ ...v, [key]: e.target.value }))}
                    />
                  </div>
                ))
              ) : (
                <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
                  No stored credentials for this provider.
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
            <Button onClick={() => saveMutation.mutate()} loading={saveMutation.isPending}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
