import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { UpgradePriceOut, ServerOut } from '@/types'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CvxBadge } from '@/components/shared/cvx-badge'
import { Badge } from '@/components/ui/badge'
import { SkeletonCard } from '@/components/shared/skeleton'
import { ErrorState } from '@/components/shared/error-state'
import { ArrowUpCircle, Cpu, Database, HardDrive, Boxes, Gauge } from 'lucide-react'
import { Link } from 'react-router-dom'

const typeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  ram: Database,
  cpu: Cpu,
  disk: HardDrive,
  backup: Boxes,
  allocation: Gauge,
}

export function UpgradesPage() {
  const pricesQ = useQuery({
    queryKey: ['upgrade-prices'],
    queryFn: () => api.get<UpgradePriceOut[]>('/servers/upgrades/prices'),
  })
  const serversQ = useQuery({
    queryKey: ['servers', 'list'],
    queryFn: () => api.get<ServerOut[]>('/servers'),
  })

  if (pricesQ.error || serversQ.error) {
    return <ErrorState onRetry={() => { pricesQ.refetch(); serversQ.refetch() }} />
  }

  const hasServers = (serversQ.data?.length || 0) > 0

  if (pricesQ.isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    )
  }

  const prices = (pricesQ.data || []).filter((p) => p.enabled)

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <ArrowUpCircle className="h-4 w-4 text-cyan-400" />
        Boost your server — upgrade RAM, CPU, storage and more with CVX.
      </div>

      {!hasServers && (
        <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 p-4 text-sm">
          You need an active server to buy upgrades.{' '}
          <Link to="/minecraft" className="text-primary underline">
            View your servers
          </Link>
        </div>
      )}

      {prices.length === 0 ? (
        <div className="rounded-xl surface p-8 text-center text-sm text-muted-foreground">
          Upgrade pricing is being configured by the admin.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {prices.map((p) => {
            const Icon = typeIcons[p.upgrade_type] || Gauge
            return (
              <Card key={p.upgrade_type}>
                <CardHeader className="flex-row items-center justify-between space-y-0 p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-400/10 text-cyan-300">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold">{p.label}</div>
                      <div className="text-xs text-muted-foreground">
                        +{p.unit_size} {p.unit} per purchase
                      </div>
                    </div>
                  </div>
                  <Badge variant="info">{p.upgrade_type}</Badge>
                </CardHeader>
                <CardContent className="flex items-center justify-between p-4 pt-0">
                  <CvxBadge value={p.cvx_cost} />
                  <Button asChild size="sm" disabled={!hasServers}>
                    <Link to="/minecraft">Upgrade</Link>
                  </Button>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
