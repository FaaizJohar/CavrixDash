import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Cpu, Database, HardDrive, Shield, Timer } from 'lucide-react'
import { api } from '@/lib/api'
import type { PlanOut } from '@/types'
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CvxBadge } from '@/components/shared/cvx-badge'
import { Badge } from '@/components/ui/badge'
import { SkeletonGrid } from '@/components/shared/skeleton'
import { ErrorState } from '@/components/shared/error-state'
import { formatNumber } from '@/lib/utils'

export function ServersRewardPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['plans'],
    queryFn: () => api.get<PlanOut[]>('/servers/plans'),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  const plans = (data || []).filter((p) => p.status === 'active')

  if (isLoading) return <SkeletonGrid count={3} />

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Shield className="h-4 w-4 text-emerald-400" />
        Free Minecraft servers, powered by Pterodactyl. One-time CVX claim, renewable.
      </div>

      {plans.length === 0 ? (
        <div className="rounded-xl surface p-8 text-center text-sm text-muted-foreground">
          Server plans are being configured. Check back soon.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {plans.map((plan) => (
            <Card key={plan.id} className="flex flex-col">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-base font-semibold">{plan.name}</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">{plan.description}</div>
                  </div>
                  {plan.region && <Badge variant="muted">{plan.region}</Badge>}
                </div>
              </CardHeader>
              <CardContent className="flex-1 space-y-3">
                <div className="grid grid-cols-3 gap-2">
                  <div className="rounded-lg border border-border bg-muted/40 p-2.5 text-center">
                    <Cpu className="mx-auto h-4 w-4 text-cavrix-400" />
                    <div className="mt-1 text-sm font-semibold tabular">{plan.cpu}</div>
                    <div className="text-[11px] text-muted-foreground">CPU</div>
                  </div>
                  <div className="rounded-lg border border-border bg-muted/40 p-2.5 text-center">
                    <Database className="mx-auto h-4 w-4 text-violet-400" />
                    <div className="mt-1 text-sm font-semibold tabular">
                      {plan.ram_mb >= 1024 ? `${plan.ram_mb / 1024} GB` : `${plan.ram_mb} MB`}
                    </div>
                    <div className="text-[11px] text-muted-foreground">RAM</div>
                  </div>
                  <div className="rounded-lg border border-border bg-muted/40 p-2.5 text-center">
                    <HardDrive className="mx-auto h-4 w-4 text-emerald-400" />
                    <div className="mt-1 text-sm font-semibold tabular">
                      {plan.disk_mb >= 1024 ? `${plan.disk_mb / 1024} GB` : `${plan.disk_mb} MB`}
                    </div>
                    <div className="text-[11px] text-muted-foreground">Disk</div>
                  </div>
                </div>
                <div className="space-y-1.5 text-xs text-muted-foreground">
                  <div className="flex justify-between">
                    <span>Backups</span>
                    <span className="tabular">{formatNumber(plan.backups)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Databases</span>
                    <span className="tabular">{formatNumber(plan.databases)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Allocations</span>
                    <span className="tabular">{formatNumber(plan.allocations)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="flex items-center gap-1">
                      <Timer className="h-3 w-3" /> Duration
                    </span>
                    <span className="tabular">{plan.duration_days} days</span>
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex items-center justify-between">
                <CvxBadge value={plan.cvx_cost} />
                <Button asChild size="sm">
                  <Link to={`/minecraft/new?plan=${plan.id}`}>Claim</Link>
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
