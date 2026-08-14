import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Server } from 'lucide-react'
import { api } from '@/lib/api'
import type { ServerOut } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { ServerCard } from '@/components/dashboard/server-card'
import { SkeletonGrid } from '@/components/shared/skeleton'
import { ErrorState } from '@/components/shared/error-state'
import { EmptyState } from '@/components/shared/empty-state'
import { Button } from '@/components/ui/button'
import { useNavigate } from 'react-router-dom'

export function MyServersPage() {
  const navigate = useNavigate()
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['servers', 'list'],
    queryFn: () => api.get<ServerOut[]>('/servers'),
    refetchInterval: 30_000,
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Servers"
        description="Your Minecraft servers, managed through Pterodactyl"
        actions={
          <Button asChild>
            <Link to="/minecraft/new">
              <Plus className="h-4 w-4" /> Create server
            </Link>
          </Button>
        }
      />

      {isLoading ? (
        <SkeletonGrid count={3} />
      ) : !data || data.length === 0 ? (
        <EmptyState
          icon={Server}
          title="No servers yet"
          description="Claim your first free Minecraft server using your CVX credits."
          action={
            <Button asChild>
              <Link to="/minecraft/new">
                <Plus className="h-4 w-4" /> Create your first server
              </Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((server) => (
            <ServerCard
              key={server.id}
              server={server}
              onOpen={(id) => navigate(`/minecraft/${id}`)}
              onConsole={(id) => navigate(`/minecraft/${id}/console`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
