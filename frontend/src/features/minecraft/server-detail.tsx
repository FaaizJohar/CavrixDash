import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import {
  ArrowLeft,
  ArrowUpCircle,
  Cpu,
  Database,
  HardDrive,
  Network,
  Play,
  RotateCw,
  Square,
  Terminal,
  SkipForward,
  Power,
  RefreshCw,
  Archive,
} from 'lucide-react'
import { api, showError } from '@/lib/api'
import type { ServerOut, UpgradePriceOut, UpgradeQuote } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { GlassCard } from '@/components/shared/glass-card'
import { StatusBadge } from '@/components/shared/status-badge'
import { ProgressBar } from '@/components/shared/progress-bar'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ErrorState } from '@/components/shared/error-state'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { formatBytes, formatCvx } from '@/lib/utils'
import { ServerConsole } from './console'
import { CvxBadge } from '@/components/shared/cvx-badge'
import { cn } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'

export function ServerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [actionTarget, setActionTarget] = useState<string | null>(null)
  const [upgradeFor, setUpgradeFor] = useState<{ type: string; amount: number } | null>(null)

  const serverQ = useQuery({
    queryKey: ['servers', id],
    queryFn: () => api.get<ServerOut>(`/servers/${id}`),
    refetchInterval: 15_000,
  })

  const statsQ = useQuery({
    queryKey: ['servers', id, 'stats'],
    queryFn: () => api.get<Record<string, unknown>>(`/servers/${id}/stats`),
    refetchInterval: 10_000,
    enabled: !!id,
  })

  const pricesQ = useQuery({
    queryKey: ['upgrade-prices'],
    queryFn: () => api.get<UpgradePriceOut[]>('/servers/upgrades/prices'),
  })

  const actionMutation = useMutation({
    mutationFn: (action: string) => api.post(`/servers/${id}/action`, { action }),
    onSuccess: () => {
      toast.success('Command sent to server')
      qc.invalidateQueries({ queryKey: ['servers', id] })
      setActionTarget(null)
    },
    onError: (err) => showError(err),
  })

  const upgradeQuoteQ = useQuery({
    queryKey: ['servers', id, 'upgrade-quote', upgradeFor?.type, upgradeFor?.amount],
    queryFn: () =>
      api.post<UpgradeQuote>(`/servers/${id}/upgrades/preview`, {
        upgrade_type: upgradeFor?.type,
        amount: upgradeFor?.amount || 1,
      }),
    enabled: !!upgradeFor,
  })

  const buyUpgrade = useMutation({
    mutationFn: () =>
      api.post(`/servers/${id}/upgrades`, {
        upgrade_type: upgradeFor?.type,
        amount: upgradeFor?.amount || 1,
      }),
    onSuccess: () => {
      toast.success('Upgrade applied!')
      setUpgradeFor(null)
      qc.invalidateQueries({ queryKey: ['servers', id] })
      qc.invalidateQueries({ queryKey: ['wallet'] })
    },
    onError: (err) => showError(err),
  })

  if (serverQ.error) return <ErrorState onRetry={() => serverQ.refetch()} />
  const server = serverQ.data
  const live = (statsQ.data || server?.live || {}) as Record<string, unknown>
  const online = server?.status === 'running' || live.online === true

  const cpuPct = Number(live.cpu_percent ?? live.cpu_absolute ?? 0)
  const memPct = Number(live.memory_percent ?? 0)
  const diskPct = Number(live.disk_percent ?? 0)

  const actions = [
    { action: 'start', label: 'Start', icon: Play, disabled: online },
    { action: 'stop', label: 'Stop', icon: Square, disabled: !online, danger: true },
    { action: 'restart', label: 'Restart', icon: RotateCw, disabled: !online },
    { action: 'kill', label: 'Kill', icon: Power, disabled: !online, danger: true },
    { action: 'reinstall', label: 'Reinstall', icon: RefreshCw, danger: true },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title={server?.name || 'Server'}
        description={server ? `${server.region} · ${server.software} ${server.version}` : ''}
        actions={
          <div className="flex items-center gap-2">
            {server && <StatusBadge status={online ? 'online' : 'offline'} />}
            <Button asChild variant="ghost" size="sm">
              <Link to="/minecraft">
                <ArrowLeft className="h-4 w-4" /> Back
              </Link>
            </Button>
          </div>
        }
      />

      {/* Live stats */}
      <GlassCard className="p-5">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatTile icon={Cpu} label="CPU" value={serverQ.isLoading ? null : `${Math.round(cpuPct)}%`} sub={`${server?.cpu ?? '—'} cores`} color="text-cyan-300" />
          <StatTile icon={Database} label="RAM" value={serverQ.isLoading ? null : live.memory_bytes !== undefined ? formatBytes(Number(live.memory_bytes)) : '—'} sub={server?.ram_mb ? `${server.ram_mb / 1024} GB` : ''} color="text-violet-300" />
          <StatTile icon={HardDrive} label="Storage" value={serverQ.isLoading ? null : live.disk_bytes !== undefined ? formatBytes(Number(live.disk_bytes)) : '—'} sub={server?.disk_mb ? `${server.disk_mb / 1024} GB` : ''} color="text-emerald-300" />
          <StatTile
            icon={Network}
            label="Players"
            value={serverQ.isLoading ? null : live.players !== undefined ? String(live.players) : '—'}
            sub={server?.ip ? `${server.ip}:${server.port}` : '—'}
            color="text-amber-300"
          />
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <UsageBar label="CPU" value={cpuPct} color="bg-cyan-400" />
          <UsageBar label="RAM" value={memPct} color="bg-violet-400" />
          <UsageBar label="Disk" value={diskPct} color="bg-emerald-400" />
        </div>
      </GlassCard>

      {/* Actions */}
      <div className="flex flex-wrap items-center gap-2">
        {actions.map((a) => (
          <Button
            key={a.action}
            variant={a.danger ? 'outline' : a.action === 'start' ? 'success' : 'secondary'}
            size="sm"
            disabled={a.disabled || actionMutation.isPending}
            className={cn(a.danger && 'text-destructive hover:text-destructive')}
            onClick={() => {
              if (a.danger) setActionTarget(a.action)
              else actionMutation.mutate(a.action)
            }}
          >
            <a.icon className="h-3.5 w-3.5" /> {a.label}
          </Button>
        ))}
        <Button asChild variant="ghost" size="sm" className="ml-auto">
          <Link to={`/minecraft/${id}/console`}>
            <Terminal className="h-3.5 w-3.5" /> Open Console
          </Link>
        </Button>
      </div>

      <Tabs defaultValue="upgrades">
        <TabsList>
          <TabsTrigger value="upgrades">
            <ArrowUpCircle className="mr-1.5 h-3.5 w-3.5" /> Upgrades
          </TabsTrigger>
          <TabsTrigger value="console">
            <Terminal className="mr-1.5 h-3.5 w-3.5" /> Console
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upgrades" className="mt-4 space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(pricesQ.data || []).filter((p) => p.enabled).map((p) => {
              const active = upgradeFor?.type === p.upgrade_type
              return (
                <div
                  key={p.upgrade_type}
                  className={cn(
                    'rounded-xl surface p-4 transition-all',
                    active && 'border-primary/50 ring-1 ring-primary/30',
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-semibold">{p.label}</div>
                    <CvxBadge value={p.cvx_cost} />
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    +{p.unit_size} {p.unit} per purchase
                  </div>
                  <Button
                    size="sm"
                    variant={active ? 'default' : 'outline'}
                    className="mt-3 w-full"
                    onClick={() => setUpgradeFor({ type: p.upgrade_type, amount: p.unit_size })}
                  >
                    {active ? 'Review' : 'Upgrade'}
                  </Button>
                </div>
              )
            })}
          </div>

          {upgradeFor && (
            <GlassCard className="p-5">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="text-sm font-semibold">Upgrade preview</div>
                  <div className="mt-1 text-sm text-muted-foreground">
                    {upgradeQuoteQ.data?.label}: {upgradeQuoteQ.data?.current_value} →{' '}
                    <span className="text-foreground">{upgradeQuoteQ.data?.new_value}</span> {upgradeQuoteQ.data?.unit}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {upgradeQuoteQ.data && <CvxBadge value={upgradeQuoteQ.data.cvx_cost} />}
                  <Button
                    loading={buyUpgrade.isPending}
                    onClick={() => buyUpgrade.mutate()}
                    disabled={!upgradeQuoteQ.data}
                  >
                    Buy upgrade
                  </Button>
                  <Button variant="ghost" onClick={() => setUpgradeFor(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            </GlassCard>
          )}
        </TabsContent>

        <TabsContent value="console" className="mt-4">
          <ServerConsole serverId={id!} />
        </TabsContent>
      </Tabs>

      {/* Danger confirmations */}
      <ConfirmDialog
        open={!!actionTarget}
        onOpenChange={(o) => !o && setActionTarget(null)}
        title={`${actionTarget === 'reinstall' ? 'Reinstall' : actionTarget === 'kill' ? 'Kill' : 'Stop'} server?`}
        description={
          actionTarget === 'reinstall'
            ? 'This will wipe the server and reinstall from the template. All data will be lost.'
            : actionTarget === 'kill'
              ? 'This forcefully powers off the server. Any unsaved data will be lost.'
              : 'This will stop the server. You can start it again later.'
        }
        confirmText={actionTarget === 'reinstall' ? 'Reinstall' : actionTarget === 'kill' ? 'Kill' : 'Stop'}
        danger={actionTarget === 'reinstall' || actionTarget === 'kill'}
        loading={actionMutation.isPending}
        onConfirm={() => actionTarget && actionMutation.mutate(actionTarget)}
      />
    </div>
  )
}

function StatTile({
  icon: Icon,
  label,
  value,
  sub,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: React.ReactNode
  sub?: string
  color: string
}) {
  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3">
      <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
        <Icon className={cn('h-3.5 w-3.5', color)} /> {label}
      </div>
      <div className="mt-1.5 truncate text-lg font-semibold tabular">
        {value === null ? <Skeleton className="h-5 w-14" /> : value}
      </div>
      {sub && <div className="mt-0.5 truncate font-mono text-[11px] text-muted-foreground">{sub}</div>}
    </div>
  )
}

function UsageBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="tabular text-muted-foreground">{Math.round(value)}%</span>
      </div>
      <ProgressBar value={value} indicatorClassName={color} />
    </div>
  )
}
