import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { KeyRound, ShieldCheck } from 'lucide-react'
import { AuthLayout } from './auth-layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api, showError } from '@/lib/api'
import { useAuth } from '@/stores/auth'
import type { MfaSetupInfo, TwoFaSetupLoginResponse } from '@/types'

export function TwoFactorSetupPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const login = useAuth((s) => s.login)
  const state = location.state as { login_token?: string; setup?: MfaSetupInfo } | null
  const loginToken = state?.login_token
  const setup = state?.setup

  const [code, setCode] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!loginToken || !setup) {
      toast.error('Missing login session. Please sign in again.')
      navigate('/login', { replace: true })
      return
    }
    setSubmitting(true)
    try {
      const res = await api.post<TwoFaSetupLoginResponse>('/auth/login/2fa/setup', {
        login_token: loginToken,
        secret: setup.secret,
        code,
      })
      setBackupCodes(res.backup_codes)
      login(res.access_token, res.refresh_token)
      toast.success('Two-factor authentication enabled')
    } catch (err) {
      showError(err, 'Verification failed')
    } finally {
      setSubmitting(false)
    }
  }

  const finish = () => navigate('/', { replace: true })

  return (
    <AuthLayout>
      <div className="space-y-6">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <h2 className="text-xl font-semibold tracking-tight">Secure your admin account</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Two-factor authentication is required for administrator accounts.
          </p>
        </div>

        {!backupCodes ? (
          <form onSubmit={onSubmit} className="space-y-4">
            {setup && (
              <div className="flex flex-col items-center gap-4 sm:flex-row">
                <img
                  src={`data:image/png;base64,${setup.qr_base64}`}
                  alt="QR code"
                  className="h-40 w-40 rounded-lg border border-border bg-white p-2"
                />
                <div className="flex-1 space-y-2">
                  <div>
                    <div className="text-xs text-muted-foreground">Manual secret</div>
                    <code className="rounded bg-muted px-2 py-1 font-mono text-xs">{setup.secret}</code>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Scan the QR code with your authenticator app, then enter the 6-digit code below.
                  </p>
                </div>
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="code">Authentication code</Label>
              <Input
                id="code"
                inputMode="numeric"
                autoFocus
                maxLength={6}
                className="text-center text-2xl tracking-[0.5em] font-mono"
                placeholder="000000"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              />
            </div>
            <Button type="submit" className="w-full" loading={submitting} disabled={code.length !== 6}>
              Verify and enable
            </Button>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="rounded-lg border border-amber-400/25 bg-amber-400/5 p-4">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-amber-300">
                <KeyRound className="h-3.5 w-3.5" /> Backup codes — save these now
              </div>
              <p className="mb-3 text-xs text-muted-foreground">
                Use one of these one-time codes if you lose access to your authenticator app.
              </p>
              <div className="grid grid-cols-2 gap-1 font-mono text-xs sm:grid-cols-3">
                {backupCodes.map((c) => (
                  <code key={c}>{c}</code>
                ))}
              </div>
            </div>
            <Button className="w-full" onClick={finish}>
              Continue
            </Button>
          </div>
        )}
      </div>
    </AuthLayout>
  )
}
