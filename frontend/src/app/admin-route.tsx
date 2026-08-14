import { useEffect, type ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/stores/auth'
import { Splash } from '@/components/shared/splash'
import { canAccessAdmin } from '@/lib/roles'

export function AdminRoute({ children }: { children: ReactNode }) {
  const { user, initialized, load } = useAuth()

  useEffect(() => {
    if (!initialized) load()
  }, [initialized, load])

  if (!initialized) return <Splash />

  if (!user) return <Navigate to="/login" replace />
  if (!user.roles || !canAccessAdmin(user.roles)) return <Navigate to="/" replace />

  return <>{children}</>
}
