import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Save, Coins } from 'lucide-react'
import { api, showError } from '@/lib/api'
import type { CvxRuleOut, Paginated, LedgerEntry } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { StatusBadge } from '@/components/shared/status-badge'
import { Pagination } from '@/components/shared/pagination'
import { ErrorState } from '@/components/shared/error-state'
import { formatCvx, formatRelative } from '@/lib/utils'
import { ledgerTypeColors, ledgerTypeLabels } from '@/lib/labels'

interface SettingField {
  key: string
  label: string
  section: string
  kind: string
}

export function AdminEconomyPage() {
  const qc = useQueryClient()
  const [values, setValues] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState<Record<string, string>>({})
  const [page, setPage] = useState(1)

  const rulesQ = useQuery({
    queryKey: ['admin', 'cvx', 'settings'],
    queryFn: () => api.get<CvxRuleOut[]>('/admin/cvx/settings'),
  })

  const ledgerQ = useQuery({
    queryKey: ['admin', 'cvx', 'ledger', page],
    queryFn: () => api.get<Paginated<LedgerEntry>>(`/admin/cvx/ledger?page=${page}&page_size=25`),
  })

  const saveMutation = useMutation({
    mutationFn: () => api.patch('/admin/cvx/settings', { settings: values }),
    onSuccess: () => {
      toast.success('Economy settings saved')
      setSaved(values)
      qc.invalidateQueries({ queryKey: ['admin', 'cvx', 'settings'] })
      qc.invalidateQueries({ queryKey: ['overview'] })
    },
    onError: (err) => showError(err),
  })

  if (rulesQ.error || ledgerQ.error) {
    return <ErrorState onRetry={() => { rulesQ.refetch(); ledgerQ.refetch() }} />
  }

  const rules = rulesQ.data || []
  const isDirty = JSON.stringify(values) !== JSON.stringify(saved)

  const sections = ['cvx', 'task', 'server', 'referral']

  return (
    <div className="space-y-6">
      <PageHeader
        title="CVX Economy"
        description="Control the internal credit system, limits, and prices"
        actions={
          <Button onClick={() => saveMutation.mutate()} loading={saveMutation.isPending} disabled={!isDirty}>
            <Save className="h-4 w-4" /> Save all
          </Button>
        }
      />

      <Tabs defaultValue="settings">
        <TabsList>
          <TabsTrigger value="settings">Settings</TabsTrigger>
          <TabsTrigger value="ledger">Ledger</TabsTrigger>
        </TabsList>

        <TabsContent value="settings" className="mt-4">
          {rulesQ.isLoading ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-64 animate-pulse rounded-xl bg-muted" />
              ))}
            </div>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {sections.map((section) => {
                const fields = rules.filter((r) => r.section === section)
                if (fields.length === 0) return null
                const sectionTitle = { cvx: 'CVX Credits', task: 'Tasks & Rewards', server: 'Servers & Pricing', referral: 'Referrals' }[section]
                return (
                  <Card key={section}>
                    <CardHeader>
                      <CardTitle>{sectionTitle}</CardTitle>
                      <CardDescription>Configure from the admin panel — no code changes needed</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {fields.map((f) => (
                        <div key={f.key} className="space-y-1.5">
                          <Label htmlFor={f.key}>{f.label}</Label>
                          <Input
                            id={f.key}
                            value={values[f.key] ?? saved[f.key] ?? f.value}
                            onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                            inputMode={f.kind === 'number' ? 'decimal' : undefined}
                          />
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="ledger" className="mt-4">
          <div className="rounded-xl surface">
            <div className="divide-y divide-border">
              {ledgerQ.isLoading ? (
                <div className="space-y-2 p-4">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} className="h-12 animate-pulse rounded bg-muted" />
                  ))}
                </div>
              ) : !ledgerQ.data || ledgerQ.data.items.length === 0 ? (
                <div className="py-12 text-center text-sm text-muted-foreground">No ledger entries yet.</div>
              ) : (
                ledgerQ.data.items.map((entry) => (
                  <div key={entry.id} className="flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                        <Coins className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div>
                        <div className={`text-sm font-medium ${ledgerTypeColors[entry.transaction_type] || ''}`}>
                          {ledgerTypeLabels[entry.transaction_type] || entry.transaction_type}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {entry.description || '—'} · {formatRelative(entry.created_at || '')}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-sm font-semibold tabular ${entry.amount >= 0 ? 'text-emerald-400' : ''}`}>
                        {entry.amount >= 0 ? '+' : ''}{formatCvx(entry.amount)}
                      </div>
                      <div className="text-[11px] text-muted-foreground tabular">bal {formatCvx(entry.balance_after)}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
          {ledgerQ.data && (
            <Pagination
              className="mt-4"
              page={ledgerQ.data.page}
              pages={ledgerQ.data.pages}
              total={ledgerQ.data.total}
              pageSize={ledgerQ.data.page_size}
              onChange={setPage}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
