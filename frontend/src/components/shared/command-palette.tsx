import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  Coins,
  Server,
  Gift,
  Settings,
  LifeBuoy,
  Terminal,
  Wallet,
  Plus,
} from 'lucide-react'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { ServerOut } from '@/types'

interface Command {
  id: string
  label: string
  hint?: string
  icon: React.ComponentType<{ className?: string }>
  action: () => void
}

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
}) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: servers } = useQuery({
    queryKey: ['servers', 'list'],
    queryFn: () => api.get<ServerOut[]>('/servers'),
    enabled: open,
  })

  const commands = useMemo<Command[]>(() => {
    const base: Command[] = [
      { id: 'earn', label: 'Earn CVX', hint: 'Tasks & offers', icon: Coins, action: () => navigate('/earn') },
      { id: 'create', label: 'Create server', hint: 'Claim a Minecraft server', icon: Plus, action: () => navigate('/minecraft/new') },
      { id: 'wallet', label: 'Open wallet', hint: 'CVX balance & ledger', icon: Wallet, action: () => navigate('/rewards') },
      { id: 'servers', label: 'My servers', icon: Server, action: () => navigate('/minecraft') },
      { id: 'rewards', label: 'Rewards & upgrades', icon: Gift, action: () => navigate('/rewards') },
      { id: 'console', label: 'Open console', hint: 'First server', icon: Terminal, action: () => {
          if (servers?.length) navigate(`/minecraft/${servers[0].id}/console`)
        } },
      { id: 'settings', label: 'Open settings', icon: Settings, action: () => navigate('/settings') },
      { id: 'support', label: 'Open support', icon: LifeBuoy, action: () => navigate('/support') },
    ]
    if (servers?.length) {
      servers.forEach((s) => {
        base.push({
          id: `server-${s.id}`,
          label: s.name,
          hint: 'Server',
          icon: Server,
          action: () => navigate(`/minecraft/${s.id}`),
        })
      })
    }
    return base
  }, [navigate, servers])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return commands.slice(0, 8)
    return commands
      .filter((c) => c.label.toLowerCase().includes(q) || (c.hint || '').toLowerCase().includes(q))
      .slice(0, 8)
  }, [commands, query])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="top-[15%] translate-y-0 gap-0 p-0 sm:max-w-xl">
        <div className="flex items-center gap-3 border-b border-border px-4 py-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Input
            ref={inputRef}
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && filtered[0]) {
                filtered[0].action()
                onOpenChange(false)
              }
            }}
            placeholder="Search servers, tasks, actions…"
            className="border-0 bg-transparent p-0 shadow-none focus-visible:ring-0"
          />
        </div>
        <div className="max-h-[320px] overflow-y-auto p-2">
          {filtered.length === 0 && (
            <div className="py-8 text-center text-sm text-muted-foreground">No results for “{query}”</div>
          )}
          {filtered.map((c) => (
            <button
              key={c.id}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-accent"
              onClick={() => {
                c.action()
                onOpenChange(false)
              }}
            >
              <c.icon className="h-4 w-4 text-muted-foreground" />
              <span className="flex-1">{c.label}</span>
              {c.hint && <span className="text-xs text-muted-foreground">{c.hint}</span>}
            </button>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
