import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { api } from '@/lib/api'
import type { TemplateOut } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { SkeletonGrid } from '@/components/shared/skeleton'
import { ErrorState } from '@/components/shared/error-state'

export function TemplatesPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['templates'],
    queryFn: () => api.get<TemplateOut[]>('/servers/templates'),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-6">
      <PageHeader
        title="Server Templates"
        description="Pre-configured Minecraft software stacks"
      />
      {isLoading ? (
        <SkeletonGrid count={4} />
      ) : !data || data.length === 0 ? (
        <div className="rounded-xl surface p-8 text-center text-sm text-muted-foreground">
          No templates configured yet.
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((t) => (
            <Card key={t.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-400/10 text-cyan-300">
                      <Sparkles className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold">{t.name}</div>
                      <div className="text-xs text-muted-foreground">{t.software}</div>
                    </div>
                  </div>
                  <Badge variant={t.enabled ? 'success' : 'muted'}>{t.enabled ? 'Active' : 'Disabled'}</Badge>
                </div>
                {t.versions.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {t.versions.map((v) => (
                      <span
                        key={v}
                        className="rounded-md border border-border bg-muted/50 px-2 py-0.5 font-mono text-[11px] text-muted-foreground"
                      >
                        {v}
                      </span>
                    ))}
                  </div>
                )}
                <Button asChild variant="outline" size="sm" className="mt-4 w-full">
                  <Link to="/minecraft/new">Use this template</Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
