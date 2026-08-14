import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { ShieldCheck } from 'lucide-react'
import { AuthLayout } from './auth-layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api, showError } from '@/lib/api'
import { useAuth } from '@/stores/auth'
import type { TokenResponse } from '@/types'

export function TwoFactorPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const login = useAuth((s) => s.login)
  const loginToken = (location.state as { login_token?: string })?.login_token
  const [code, setCode] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!loginToken) {
      toast.error('Missing login session. Please sign in again.')
      navigate('/login')
      return
    }
    setSubmitting(true)
    try {
      const res = await api.post<TokenResponse>('/auth/login/2fa', { login_token: loginToken, code })
      login(res.access_token, res.refresh_token)
      toast.success('Welcome back!')
      navigate('/', { replace: true })
    } catch (err) {
      showError(err, 'Verification failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout>
      <div className="space-y-6">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <h2 className="text-xl font-semibold tracking-tight">Two-factor authentication</h2>
          <p className="mt-1 text-sm text-muted-foreground">Enter the 6-digit code from your authenticator app</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
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
            Verify
          </Button>
        </form>
        <p className="text-center text-xs text-muted-foreground">
          Lost your authenticator? Contact support for account recovery.
        </p>
      </div>
    </AuthLayout>
  )
}
