import { Bell, CheckCheck } from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, showError } from '@/lib/api'
import type { NotificationOut, Paginated } from '@/types'
import { formatRelative } from '@/lib/utils'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'

const priorityDot: Record<string, string> = {
  high: 'bg-red-400',
  urgent: 'bg-red-500',
  critical: 'bg-red-500',
  normal: 'bg-cavrix-400',
  low: 'bg-slate-400',
}

export function NotificationCenter() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => api.get<Paginated<NotificationOut>>('/notifications'),
    refetchInterval: 60_000,
  })

  const list = data?.items ?? []
  const unread = list.filter((n) => !n.read).length

  const markRead = useMutation({
    mutationFn: () => api.post('/notifications/read'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
    onError: (e) => showError(e),
  })

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unread > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-white">
              {unread > 9 ? '9+' : unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-sm font-semibold">Notifications</span>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1 text-xs"
            disabled={unread === 0}
            onClick={() => markRead.mutate()}
          >
            <CheckCheck className="h-3.5 w-3.5" /> Mark all read
          </Button>
        </div>
        <ScrollArea className="max-h-[360px]">
          {!isLoading && list.length === 0 && (
            <div className="py-10 text-center text-sm text-muted-foreground">No notifications yet</div>
          )}
          {list.map((n) => (
            <div
              key={n.id}
              className={cn(
                'flex gap-3 border-b border-border/50 px-4 py-3',
                !n.read && 'bg-primary/5',
              )}
            >
              <span className={cn('mt-1.5 h-2 w-2 shrink-0 rounded-full', priorityDot[n.priority] || 'bg-slate-400')} />
              <div className="min-w-0">
                <div className={cn('text-sm', !n.read && 'font-semibold')}>{n.title}</div>
                {n.body && <div className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{n.body}</div>}
                <div className="mt-1 text-[11px] text-muted-foreground/70">{formatRelative(n.created_at || '')}</div>
              </div>
            </div>
          ))}
        </ScrollArea>
      </PopoverContent>
    </Popover>
  )
}
