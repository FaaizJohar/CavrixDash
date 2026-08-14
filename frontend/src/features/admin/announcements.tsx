import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Megaphone, Plus, Save, Trash2 } from 'lucide-react'
import { api, showError } from '@/lib/api'
import type { Paginated, AnnouncementOut } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { ErrorState } from '@/components/shared/error-state'
import { Pagination } from '@/components/shared/pagination'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatDate } from '@/lib/utils'

interface AnnouncementDraft {
  id?: string
  title: string
  message: string
  audience: string
  priority: string
}

const emptyDraft: AnnouncementDraft = { title: '', message: '', audience: 'all', priority: 'normal' }

export function AdminAnnouncementsPage() {
  const [page, setPage] = useState(1)
  const [draft, setDraft] = useState<AnnouncementDraft | null>(null)
  const qc = useQueryClient()

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'announcements', page],
    queryFn: () => api.get<Paginated<AnnouncementOut>>(`/admin/announcements?page=${page}&page_size=25`),
  })

  const create = useMutation({
    mutationFn: () => api.post('/admin/announcements', draft),
    onSuccess: () => {
      toast.success('Announcement published')
      setDraft(null)
      qc.invalidateQueries({ queryKey: ['admin', 'announcements'] })
      qc.invalidateQueries({ queryKey: ['notifications'] })
    },
    onError: (err) => showError(err),
  })

  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => api.patch(`/admin/announcements/${id}`, { enabled }),
    onSuccess: () => {
      toast.success('Announcement updated')
      qc.invalidateQueries({ queryKey: ['admin', 'announcements'] })
      qc.invalidateQueries({ queryKey: ['notifications'] })
    },
    onError: (err) => showError(err),
  })

  const remove = useMutation({
    mutationFn: (id: string) => api.delete(`/admin/announcements/${id}`),
    onSuccess: () => {
      toast.success('Announcement deleted')
      qc.invalidateQueries({ queryKey: ['admin', 'announcements'] })
    },
    onError: (err) => showError(err),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-4">
      <PageHeader
        title="Announcements"
        description="Broadcast to all users or targeted audiences"
        actions={
          <Button onClick={() => setDraft({ ...emptyDraft })}>
            <Plus className="h-4 w-4" /> New announcement
          </Button>
        }
      />

      <div className="rounded-xl surface">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Audience</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Active</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 6 }).map((__, j) => (
                    <TableCell key={j}><div className="h-4 animate-pulse rounded bg-muted" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : !data || data.items.length === 0 ? (
              <TableRow><TableCell colSpan={6} className="py-10 text-center text-muted-foreground">No announcements yet.</TableCell></TableRow>
            ) : (
              data.items.map((a) => (
                <TableRow key={a.id}>
                  <TableCell>
                    <div className="flex items-center gap-2 font-medium">
                      <Megaphone className="h-4 w-4 text-muted-foreground" />
                      <span className="truncate">{a.title}</span>
                    </div>
                    <div className="max-w-md truncate text-xs text-muted-foreground">{a.message}</div>
                  </TableCell>
                  <TableCell className="text-xs">{a.audience}</TableCell>
                  <TableCell>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      a.priority === 'urgent' ? 'bg-rose-400/10 text-rose-300' :
                      a.priority === 'important' ? 'bg-amber-400/10 text-amber-300' : 'bg-muted text-muted-foreground'
                    }`}>{a.priority}</span>
                  </TableCell>
                  <TableCell>
                    <span className={`status-dot ${a.enabled ? 'bg-emerald-400' : 'bg-muted'}`} />
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{formatDate(a.created_at || '')}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1.5">
                      <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => toggle.mutate({ id: a.id, enabled: !a.enabled })}>
                        {a.enabled ? 'Disable' : 'Enable'}
                      </Button>
                      <Button size="sm" variant="ghost" className="h-7 text-xs text-rose-400" onClick={() => remove.mutate(a.id)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onChange={setPage} />}

      <Dialog open={!!draft} onOpenChange={(open) => !open && setDraft(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{draft?.id ? 'Edit announcement' : 'New announcement'}</DialogTitle>
            <DialogDescription>Broadcast a message to Cavrix Cloud users</DialogDescription>
          </DialogHeader>
          {draft && (
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="title">Title</Label>
                <Input id="title" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="message">Message</Label>
                <textarea
                  id="message"
                  className="flex min-h-[90px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={draft.message}
                  onChange={(e) => setDraft({ ...draft, message: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Audience</Label>
                  <Select value={draft.audience} onValueChange={(v) => setDraft({ ...draft, audience: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All users</SelectItem>
                      <SelectItem value="active">Active users</SelectItem>
                      <SelectItem value="admin">Admins</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Priority</Label>
                  <Select value={draft.priority} onValueChange={(v) => setDraft({ ...draft, priority: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="normal">Normal</SelectItem>
                      <SelectItem value="important">Important</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDraft(null)}>Cancel</Button>
            <Button onClick={() => create.mutate()} loading={create.isPending}>
              <Save className="h-4 w-4" /> Publish
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
