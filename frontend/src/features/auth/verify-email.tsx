import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { CheckCircle2 } from 'lucide-react'
import { AuthLayout } from './auth-layout'
import { Button } from '@/components/ui/button'
import { api, showError } from '@/lib/api'

export function VerifyEmailPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token')
  const [state, setState] = useState<'loading' | 'done' | 'error'>('loading')

  useEffect(() => {
    if (!token) {
      setState('error')
      return
    }
    api
      .post('/auth/verify-email', { token }, { auth: false })
      .then(() => {
        setState('done')
        toast.success('Email verified')
      })
      .catch((e) => {
        setState('error')
        showError(e, 'Verification failed')
      })
  }, [token])

  return (
    <AuthLayout>
      <div className="space-y-6 text-center">
        {state === 'loading' && (
          <div>
            <h2 className="text-xl font-semibold">Verifying your email…</h2>
          </div>
        )}
        {state === 'done' && (
          <div className="space-y-4">
            <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-400" />
            <div>
              <h2 className="text-xl font-semibold">Email verified</h2>
              <p className="mt-1 text-sm text-muted-foreground">Your account is fully activated.</p>
            </div>
            <Button asChild className="w-full">
              <Link to="/login">Continue to sign in</Link>
            </Button>
          </div>
        )}
        {state === 'error' && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Verification failed</h2>
            <p className="text-sm text-muted-foreground">
              This link may be invalid or expired. Sign in to request a new one.
            </p>
            <Button asChild variant="outline" className="w-full" onClick={() => navigate('/login')}>
              <Link to="/login">Back to sign in</Link>
            </Button>
          </div>
        )}
      </div>
    </AuthLayout>
  )
}
