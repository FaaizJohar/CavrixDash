import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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
import type { TokenResponse } from '@/types'

const schema = z
  .object({
    email: z.string().email('Enter a valid email'),
    username: z
      .string()
      .min(3, 'At least 3 characters')
      .max(40)
      .regex(/^[a-zA-Z0-9_.-]+$/, 'Only letters, numbers, . _ -'),
    display_name: z.string().max(80).optional().or(z.literal('')),
    password: z.string().min(8, 'At least 8 characters').max(128),
    confirm: z.string(),
    referral_code: z.string().optional().or(z.literal('')),
  })
  .refine((d) => d.password === d.confirm, { message: 'Passwords do not match', path: ['confirm'] })

type FormData = z.infer<typeof schema>

export function RegisterPage() {
  const navigate = useNavigate()
  const login = useAuth((s) => s.login)
  const [showPassword, setShowPassword] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: FormData) => {
    try {
      const res = await api.post<
        { user: { id: string }; requires_verification: boolean; message: string } | TokenResponse
      >('/auth/register', {
        email: data.email,
        username: data.username,
        display_name: data.display_name,
        password: data.password,
        referral_code: data.referral_code || undefined,
      })
      if ('requires_verification' in res && res.requires_verification) {
        toast.success('Account created. Check your email to verify.')
        navigate('/verify-email')
        return
      }
      const tok = res as TokenResponse
      login(tok.access_token, tok.refresh_token)
      toast.success('Account created. Welcome to Cavrix Cloud!')
      navigate('/', { replace: true })
    } catch (err) {
      showError(err, 'Registration failed')
    }
  }

  return (
    <AuthLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Create your account</h2>
          <p className="mt-1 text-sm text-muted-foreground">Start earning CVX in minutes</p>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" placeholder="you@example.com" {...register('email')} />
            {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <Input id="username" placeholder="yourgamertag" {...register('username')} />
            {errors.username && <p className="text-xs text-destructive">{errors.username.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="display_name">Display name (optional)</Label>
            <Input id="display_name" placeholder="How we address you" {...register('display_name')} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="At least 8 characters"
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
          <div className="space-y-2">
            <Label htmlFor="confirm">Confirm password</Label>
            <Input id="confirm" type="password" placeholder="Repeat password" {...register('confirm')} />
            {errors.confirm && <p className="text-xs text-destructive">{errors.confirm.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="referral_code">Referral code (optional)</Label>
            <Input id="referral_code" placeholder="Friend's code" {...register('referral_code')} />
          </div>
          <Button type="submit" className="w-full" loading={isSubmitting}>
            Create account
          </Button>
        </form>
        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <Link to="/login" className="text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </AuthLayout>
  )
}
