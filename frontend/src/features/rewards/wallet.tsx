import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Coins, TrendingUp, TrendingDown, Wallet as WalletIcon } from 'lucide-react'
import { api } from '@/lib/api'
import type { WalletOut, Paginated, LedgerEntry } from '@/types'
import { GlassCard } from '@/components/shared/glass-card'
import { MetricCard } from '@/components/shared/metric-card'
import { StatusBadge } from '@/components/shared/status-badge'
import { ErrorState } from '@/components/shared/error-state'
import { EmptyState } from '@/components/shared/empty-state'
import { formatCvx, formatRelative } from '@/lib/utils'
import { ledgerTypeColors, ledgerTypeLabels } from '@/lib/labels'
import { ProgressBar } from '@/components/shared/progress-bar'
import { Button } from '@/components/ui/button'

export function WalletPage() {
  const walletQ = useQuery({
    queryKey: ['wallet'],
    queryFn: () => api.get<WalletOut>('/cvx/wallet'),
  })
  const ledgerQ = useQuery({
    queryKey: ['ledger'],
    queryFn: () => api.get<Paginated<LedgerEntry>>('/cvx/ledger?page=1&page_size=15'),
  })

  if (walletQ.error || ledgerQ.error) return <ErrorState onRetry={() => { walletQ.refetch(); ledgerQ.refetch() }} />

  const wallet = walletQ.data

  const dailyPct = wallet ? (wallet.earned_today / wallet.daily_limit) * 100 : 0
  const hourlyPct = wallet ? (wallet.earned_this_hour / wallet.hourly_limit) * 100 : 0

  return (
    <div className="space-y-6">
      {/* Balance hero */}
      <GlassCard className="relative overflow-hidden p-6">
        <div
          className="pointer-events-none absolute inset-0"
          style={{ background: 'radial-gradient(400px 200px at 90% 0%, rgba(245,158,11,0.12), transparent 60%)' }}
        />
        <div className="relative">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <WalletIcon className="h-4 w-4" /> Available balance
          </div>
          <div className="mt-2 flex items-end gap-3">
            <div className="text-4xl font-bold tabular tracking-tight text-gradient">
              {wallet ? formatCvx(wallet.balance) : '—'}
            </div>
            <div className="mb-1 text-xs text-muted-foreground">
              {wallet ? `max ${formatCvx(wallet.max_balance)}` : ''}
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-6">
            <div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <TrendingUp className="h-3 w-3 text-emerald-400" /> Lifetime earned
              </div>
              <div className="mt-0.5 text-sm font-semibold tabular text-emerald-400">
                {wallet ? formatCvx(wallet.lifetime_earned) : '—'}
              </div>
            </div>
            <div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <TrendingDown className="h-3 w-3 text-slate-400" /> Lifetime spent
              </div>
              <div className="mt-0.5 text-sm font-semibold tabular">{wallet ? formatCvx(wallet.lifetime_spent) : '—'}</div>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Limits */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl surface p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Earned today</span>
            <span className="text-xs text-muted-foreground tabular">
              {wallet ? formatCvx(wallet.earned_today) : '—'} / {wallet ? formatCvx(wallet.daily_limit) : '—'}
            </span>
          </div>
          <ProgressBar value={dailyPct} className="mt-3" indicatorClassName="bg-emerald-400" />
        </div>
        <div className="rounded-xl surface p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Earned this hour</span>
            <span className="text-xs text-muted-foreground tabular">
              {wallet ? formatCvx(wallet.earned_this_hour) : '—'} / {wallet ? formatCvx(wallet.hourly_limit) : '—'}
            </span>
          </div>
          <ProgressBar value={hourlyPct} className="mt-3" indicatorClassName="bg-cyan-400" />
        </div>
      </div>

      {/* Ledger */}
      <div>
        <h3 className="mb-3 text-sm font-semibold">Transaction ledger</h3>
        <GlassCard className="divide-y divide-border/50">
          {ledgerQ.isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-11 animate-pulse rounded-md bg-muted" />
              ))}
            </div>
          ) : !ledgerQ.data || ledgerQ.data.items.length === 0 ? (
            <EmptyState icon={Coins} title="No transactions yet" description="Earn CVX to see your ledger here." />
          ) : (
            ledgerQ.data.items.map((entry) => (
              <div key={entry.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <div className={`text-sm font-medium ${ledgerTypeColors[entry.transaction_type] || ''}`}>
                    {ledgerTypeLabels[entry.transaction_type] || entry.transaction_type}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {entry.description || '—'} · {formatRelative(entry.created_at || '')}
                  </div>
                </div>
                <div className="text-right">
                  <div className={`text-sm font-semibold tabular ${entry.amount >= 0 ? 'text-emerald-400' : ''}`}>
                    {entry.amount >= 0 ? '+' : ''}
                    {formatCvx(entry.amount)}
                  </div>
                  <div className="text-[11px] text-muted-foreground tabular">bal {formatCvx(entry.balance_after)}</div>
                </div>
              </div>
            ))
          )}
        </GlassCard>
        <div className="mt-3 flex justify-center">
          <Button asChild variant="outline" size="sm">
            <Link to="/earn">Earn more CVX</Link>
          </Button>
        </div>
      </div>
    </div>
  )
}
