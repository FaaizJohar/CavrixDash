import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { AuthLayout } from './auth-layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api, showError } from '@/lib/api'

const schema = z.object({
  password: z.string().min(8, 'At least 8 characters').max(128),
  confirm: z.string(),
}).refine((d) => d.password === d.confirm, { message: 'Passwords do not match', path: ['confirm'] })

type FormData = z.infer<typeof schema>

export function ResetPasswordPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const token = params.get('token') || ''

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: FormData) => {
    try {
      await api.post('/auth/reset-password', { token, password: data.password }, { auth: false })
      toast.success('Password reset. Sign in with your new password.')
      navigate('/login')
    } catch (err) {
      showError(err)
    }
  }

  return (
    <AuthLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Set a new password</h2>
          <p className="mt-1 text-sm text-muted-foreground">Choose a strong password you haven't used before.</p>
        </div>
        {!token ? (
          <div className="space-y-4">
            <p className="text-sm text-destructive">This reset link is invalid or has expired.</p>
            <Button asChild variant="outline" className="w-full">
              <Link to="/forgot-password">Request a new link</Link>
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="password">New password</Label>
              <Input id="password" type="password" placeholder="At least 8 characters" {...register('password')} />
              {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm">Confirm password</Label>
              <Input id="confirm" type="password" placeholder="Repeat password" {...register('confirm')} />
              {errors.confirm && <p className="text-xs text-destructive">{errors.confirm.message}</p>}
            </div>
            <Button type="submit" className="w-full" loading={isSubmitting}>
              Reset password
            </Button>
          </form>
        )}
      </div>
    </AuthLayout>
  )
}
