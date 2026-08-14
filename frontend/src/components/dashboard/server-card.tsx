import { motion } from 'framer-motion'
import { Cpu, Database, HardDrive, MapPin, MoreHorizontal, Terminal } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { StatusBadge } from '@/components/shared/status-badge'
import { ProgressBar } from '@/components/shared/progress-bar'
import { formatBytes } from '@/lib/utils'
import type { ServerOut } from '@/types'

interface ServerCardProps {
  server: ServerOut
  onOpen: (id: string) => void
  onConsole?: (id: string) => void
  live?: boolean
}

export function ServerCard({ server, onOpen, onConsole, live = true }: ServerCardProps) {
  const memoryPct = server.live?.memory_percent ?? null
  const cpuPct = server.live?.cpu_percent ?? null
  const diskPct = server.live?.disk_percent ?? null
  const online = server.live?.online ?? server.status === 'running'

  return (
    <motion.div whileHover={{ y: -2 }} transition={{ duration: 0.15 }}>
      <Card className="h-full overflow-hidden">
        <CardHeader className="flex-row items-start justify-between space-y-0 p-4 pb-0">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="truncate text-sm font-semibold">{server.name}</h3>
              <StatusBadge status={online ? 'online' : 'offline'} />
            </div>
            <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
              <MapPin className="h-3 w-3" /> {server.region}
              <span>·</span>
              <span className="font-mono">
                {server.ip || '—'}:{server.port || '—'}
              </span>
            </div>
          </div>
          <Button variant="ghost" size="iconSm" onClick={() => onOpen(server.id)}>
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent className="p-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-border bg-muted/40 p-2.5">
              <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                <Cpu className="h-3 w-3" /> CPU
              </div>
              <div className="mt-1 text-sm font-semibold tabular">{server.cpu}</div>
              {live && cpuPct !== null && (
                <ProgressBar value={cpuPct} className="mt-2 h-1" indicatorClassName="bg-cyan-400" />
              )}
            </div>
            <div className="rounded-lg border border-border bg-muted/40 p-2.5">
              <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                <Database className="h-3 w-3" /> RAM
              </div>
              <div className="mt-1 text-sm font-semibold tabular">
                {server.ram_mb >= 1024 ? `${server.ram_mb / 1024} GB` : `${server.ram_mb} MB`}
              </div>
              {live && memoryPct !== null && (
                <ProgressBar value={memoryPct} className="mt-2 h-1" indicatorClassName="bg-violet-400" />
              )}
            </div>
            <div className="rounded-lg border border-border bg-muted/40 p-2.5">
              <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                <HardDrive className="h-3 w-3" /> Disk
              </div>
              <div className="mt-1 text-sm font-semibold tabular">
                {server.disk_mb >= 1024 ? `${server.disk_mb / 1024} GB` : `${server.disk_mb} MB`}
              </div>
              {live && diskPct !== null && (
                <ProgressBar value={diskPct} className="mt-2 h-1" indicatorClassName="bg-emerald-400" />
              )}
            </div>
          </div>
          {onConsole && (
            <Button variant="outline" size="sm" className="mt-3 w-full" onClick={() => onConsole(server.id)}>
              <Terminal className="h-4 w-4" /> Open console
            </Button>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}
