import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import {
  User,
  Shield,
  Monitor,
  KeyRound,
  Smartphone,
  Copy,
  Check,
} from 'lucide-react'
import { api, showError } from '@/lib/api'
import type { UserMe, SecurityState, TwoFaSetupResponse } from '@/types'
import { PageHeader } from '@/components/shared/page-header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { StatusBadge } from '@/components/shared/status-badge'
import { formatDateTime } from '@/lib/utils'
import { useAuth } from '@/stores/auth'

const profileSchema = z.object({
  display_name: z.string().max(80).optional().or(z.literal('')),
  avatar_url: z.string().max(512).optional().or(z.literal('')),
})

const passwordSchema = z
  .object({
    current_password: z.string().min(1, 'Enter your current password'),
    new_password: z.string().min(8, 'At least 8 characters').max(128),
    confirm: z.string(),
  })
  .refine((d) => d.new_password === d.confirm, { message: 'Passwords do not match', path: ['confirm'] })

export function SettingsPage() {
  const qc = useQueryClient()
  const setUser = useAuth((s) => s.setUser)
  const user = useAuth((s) => s.user)

  const [twoFaSetup, setTwoFaSetup] = useState<TwoFaSetupResponse | null>(null)
  const [totpCode, setTotpCode] = useState('')

  const securityQ = useQuery({
    queryKey: ['security'],
    queryFn: () => api.get<SecurityState>('/auth/security'),
  })

  const profileForm = useForm<z.infer<typeof profileSchema>>({
    resolver: zodResolver(profileSchema),
    defaultValues: { display_name: user?.display_name || '', avatar_url: user?.avatar_url || '' },
  })

  const passwordForm = useForm<z.infer<typeof passwordSchema>>({
    resolver: zodResolver(passwordSchema),
  })

  const profileMutation = useMutation({
    mutationFn: (data: z.infer<typeof profileSchema>) => api.patch<UserMe>('/users/me', data),
    onSuccess: (me) => {
      setUser(me)
      toast.success('Profile updated')
    },
    onError: (err) => showError(err),
  })

  const passwordMutation = useMutation({
    mutationFn: (data: z.infer<typeof passwordSchema>) =>
      api.patch('/users/me', {
        current_password: data.current_password,
        password: data.new_password,
      }),
    onSuccess: () => {
      toast.success('Password changed')
      passwordForm.reset()
    },
    onError: (err) => showError(err),
  })

  const setup2fa = useMutation({
    mutationFn: () => api.get<TwoFaSetupResponse>('/auth/2fa/setup'),
    onSuccess: (data) => setTwoFaSetup(data),
    onError: (err) => showError(err),
  })

  const enable2fa = useMutation({
    mutationFn: () => api.post('/auth/2fa/enable', { secret: twoFaSetup!.secret, code: totpCode }),
    onSuccess: () => {
      toast.success('Two-factor authentication enabled')
      setTwoFaSetup(null)
      setTotpCode('')
      qc.invalidateQueries({ queryKey: ['security'] })
      qc.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
    onError: (err) => showError(err),
  })

  const disable2fa = useMutation({
    mutationFn: (password: string) => api.post('/auth/2fa/disable', { password }),
    onSuccess: () => {
      toast.success('Two-factor authentication disabled')
      qc.invalidateQueries({ queryKey: ['security'] })
    },
    onError: (err) => showError(err),
  })

  const revokeSession = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/sessions/${id}`),
    onSuccess: () => {
      toast.success('Session revoked')
      qc.invalidateQueries({ queryKey: ['security'] })
    },
    onError: (err) => showError(err),
  })

  const [disablePassword, setDisablePassword] = useState('')

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Manage your profile, security, and sessions" />

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">
            <User className="mr-1.5 h-3.5 w-3.5" /> Profile
          </TabsTrigger>
          <TabsTrigger value="security">
            <Shield className="mr-1.5 h-3.5 w-3.5" /> Security
          </TabsTrigger>
          <TabsTrigger value="sessions">
            <Monitor className="mr-1.5 h-3.5 w-3.5" /> Sessions
          </TabsTrigger>
        </TabsList>

        {/* Profile */}
        <TabsContent value="profile" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Profile information</CardTitle>
              <CardDescription>How you appear across Cavrix Cloud</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={profileForm.handleSubmit((d) => profileMutation.mutate(d))} className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Username</Label>
                    <Input value={user?.username || ''} disabled />
                    <p className="text-xs text-muted-foreground">Usernames cannot be changed.</p>
                  </div>
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input value={user?.email || ''} disabled />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="display_name">Display name</Label>
                    <Input id="display_name" {...profileForm.register('display_name')} placeholder="Your name" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="avatar_url">Avatar URL</Label>
                    <Input id="avatar_url" {...profileForm.register('avatar_url')} placeholder="https://…" />
                  </div>
                </div>
                <Button type="submit" loading={profileMutation.isPending}>
                  Save changes
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security */}
        <TabsContent value="security" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Change password</CardTitle>
              <CardDescription>Use a strong password you don't use elsewhere</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={passwordForm.handleSubmit((d) => passwordMutation.mutate(d))} className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="current_password">Current password</Label>
                    <Input id="current_password" type="password" {...passwordForm.register('current_password')} />
                    {passwordForm.formState.errors.current_password && (
                      <p className="text-xs text-destructive">{passwordForm.formState.errors.current_password.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="new_password">New password</Label>
                    <Input id="new_password" type="password" {...passwordForm.register('new_password')} />
                    {passwordForm.formState.errors.new_password && (
                      <p className="text-xs text-destructive">{passwordForm.formState.errors.new_password.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirm">Confirm</Label>
                    <Input id="confirm" type="password" {...passwordForm.register('confirm')} />
                    {passwordForm.formState.errors.confirm && (
                      <p className="text-xs text-destructive">{passwordForm.formState.errors.confirm.message}</p>
                    )}
                  </div>
                </div>
                <Button type="submit" loading={passwordMutation.isPending}>
                  Update password
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Two-factor authentication</CardTitle>
              <CardDescription>
                Status: <StatusBadge status={securityQ.data?.twofa_enabled ? 'active' : 'disabled'} />
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!securityQ.data?.twofa_enabled ? (
                twoFaSetup ? (
                  <div className="space-y-4">
                    <div className="flex flex-col items-center gap-4 sm:flex-row">
                      <img
                        src={`data:image/png;base64,${twoFaSetup.qr_base64}`}
                        alt="QR code"
                        className="h-40 w-40 rounded-lg border border-border bg-white p-2"
                      />
                      <div className="flex-1 space-y-2">
                        <div>
                          <div className="text-xs text-muted-foreground">Manual secret</div>
                          <div className="flex items-center gap-2">
                            <code className="rounded bg-muted px-2 py-1 text-xs">{twoFaSetup.secret}</code>
                            <Button
                              size="iconSm"
                              variant="ghost"
                              onClick={() => {
                                navigator.clipboard.writeText(twoFaSetup.secret)
                                toast.success('Copied')
                              }}
                            >
                              <Copy className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>
                        <div>
                          <div className="mb-2 text-xs text-muted-foreground">
                            Scan with your authenticator app, then enter the 6-digit code:
                          </div>
                          <div className="flex gap-2">
                            <Input
                              inputMode="numeric"
                              maxLength={6}
                              value={totpCode}
                              onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                              placeholder="000000"
                              className="w-32 font-mono tracking-widest"
                            />
                            <Button
                              onClick={() => enable2fa.mutate()}
                              loading={enable2fa.isPending}
                              disabled={totpCode.length !== 6}
                            >
                              <Check className="h-4 w-4" /> Enable
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                    {twoFaSetup.backup_codes.length > 0 && (
                      <div className="rounded-lg border border-amber-400/25 bg-amber-400/5 p-4">
                        <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-amber-300">
                          <KeyRound className="h-3.5 w-3.5" /> Backup codes — save these now
                        </div>
                        <div className="grid grid-cols-2 gap-1 font-mono text-xs sm:grid-cols-3">
                          {twoFaSetup.backup_codes.map((c) => (
                            <code key={c}>{c}</code>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-muted-foreground">
                      Add an extra layer of security with an authenticator app.
                    </div>
                    <Button onClick={() => setup2fa.mutate()} loading={setup2fa.isPending}>
                      <Smartphone className="h-4 w-4" /> Set up 2FA
                    </Button>
                  </div>
                )
              ) : (
                <div className="space-y-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                    <div className="text-sm text-muted-foreground">Two-factor authentication is active.</div>
                    <div className="flex gap-2 sm:ml-auto">
                      <Input
                        type="password"
                        placeholder="Password to disable"
                        value={disablePassword}
                        onChange={(e) => setDisablePassword(e.target.value)}
                        className="w-52"
                      />
                      <Button
                        variant="destructive"
                        loading={disable2fa.isPending}
                        disabled={!disablePassword}
                        onClick={() => disable2fa.mutate(disablePassword)}
                      >
                        Disable
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Sessions */}
        <TabsContent value="sessions" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Active sessions</CardTitle>
              <CardDescription>Devices currently signed in to your account</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="divide-y divide-border">
                {securityQ.data?.sessions.map((s) => (
                  <div key={s.id} className="flex items-center justify-between py-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                        <Monitor className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div>
                        <div className="text-sm font-medium">
                          {s.device_name || 'Unknown device'} {s.current && <span className="text-xs text-primary">(this device)</span>}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {s.ip} · {formatDateTime(s.last_seen_at || '')}
                        </div>
                      </div>
                    </div>
                    {!s.current && (
                      <Button
                        variant="outline"
                        size="sm"
                        loading={revokeSession.isPending}
                        onClick={() => revokeSession.mutate(s.id)}
                      >
                        Revoke
                      </Button>
                    )}
                  </div>
                ))}
                {securityQ.isLoading && (
                  <div className="space-y-3 py-3">
                    {Array.from({ length: 3 }).map((_, i) => (
                      <div key={i} className="h-12 animate-pulse rounded-lg bg-muted" />
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
