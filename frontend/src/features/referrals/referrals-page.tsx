import { useQuery } from '@tanstack/react-query'
import { Link2, Copy, Users, CheckCircle2, Wallet } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import type { ReferralSummary, ReferralRow, Paginated } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { GlassCard } from '@/components/shared/glass-card'
import { MetricCard } from '@/components/shared/metric-card'
import { StatusBadge } from '@/components/shared/status-badge'
import { ErrorState } from '@/components/shared/error-state'
import { Button } from '@/components/ui/button'
import { CvxBadge } from '@/components/shared/cvx-badge'
import { formatCvx, formatRelative } from '@/lib/utils'

export function ReferralsPage() {
  const summaryQ = useQuery({
    queryKey: ['referrals'],
    queryFn: () => api.get<ReferralSummary>('/referrals'),
  })
  const rowsQ = useQuery({
    queryKey: ['referrals', 'rows'],
    queryFn: () => api.get<Paginated<ReferralRow>>('/referrals/invitees?page=1&page_size=25'),
  })

  if (summaryQ.error || rowsQ.error) {
    return <ErrorState onRetry={() => { summaryQ.refetch(); rowsQ.refetch() }} />
  }

  const summary = summaryQ.data

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success('Copied to clipboard')
    } catch {
      toast.error('Could not copy')
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Referrals"
        description="Invite friends and earn CVX when they join and verify"
      />

      {/* Referral code hero */}
      {summary && (
        <GlassCard className="relative overflow-hidden p-6">
          <div
            className="pointer-events-none absolute inset-0"
            style={{ background: 'radial-gradient(400px 200px at 90% 0%, rgba(59,87,255,0.15), transparent 60%)' }}
          />
          <div className="relative">
            <div className="text-sm font-semibold">Your referral link</div>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="flex flex-1 items-center gap-2 rounded-lg border border-border bg-background/60 px-3 py-2.5">
                <Link2 className="h-4 w-4 shrink-0 text-primary" />
                <span className="truncate font-mono text-sm">{summary.url}</span>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" onClick={() => copy(summary.url)}>
                  <Copy className="h-4 w-4" /> Copy link
                </Button>
                <Button size="sm" onClick={() => copy(summary.code)}>
                  Copy code
                </Button>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
              <Wallet className="h-3.5 w-3.5 text-amber-300" />
              Earn <span className="text-amber-300 font-semibold">{formatCvx(summary.reward)}</span> per verified invite
            </div>
          </div>
        </GlassCard>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <MetricCard label="Total Invited" value={summary?.total_invited ?? null} icon={Users} loading={summaryQ.isLoading} />
        <MetricCard label="Verified" value={summary?.verified ?? null} icon={CheckCircle2} iconClassName="bg-emerald-400/10 text-emerald-300" loading={summaryQ.isLoading} />
        <MetricCard label="Rewarded" value={summary?.rewarded ?? null} icon={Wallet} iconClassName="bg-amber-400/10 text-amber-300" loading={summaryQ.isLoading} />
        <MetricCard label="This Month" value={summary?.referrals_this_month ?? null} sub={summary ? `/ ${summary.max_monthly} limit` : undefined} loading={summaryQ.isLoading} />
        <MetricCard label="Earnings" value={summary ? formatCvx(summary.earnings) : '—'} icon={Wallet} iconClassName="bg-emerald-400/10 text-emerald-300" loading={summaryQ.isLoading} />
      </div>

      {/* Invitees */}
      <div>
        <h3 className="mb-3 text-sm font-semibold">Invited users</h3>
        <GlassCard className="divide-y divide-border/50">
          {rowsQ.isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-11 animate-pulse rounded-md bg-muted" />
              ))}
            </div>
          ) : !rowsQ.data || rowsQ.data.items.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              You haven't invited anyone yet. Share your link to start earning.
            </div>
          ) : (
            rowsQ.data.items.map((row) => (
              <div key={row.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <div className="text-sm font-medium">{row.invitee_email}</div>
                  <div className="text-xs text-muted-foreground">{formatRelative(row.created_at || '')}</div>
                </div>
                <div className="flex items-center gap-3">
                  {row.reward_amount > 0 && <CvxBadge value={row.reward_amount} />}
                  <StatusBadge status={row.status} />
                </div>
              </div>
            ))
          )}
        </GlassCard>
      </div>
    </div>
  )
}
