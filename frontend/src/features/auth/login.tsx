import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Eye, EyeOff } from 'lucide-react'
import { AuthLayout } from './auth-layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api, showError } from '@/lib/api'
import { useAuth } from '@/stores/auth'
import type { MfaSetupInfo, TokenResponse } from '@/types'

const schema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})

type FormData = z.infer<typeof schema>

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const login = useAuth((s) => s.login)
  const [showPassword, setShowPassword] = useState(false)
  const [twoFaToken, setTwoFaToken] = useState<string | null>(null)

  const from = (location.state as { from?: string })?.from || '/'

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: FormData) => {
    try {
      const res = await api.post<
        | TokenResponse
        | { requires_2fa: boolean; login_token: string; mfa_setup_required?: boolean; setup?: MfaSetupInfo }
      >('/auth/login', {
        ...data,
        device_id: localStorage.getItem('cavrix.device_id') || undefined,
        device_name: navigator.userAgent.slice(0, 80),
      })
      if ('requires_2fa' in res && res.requires_2fa && 'login_token' in res) {
        if (res.mfa_setup_required && res.setup) {
          navigate('/2fa/setup', { state: { login_token: res.login_token, setup: res.setup } })
          return
        }
        setTwoFaToken(res.login_token)
        navigate('/2fa', { state: { login_token: res.login_token } })
        return
      }
      const tok = res as TokenResponse
      login(tok.access_token, tok.refresh_token)
      toast.success(`Welcome back${tok.user.display_name ? ', ' + tok.user.display_name : ''}!`)
      navigate(from, { replace: true })
    } catch (err) {
      showError(err, 'Sign in failed')
    }
  }

  return (
    <AuthLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Sign in</h2>
          <p className="mt-1 text-sm text-muted-foreground">Welcome back to Cavrix Cloud</p>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" placeholder="you@example.com" autoComplete="email" {...register('email')} />
            {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password">Password</Label>
              <Link to="/forgot-password" className="text-xs text-primary hover:underline">
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                autoComplete="current-password"
                {...register('password')}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
          </div>
          <Button type="submit" className="w-full" loading={isSubmitting}>
            Sign in
          </Button>
        </form>
        <p className="text-center text-sm text-muted-foreground">
          Don't have an account?{' '}
          <Link to="/register" className="text-primary hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </AuthLayout>
  )
}
