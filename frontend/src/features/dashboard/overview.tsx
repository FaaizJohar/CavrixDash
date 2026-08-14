import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Coins,
  Server,
  CheckCircle2,
  Clock,
  ArrowRight,
  Rocket,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import { api } from '@/lib/api'
import type { OverviewStats } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { MetricCard } from '@/components/shared/metric-card'
import { GlassCard } from '@/components/shared/glass-card'
import { ProgressBar } from '@/components/shared/progress-bar'
import { CvxBadge } from '@/components/shared/cvx-badge'
import { SkeletonGrid, SkeletonCard } from '@/components/shared/skeleton'
import { ErrorState } from '@/components/shared/error-state'
import { FadeIn } from '@/components/shared/motion'
import { StatusBadge } from '@/components/shared/status-badge'
import { categoryLabels } from '@/lib/labels'
import { formatCvx, formatRelative } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/stores/auth'

export function OverviewPage() {
  const user = useAuth((s) => s.user)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['overview'],
    queryFn: () => api.get<OverviewStats>('/analytics/overview'),
  })

  if (error) {
    return <ErrorState onRetry={() => refetch()} />
  }

  const servers = (data?.servers || []) as Array<Record<string, unknown> & { id: string; name: string; status: string }>
  const recommended = (data?.recommended_offers || []) as Array<Record<string, unknown> & { id: string; title: string; effective_reward?: number; reward?: number; estimated_time?: number; category?: string }>
  const ledger = (data?.recent_ledger || []) as Array<Record<string, unknown> & { transaction_type: string; amount: number; description?: string }>
  const progress = data ? Math.min(100, (data.next_reward_progress / data.next_reward_target) * 100) : 0

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome back, ${user?.display_name || user?.username || 'friend'}`}
        description="Here's what's happening with your Cavrix Cloud"
      />

      {/* CVX hero + stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard
          label="CVX Balance"
          value={data ? formatCvx(data.cvx_balance, data.cvx_symbol) : '—'}
          icon={Coins}
          iconClassName="bg-amber-400/10 text-amber-300"
          loading={isLoading}
        />
        <MetricCard
          label="Active Servers"
          value={data ? `${data.active_servers} / ${data.server_limit}` : '—'}
          icon={Server}
          iconClassName="bg-emerald-400/10 text-emerald-300"
          loading={isLoading}
        />
        <MetricCard
          label="Tasks Completed"
          value={data?.tasks_completed ?? null}
          icon={CheckCircle2}
          iconClassName="bg-cavrix-400/10 text-cavrix-300"
          loading={isLoading}
        />
        <MetricCard
          label="Approved Conversions"
          value={data?.conversions_approved ?? null}
          sub={
            data ? `${data.conversions_pending} pending` : undefined
          }
          icon={TrendingUp}
          iconClassName="bg-cyan-400/10 text-cyan-300"
          loading={isLoading}
        />
      </div>

      {/* Next reward progress */}
      {data && data.next_reward_target > 0 && (
        <GlassCard className="p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Rocket className="h-5 w-5" />
              </div>
              <div>
                <div className="text-sm font-semibold">Next server reward</div>
                <div className="text-xs text-muted-foreground">
                  {formatCvx(data.next_reward_target - data.next_reward_progress, data.cvx_symbol)} remaining
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-40 sm:w-56">
                <ProgressBar value={progress} showLabel />
              </div>
              <div className="text-right">
                <div className="text-lg font-bold tabular text-gradient">
                  {Math.round(progress)}%
                </div>
              </div>
            </div>
          </div>
        </GlassCard>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recommended tasks */}
        <div className="space-y-3 lg:col-span-1">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recommended tasks</h2>
            <Link to="/earn" className="flex items-center gap-1 text-xs text-primary hover:underline">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          {isLoading ? (
            <SkeletonCard />
          ) : recommended.length === 0 ? (
            <GlassCard className="p-5 text-center text-sm text-muted-foreground">
              No tasks available right now. Check back soon.
            </GlassCard>
          ) : (
            <div className="space-y-2.5">
              {recommended.slice(0, 4).map((o) => (
                <Link key={o.id} to="/earn">
                  <GlassCard interactive className="flex items-center justify-between p-3.5">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{o.title}</div>
                      <div className="text-xs text-muted-foreground">
                        {categoryLabels[o.category || 'other']}
                        {o.estimated_time ? ` · ~${o.estimated_time} min` : ''}
                      </div>
                    </div>
                    <CvxBadge value={o.effective_reward ?? o.reward ?? 0} />
                  </GlassCard>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Minecraft servers */}
        <div className="space-y-3 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Your Minecraft servers</h2>
            <Link to="/minecraft" className="flex items-center gap-1 text-xs text-primary hover:underline">
              Manage <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          {isLoading ? (
            <SkeletonGrid count={2} />
          ) : servers.length === 0 ? (
            <GlassCard className="flex flex-col items-center gap-3 p-8 text-center">
              <Server className="h-8 w-8 text-muted-foreground" />
              <div>
                <div className="text-sm font-semibold">No servers yet</div>
                <p className="mt-1 text-sm text-muted-foreground">
                  Claim your first free Minecraft server with CVX credits.
                </p>
              </div>
              <Button asChild size="sm">
                <Link to="/minecraft/new">Create a server</Link>
              </Button>
            </GlassCard>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {servers.slice(0, 2).map((s) => (
                <Link key={s.id} to={`/minecraft/${s.id}`}>
                  <GlassCard interactive className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="truncate text-sm font-semibold">{s.name}</div>
                      <StatusBadge status={s.status || 'offline'} />
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      {String(s.region || 'NA')} · {String(s.plan_name || 'Minecraft')}
                    </div>
                    <div className="mt-2 font-mono text-xs text-muted-foreground">
                      {(s as unknown as { ip?: string }).ip || '—'}:
                      {(s as unknown as { port?: number }).port || '—'}
                    </div>
                  </GlassCard>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent transactions */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Recent CVX activity</h2>
          <Link to="/rewards/wallet" className="flex items-center gap-1 text-xs text-primary hover:underline">
            Open wallet <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
        <GlassCard className="divide-y divide-border/50">
          {isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-10 animate-pulse rounded-md bg-muted" />
              ))}
            </div>
          ) : ledger.length === 0 ? (
            <div className="flex items-center justify-center gap-2 p-6 text-sm text-muted-foreground">
              <Wallet className="h-4 w-4" /> No transactions yet. Start earning CVX!
            </div>
          ) : (
            ledger.map((entry, i) => (
              <div key={i} className="flex items-center justify-between px-4 py-3">
                <div>
                  <div className="text-sm font-medium">{entry.description || entry.transaction_type}</div>
                  <div className="text-xs text-muted-foreground">
                    {formatRelative((entry.created_at as string) || '')}
                  </div>
                </div>
                <div className="text-right">
                  <div
                    className={`text-sm font-semibold tabular ${
                      (entry.amount || 0) >= 0 ? 'text-emerald-400' : 'text-slate-300'
                    }`}
                  >
                    {entry.amount >= 0 ? '+' : ''}
                    {formatCvx(entry.amount, data?.cvx_symbol)}
                  </div>
                </div>
              </div>
            ))
          )}
        </GlassCard>
      </div>
    </div>
  )
}
