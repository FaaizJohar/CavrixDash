import { useCallback, useEffect, useRef, useState } from 'react'
import { Send, Search, Trash2, Terminal, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { getWsUrl, tokenStore } from '@/lib/api'
import { cn } from '@/lib/utils'

interface ConsoleProps {
  serverId: string
}

export function ServerConsole({ serverId }: ConsoleProps) {
  const [lines, setLines] = useState<string[]>([])
  const [connected, setConnected] = useState(false)
  const [command, setCommand] = useState('')
  const [search, setSearch] = useState('')
  const [autoscroll, setAutoscroll] = useState(true)
  const [history, setHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const wsRef = useRef<WebSocket | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const append = useCallback((text: string) => {
    setLines((prev) => {
      const next = [...prev, text]
      return next.length > 2000 ? next.slice(next.length - 2000) : next
    })
  }, [])

  useEffect(() => {
    const access = tokenStore.access
    if (!access) return
    const url = getWsUrl(`/ws/console/${serverId}`) + `?token=${encodeURIComponent(access)}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onerror = () => setConnected(false)
    ws.onmessage = (e) => {
      let text = ''
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'console' && data.line) text = data.line
        else if (data.type === 'auth') text = data.message || ''
        else if (typeof data === 'string') text = data
        else if (data.message) text = data.message
      } catch {
        text = e.data as string
      }
      if (text) append(text)
    }

    return () => ws.close()
  }, [serverId, append])

  useEffect(() => {
    if (autoscroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [lines, autoscroll])

  const sendCommand = () => {
    const cmd = command.trim()
    if (!cmd || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'command', command: cmd }))
    append(`> ${cmd}`)
    setHistory((h) => [cmd, ...h.filter((x) => x !== cmd)].slice(0, 50))
    setHistoryIndex(-1)
    setCommand('')
  }

  const filtered = search
    ? lines.filter((l) => l.toLowerCase().includes(search.toLowerCase()))
    : lines

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-2 rounded-lg border border-border px-2.5 py-1.5 text-xs">
          <span className={cn('status-dot', connected ? 'bg-emerald-400' : 'bg-slate-500')} />
          <span className={connected ? 'text-emerald-400' : 'text-muted-foreground'}>
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <div className="relative flex-1 min-w-[140px] max-w-xs">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search console…"
            className="h-8 pl-8 text-xs"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={autoscroll}
            onChange={(e) => setAutoscroll(e.target.checked)}
            className="h-3.5 w-3.5 accent-primary"
          />
          Auto-scroll
        </label>
        <Button
          variant="ghost"
          size="sm"
          className="h-8"
          onClick={() => {
            setLines([])
            setSearch('')
          }}
        >
          <Trash2 className="h-3.5 w-3.5" /> Clear
        </Button>
      </div>

      {/* Console output */}
      <div className="overflow-hidden rounded-lg border border-border bg-black/60">
        <ScrollArea className="h-[420px]">
          <div ref={scrollRef} className="p-3 font-mono text-xs leading-relaxed">
            {filtered.length === 0 && (
              <div className="flex flex-col items-center gap-2 py-10 text-muted-foreground">
                <Terminal className="h-6 w-6" />
                <span className="text-sm">Console output will appear here.</span>
                {!connected && <span className="text-xs">Waiting for connection…</span>}
              </div>
            )}
            {filtered.map((line, i) => (
              <div key={i} className="whitespace-pre-wrap break-words">
                <span className="text-emerald-400">$</span> <span className="text-slate-300">{line}</span>
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Command input */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Terminal className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') sendCommand()
              else if (e.key === 'ArrowUp') {
                e.preventDefault()
                const idx = historyIndex + 1
                if (idx < history.length) {
                  setHistoryIndex(idx)
                  setCommand(history[idx])
                }
              } else if (e.key === 'ArrowDown') {
                e.preventDefault()
                const idx = historyIndex - 1
                if (idx >= 0) {
                  setHistoryIndex(idx)
                  setCommand(history[idx])
                } else {
                  setHistoryIndex(-1)
                  setCommand('')
                }
              }
            }}
            placeholder="Type a command, e.g. /say hello"
            className="h-10 pl-9 font-mono"
            disabled={!connected}
          />
        </div>
        <Button onClick={sendCommand} disabled={!connected || !command.trim()}>
          <Send className="h-4 w-4" /> Send
        </Button>
      </div>
    </div>
  )
}
