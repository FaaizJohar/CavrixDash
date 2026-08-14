import { useMemo, useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { ArrowLeft, ArrowRight, Check, Cpu, Database, HardDrive, Sparkles } from 'lucide-react'
import { api, showError } from '@/lib/api'
import type { PlanOut, RegionOut, TemplateOut, ServerOut } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { CvxBadge } from '@/components/shared/cvx-badge'
import { ProgressBar } from '@/components/shared/progress-bar'
import { SkeletonGrid } from '@/components/shared/skeleton'
import { ErrorState } from '@/components/shared/error-state'
import { cn } from '@/lib/utils'

const schema = z.object({
  server_name: z
    .string()
    .min(3, 'At least 3 characters')
    .max(60)
    .regex(/^[a-zA-Z0-9_-]+$/, 'Letters, numbers, - and _ only'),
})

type FormData = z.infer<typeof schema>

const steps = ['Plan', 'Region', 'Software', 'Details', 'Confirm']

export function CreateServerPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const preselectPlan = params.get('plan') || ''

  const [step, setStep] = useState(0)
  const [planId, setPlanId] = useState(preselectPlan)
  const [region, setRegion] = useState('')
  const [templateId, setTemplateId] = useState('')
  const [version, setVersion] = useState('')

  const plansQ = useQuery({
    queryKey: ['plans'],
    queryFn: () => api.get<PlanOut[]>('/servers/plans'),
  })
  const regionsQ = useQuery({
    queryKey: ['regions'],
    queryFn: () => api.get<RegionOut[]>('/servers/regions'),
  })
  const templatesQ = useQuery({
    queryKey: ['templates'],
    queryFn: () => api.get<TemplateOut[]>('/servers/templates'),
  })

  const plans = (plansQ.data || []).filter((p) => p.status === 'active')
  const regions = (regionsQ.data || []).filter((r) => r.enabled)
  const templates = (templatesQ.data || []).filter((t) => t.enabled)

  const selectedPlan = plans.find((p) => p.id === planId)
  const selectedRegion = regions.find((r) => r.code === region)
  const selectedTemplate = templates.find((t) => t.id === templateId)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const createMutation = useMutation({
    mutationFn: (data: FormData) =>
      api.post<ServerOut>('/servers', {
        plan_id: planId,
        region: region || 'default',
        template_id: templateId || undefined,
        version,
        server_name: data.server_name,
      }),
    onSuccess: (server) => {
      toast.success('Server claimed! Provisioning started.')
      navigate(`/minecraft/${server.id}`, { replace: true })
    },
    onError: (err) => showError(err, 'Failed to create server'),
  })

  const canNext = useMemo(() => {
    if (step === 0) return Boolean(planId)
    if (step === 1) return Boolean(region)
    if (step === 2) return Boolean(templateId)
    return true
  }, [step, planId, region, templateId])

  if (plansQ.error) return <ErrorState onRetry={() => plansQ.refetch()} />

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title="Create a Minecraft server"
        description="Claim a free server using your CVX credits"
        actions={
          <Button asChild variant="ghost" size="sm">
            <Link to="/minecraft">
              <ArrowLeft className="h-4 w-4" /> Back
            </Link>
          </Button>
        }
      />

      {/* Stepper */}
      <div className="flex items-center gap-2">
        {steps.map((label, i) => (
          <div key={label} className="flex flex-1 items-center gap-2">
            <div
              className={cn(
                'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
                i < step ? 'bg-emerald-500/20 text-emerald-400' : i === step ? 'bg-primary text-white' : 'bg-muted text-muted-foreground',
              )}
            >
              {i < step ? <Check className="h-3.5 w-3.5" /> : i + 1}
            </div>
            <div className={cn('hidden text-xs font-medium sm:block', i === step ? 'text-foreground' : 'text-muted-foreground')}>
              {label}
            </div>
            {i < steps.length - 1 && <div className="h-px flex-1 bg-border" />}
          </div>
        ))}
      </div>

      {step === 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold">Choose a plan</h3>
          {plansQ.isLoading ? (
            <SkeletonGrid count={3} />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {plans.map((plan) => (
                <Card
                  key={plan.id}
                  className={cn(
                    'cursor-pointer transition-all',
                    planId === plan.id && 'border-primary/60 ring-1 ring-primary/30',
                  )}
                  onClick={() => setPlanId(plan.id)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-semibold">{plan.name}</div>
                      <CvxBadge value={plan.cvx_cost} />
                    </div>
                    <div className="mt-3 grid grid-cols-3 gap-1.5 text-center">
                      <div className="rounded-md bg-muted/60 p-2">
                        <Cpu className="mx-auto h-3.5 w-3.5 text-cavrix-400" />
                        <div className="mt-1 text-xs font-semibold tabular">{plan.cpu}</div>
                      </div>
                      <div className="rounded-md bg-muted/60 p-2">
                        <Database className="mx-auto h-3.5 w-3.5 text-violet-400" />
                        <div className="mt-1 text-xs font-semibold tabular">
                          {plan.ram_mb >= 1024 ? `${plan.ram_mb / 1024}GB` : `${plan.ram_mb}MB`}
                        </div>
                      </div>
                      <div className="rounded-md bg-muted/60 p-2">
                        <HardDrive className="mx-auto h-3.5 w-3.5 text-emerald-400" />
                        <div className="mt-1 text-xs font-semibold tabular">
                          {plan.disk_mb >= 1024 ? `${plan.disk_mb / 1024}GB` : `${plan.disk_mb}MB`}
                        </div>
                      </div>
                    </div>
                    {plan.region && (
                      <div className="mt-2 text-[11px] text-muted-foreground">Region: {plan.region}</div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {step === 1 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold">Select a region</h3>
          <div className="grid gap-3 sm:grid-cols-3">
            {regions.map((r) => (
              <Card
                key={r.code}
                className={cn(
                  'cursor-pointer transition-all',
                  region === r.code && 'border-primary/60 ring-1 ring-primary/30',
                )}
                onClick={() => setRegion(r.code)}
              >
                <CardContent className="p-4">
                  <div className="text-2xl">{r.flag || '🌍'}</div>
                  <div className="mt-2 text-sm font-semibold">{r.name}</div>
                  <div className="text-xs text-muted-foreground font-mono">{r.code}</div>
                </CardContent>
              </Card>
            ))}
          </div>
          {regions.length === 0 && (
            <div className="rounded-xl surface p-6 text-center text-sm text-muted-foreground">
              No regions configured yet.
            </div>
          )}
        </div>
      )}

      {step === 2 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold">Select software</h3>
          {templatesQ.isLoading ? (
            <SkeletonGrid count={3} />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {templates.map((t) => (
                <Card
                  key={t.id}
                  className={cn(
                    'cursor-pointer transition-all',
                    templateId === t.id && 'border-primary/60 ring-1 ring-primary/30',
                  )}
                  onClick={() => {
                    setTemplateId(t.id)
                    setVersion(t.versions[0] || 'latest')
                  }}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-cyan-400" />
                      <div className="text-sm font-semibold">{t.name}</div>
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">{t.software}</div>
                    {t.versions.length > 0 && (
                      <div className="mt-2 text-[11px] text-muted-foreground">
                        {t.versions.slice(0, 4).join(' · ')}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
          {templates.length === 0 && (
            <div className="rounded-xl surface p-6 text-center text-sm text-muted-foreground">
              No templates configured yet.
            </div>
          )}
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold">Server details</h3>
          <form id="create-form" onSubmit={handleSubmit((d) => createMutation.mutate(d))} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="server_name">Server name</Label>
              <Input id="server_name" placeholder="survival-smp" {...register('server_name')} />
              {errors.server_name && <p className="text-xs text-destructive">{errors.server_name.message}</p>}
            </div>
            {selectedTemplate && selectedTemplate.versions.length > 0 && (
              <div className="space-y-2">
                <Label>Minecraft version</Label>
                <div className="flex flex-wrap gap-2">
                  {selectedTemplate.versions.map((v) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => setVersion(v)}
                      className={cn(
                        'rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors',
                        version === v
                          ? 'border-primary bg-primary/15 text-primary'
                          : 'border-border text-muted-foreground hover:bg-accent',
                      )}
                    >
                      {v}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </form>
        </div>
      )}

      {step === 4 && selectedPlan && (
        <Card>
          <CardContent className="space-y-4 p-5">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold">Confirm server claim</div>
                <div className="text-xs text-muted-foreground">You're about to claim a server</div>
              </div>
              <CvxBadge value={selectedPlan.cvx_cost} />
            </div>
            <div className="divide-y divide-border rounded-lg border border-border">
              <Row label="Plan" value={selectedPlan.name} />
              <Row label="Region" value={selectedRegion?.name || region} />
              <Row label="Software" value={selectedTemplate?.name || '—'} />
              <Row label="Version" value={version} />
              <Row
                label="Resources"
                value={`${selectedPlan.cpu} CPU · ${selectedPlan.ram_mb / 1024}GB RAM · ${selectedPlan.disk_mb / 1024}GB`}
              />
              <Row label="Duration" value={`${selectedPlan.duration_days} days`} />
            </div>
            <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-xs text-amber-200/80">
              CVX is deducted only after the server is successfully created. If provisioning fails, your credits
              are refunded automatically.
            </div>
          </CardContent>
        </Card>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
          <ArrowLeft className="h-4 w-4" /> Back
        </Button>
        {step < steps.length - 1 ? (
          <Button disabled={!canNext} onClick={() => setStep((s) => s + 1)}>
            Continue <ArrowRight className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            type="submit"
            form="create-form"
            loading={createMutation.isPending}
            onClick={() => {
              if (!planId) {
                toast.error('Select a plan first')
                setStep(0)
              }
            }}
          >
            Confirm & Claim <Check className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between px-4 py-2.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-xs font-medium">{value}</span>
    </div>
  )
}
