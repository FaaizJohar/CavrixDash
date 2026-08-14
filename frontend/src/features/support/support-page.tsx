import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { LifeBuoy, Plus, MessageSquare } from 'lucide-react'
import { api, showError } from '@/lib/api'
import type { Paginated, TicketOut, TicketDetail } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { GlassCard } from '@/components/shared/glass-card'
import { StatusBadge } from '@/components/shared/status-badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { EmptyState } from '@/components/shared/empty-state'
import { ErrorState } from '@/components/shared/error-state'
import { formatRelative } from '@/lib/utils'

const schema = z.object({
  subject: z.string().min(3, 'Add a short subject').max(120),
  message: z.string().min(10, 'Describe your issue (at least 10 characters)'),
})

type FormData = z.infer<typeof schema>

export function SupportPage() {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [category, setCategory] = useState('general')
  const [activeTicket, setActiveTicket] = useState<string | null>(null)
  const [reply, setReply] = useState('')

  const ticketsQ = useQuery({
    queryKey: ['support-tickets'],
    queryFn: () => api.get<Paginated<TicketOut>>('/support/tickets?page=1&page_size=25'),
  })

  const detailQ = useQuery({
    queryKey: ['support-tickets', activeTicket],
    queryFn: () => api.get<TicketDetail>(`/support/tickets/${activeTicket}`),
    enabled: !!activeTicket,
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const createMutation = useMutation({
    mutationFn: (data: FormData) =>
      api.post('/support/tickets', { subject: data.subject, category, message: data.message }),
    onSuccess: () => {
      toast.success('Ticket opened')
      setOpen(false)
      reset()
      qc.invalidateQueries({ queryKey: ['support-tickets'] })
    },
    onError: (err) => showError(err),
  })

  const replyMutation = useMutation({
    mutationFn: () => api.post(`/support/tickets/${activeTicket}/messages`, { body: reply }),
    onSuccess: () => {
      toast.success('Reply sent')
      setReply('')
      qc.invalidateQueries({ queryKey: ['support-tickets', activeTicket] })
    },
    onError: (err) => showError(err),
  })

  const tickets = ticketsQ.data?.items || []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Support"
        description="Get help with your account, servers, or rewards"
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus className="h-4 w-4" /> New ticket
          </Button>
        }
      />

      {ticketsQ.error ? (
        <ErrorState onRetry={() => ticketsQ.refetch()} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Ticket list */}
          <GlassCard className="divide-y divide-border/50">
            {ticketsQ.isLoading ? (
              <div className="space-y-2 p-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
                ))}
              </div>
            ) : tickets.length === 0 ? (
              <EmptyState
                icon={LifeBuoy}
                title="No tickets"
                description="Open a ticket and we'll help you out."
              />
            ) : (
              tickets.map((t) => (
                <button
                  key={t.id}
                  className={`flex w-full items-center justify-between px-4 py-3.5 text-left transition-colors hover:bg-accent/50 ${
                    activeTicket === t.id ? 'bg-accent/60' : ''
                  }`}
                  onClick={() => setActiveTicket(t.id)}
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">{t.subject}</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {t.category} · {formatRelative(t.updated_at || t.created_at || '')}
                    </div>
                  </div>
                  <StatusBadge status={t.status} />
                </button>
              ))
            )}
          </GlassCard>

          {/* Ticket detail */}
          <GlassCard className="flex min-h-[320px] flex-col p-5">
            {!activeTicket ? (
              <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
                <LifeBuoy className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Select a ticket to view the conversation.</p>
              </div>
            ) : detailQ.isLoading ? (
              <div className="flex-1 space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="h-14 animate-pulse rounded-lg bg-muted" />
                ))}
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <div>
                    <div className="text-sm font-semibold">{detailQ.data?.subject}</div>
                    <div className="text-xs text-muted-foreground capitalize">{detailQ.data?.category}</div>
                  </div>
                  <StatusBadge status={detailQ.data?.status || 'open'} />
                </div>
                <div className="flex-1 space-y-3 py-4">
                  {(detailQ.data?.messages || []).map((m, i) => {
                    const msg = m as { body?: string; sender?: string; created_at?: string }
                    const isUser = msg.sender === 'user'
                    return (
                      <div key={i} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                        <div
                          className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
                            isUser ? 'bg-primary/15 text-foreground' : 'bg-muted/60 text-foreground'
                          }`}
                        >
                          <div className="whitespace-pre-wrap">{msg.body}</div>
                          <div className="mt-1 text-[10px] text-muted-foreground">
                            {formatRelative(msg.created_at || '')}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
                {detailQ.data?.status === 'open' && (
                  <div className="flex gap-2 border-t border-border pt-3">
                    <Input
                      placeholder="Write a reply…"
                      value={reply}
                      onChange={(e) => setReply(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault()
                          if (reply.trim()) replyMutation.mutate()
                        }
                      }}
                    />
                    <Button
                      size="icon"
                      disabled={!reply.trim() || replyMutation.isPending}
                      onClick={() => replyMutation.mutate()}
                    >
                      <MessageSquare className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </>
            )}
          </GlassCard>
        </div>
      )}

      {/* New ticket dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Open a support ticket</DialogTitle>
            <DialogDescription>
              Describe your issue. Support usually responds within 24 hours.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit((d) => createMutation.mutate(d))} className="space-y-4">
            <div className="space-y-2">
              <Label>Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger>
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="general">General</SelectItem>
                  <SelectItem value="account">Account</SelectItem>
                  <SelectItem value="server">Server</SelectItem>
                  <SelectItem value="cvx">CVX / Rewards</SelectItem>
                  <SelectItem value="task">Tasks & Offers</SelectItem>
                  <SelectItem value="payment">Payments</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="subject">Subject</Label>
              <Input id="subject" placeholder="Brief summary" {...register('subject')} />
              {errors.subject && <p className="text-xs text-destructive">{errors.subject.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="message">Message</Label>
              <Textarea id="message" rows={4} placeholder="Describe your issue…" {...register('message')} />
              {errors.message && <p className="text-xs text-destructive">{errors.message.message}</p>}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={isSubmitting}>
                Open ticket
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
