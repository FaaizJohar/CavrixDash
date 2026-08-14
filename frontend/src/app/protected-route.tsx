import { useEffect, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/stores/auth'
import { Splash } from '@/components/shared/splash'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading, initialized, load } = useAuth()
  const location = useLocation()

  useEffect(() => {
    if (!initialized) load()
  }, [initialized, load])

  if (!initialized) return <Splash />

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  if (user.status === 'suspended') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <div className="text-lg font-semibold">Account suspended</div>
        <p className="max-w-md text-sm text-muted-foreground">
          Your account has been suspended. Please contact support for more information.
        </p>
        <a href="mailto:support@cavrix.app" className="text-sm text-primary underline">
          Contact support
        </a>
      </div>
    )
  }

  if (user.status === 'banned') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <div className="text-lg font-semibold">Account banned</div>
        <p className="max-w-md text-sm text-muted-foreground">
          This account has been permanently banned for violating our terms of service.
        </p>
      </div>
    )
  }

  return <>{children}</>
}
