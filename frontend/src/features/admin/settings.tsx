import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Save } from 'lucide-react'
import { api, showError } from '@/lib/api'
import { PageHeader } from '@/components/shared/page-header'
import { ErrorState } from '@/components/shared/error-state'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface SettingItem {
  key: string
  label: string
  description?: string
  value: string
  kind?: string
  section?: string
}

const SECTIONS = ['platform', 'support', 'payouts', 'security']

export function AdminSettingsPage() {
  const qc = useQueryClient()
  const [values, setValues] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState<Record<string, string>>({})

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'settings'],
    queryFn: () => api.get<SettingItem[]>('/admin/settings'),
  })

  const save = useMutation({
    mutationFn: () => api.patch('/admin/settings', { settings: values }),
    onSuccess: () => {
      toast.success('Platform settings saved')
      setSaved(values)
      qc.invalidateQueries({ queryKey: ['admin', 'settings'] })
    },
    onError: (err) => showError(err),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  const settings = data || []
  const isDirty = JSON.stringify(values) !== JSON.stringify(saved)

  const sectionLabels: Record<string, string> = {
    platform: 'Platform',
    support: 'Support',
    payouts: 'Payouts',
    security: 'Security',
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Platform Settings"
        description="Global configuration for Cavrix Cloud"
        actions={
          <Button onClick={() => save.mutate()} loading={save.isPending} disabled={!isDirty}>
            <Save className="h-4 w-4" /> Save all
          </Button>
        }
      />

      {isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-48 animate-pulse rounded-xl bg-muted" />)}
        </div>
      ) : settings.length === 0 ? (
        <div className="rounded-xl surface p-12 text-center text-sm text-muted-foreground">No configurable settings exposed yet.</div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {SECTIONS.map((section) => {
            const items = settings.filter((s) => s.section === section)
            if (items.length === 0) return null
            return (
              <Card key={section}>
                <CardHeader>
                  <CardTitle>{sectionLabels[section] || section}</CardTitle>
                  <CardDescription>Applied globally across the platform</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {items.map((item) => (
                    <div key={item.key} className="space-y-1.5">
                      <Label htmlFor={item.key}>{item.label}</Label>
                      <Input
                        id={item.key}
                        value={values[item.key] ?? saved[item.key] ?? item.value}
                        onChange={(e) => setValues((v) => ({ ...v, [item.key]: e.target.value }))}
                      />
                      {item.description && <p className="text-xs text-muted-foreground">{item.description}</p>}
                    </div>
                  ))}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
