import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Eye, EyeOff, KeyRound, Save, ShieldCheck } from 'lucide-react'
import { api, ApiError, showError } from '@/lib/api'
import { PageHeader } from '@/components/shared/page-header'
import { ErrorState } from '@/components/shared/error-state'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { StepUpDialog, useStepUp } from '@/components/shared/step-up'

interface SecretRow {
  key: string
  label: string
  masked: string
  set: boolean
  last_rotated_at?: string | null
}

export function AdminSecretsPage() {
  const qc = useQueryClient()
  const stepUp = useStepUp()
  const [values, setValues] = useState<Record<string, string>>({})
  const [visible, setVisible] = useState<Record<string, boolean>>({})
  const [confirmed, setConfirmed] = useState(false)
  const [token, setToken] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'secrets'],
    queryFn: () =>
      api.get<SecretRow[]>('/admin/secrets', {
        headers: token ? ({ 'X-Step-Up-Token': token } as Record<string, string>) : undefined,
      }),
    enabled: confirmed,
  })

  useEffect(() => {
    if (error instanceof ApiError && error.code === 'STEP_UP_REQUIRED') {
      setConfirmed(false)
      setToken(null)
    }
  }, [error])

  const reveal = () => {
    stepUp.confirm(async (t) => {
      setToken(t)
      setConfirmed(true)
    })
  }

  const save = async () => {
    stepUp.confirm(async (t) => {
      setSaving(true)
      try {
        await api.post('/admin/secrets', values, {
          headers: { 'X-Step-Up-Token': t } as Record<string, string>,
        })
        toast.success('Secrets updated')
        setValues({})
        qc.invalidateQueries({ queryKey: ['admin', 'secrets'] })
      } catch (err) {
        showError(err)
      } finally {
        setSaving(false)
      }
    })
  }

  if (!confirmed) {
    return (
      <div className="space-y-6">
        <PageHeader title="Secrets Management" description="Encrypted API keys and credentials. Values are stored encrypted at rest." />
        <div className="rounded-xl surface flex flex-col items-center gap-4 p-12 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <h3 className="font-semibold">Identity confirmation required</h3>
            <p className="mt-1 max-w-md text-sm text-muted-foreground">
              Revealing provider credentials and API keys is a sensitive action. Verify your identity to continue.
            </p>
          </div>
          <Button onClick={reveal} loading={stepUp.submitting}>
            <ShieldCheck className="h-4 w-4" /> Verify to view secrets
          </Button>
        </div>
        <StepUpDialog handle={stepUp} />
      </div>
    )
  }

  if (error) return <ErrorState onRetry={() => refetch()} />

  const secrets = data || []
  const anyDirty = Object.keys(values).some((k) => values[k].trim() !== '')

  return (
    <div className="space-y-6">
      <PageHeader
        title="Secrets Management"
        description="Encrypted API keys and credentials. Values are stored encrypted at rest."
        actions={
          <Button onClick={save} loading={saving} disabled={!anyDirty}>
            <Save className="h-4 w-4" /> Save new values
          </Button>
        }
      />

      <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-sm text-amber-300">
        <KeyRound className="mr-1.5 inline h-4 w-4" />
        Paste a value to rotate that secret. Blank fields leave existing secrets unchanged.
      </div>

      {isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-xl bg-muted" />)}
        </div>
      ) : secrets.length === 0 ? (
        <div className="rounded-xl surface p-12 text-center text-sm text-muted-foreground">No secrets configured.</div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {secrets.map((s) => (
            <Card key={s.key}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{s.label}</CardTitle>
                  {s.set && <Badge variant="outline" className="text-emerald-400">Set</Badge>}
                </div>
                <CardDescription className="font-mono text-xs">{s.key}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="relative">
                  <Input
                    type={visible[s.key] ? 'text' : 'password'}
                    placeholder={s.set ? s.masked : 'Not configured yet'}
                    value={values[s.key] ?? ''}
                    onChange={(e) => setValues((v) => ({ ...v, [s.key]: e.target.value }))}
                    className="pr-9 font-mono"
                  />
                  <button
                    type="button"
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    onClick={() => setVisible((v) => ({ ...v, [s.key]: !v[s.key] }))}
                    aria-label="Toggle visibility"
                  >
                    {visible[s.key] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {s.last_rotated_at && (
                  <p className="text-xs text-muted-foreground">
                    Last rotated {new Date(s.last_rotated_at).toLocaleString()}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      <StepUpDialog handle={stepUp} />
    </div>
  )
}
