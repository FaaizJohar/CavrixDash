import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Paginated, TaskOut } from '@/types'
import { Card, CardContent } from '@/components/ui/card'
import { StatusBadge } from '@/components/shared/status-badge'
import { CvxBadge } from '@/components/shared/cvx-badge'
import { EmptyState } from '@/components/shared/empty-state'
import { ErrorState } from '@/components/shared/error-state'
import { SkeletonCard } from '@/components/shared/skeleton'
import { ListChecks, RefreshCcw } from 'lucide-react'
import { formatRelative } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useState } from 'react'

export function MyTasks() {
  const [page, setPage] = useState(1)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['tasks', page],
    queryFn: () => api.get<Paginated<TaskOut>>(`/tasks?page=${page}&page_size=15`),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  if (isLoading) {
    return (
      <div className="grid gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    )
  }

  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        icon={ListChecks}
        title="No tasks yet"
        description="Start a task from the Tasks tab and track its status here."
      />
    )
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-3">
        {data.items.map((task) => (
          <Card key={task.id}>
            <CardContent className="flex items-center justify-between gap-4 p-4">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{task.offer_title}</div>
                <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{task.provider_code}</span>
                  <span>·</span>
                  <span className="capitalize">{task.category}</span>
                  <span>·</span>
                  <span>{formatRelative(task.created_at || '')}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <CvxBadge value={task.reward_offered} />
                <StatusBadge status={task.status} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      {data.pages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            Page {data.page} of {data.pages}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
      <div className="flex justify-center pt-2">
        <Button variant="ghost" size="sm" onClick={() => refetch()}>
          <RefreshCcw className="h-3.5 w-3.5" /> Refresh status
        </Button>
      </div>
    </div>
  )
}
