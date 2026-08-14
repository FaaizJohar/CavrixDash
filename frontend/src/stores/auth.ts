import { create } from 'zustand'
import { api, tokenStore } from '@/lib/api'
import type { UserMe } from '@/types'

interface AuthState {
  user: UserMe | null
  loading: boolean
  initialized: boolean
  setUser: (user: UserMe | null) => void
  load: () => Promise<void>
  login: (access: string, refresh: string) => void
  logout: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: false,
  initialized: false,

  setUser: (user) => set({ user }),

  load: async () => {
    if (!tokenStore.access) {
      set({ initialized: true })
      return
    }
    set({ loading: true })
    try {
      const user = await api.get<UserMe>('/auth/me')
      set({ user, loading: false, initialized: true })
    } catch (err) {
      const e = err as { status?: number }
      if (e.status !== 401) {
        set({ user: null, loading: false, initialized: true })
      } else {
        set({ user: null, loading: false, initialized: true })
      }
    }
  },

  login: (access, refresh) => {
    tokenStore.set(access, refresh)
  },

  logout: async () => {
    try {
      await api.post('/auth/logout', {}, { retry: false })
    } catch {
      /* ignore */
    }
    tokenStore.clear()
    set({ user: null })
  },
}))

export function useCurrentUser(): UserMe | null {
  return useAuth((s) => s.user)
}
