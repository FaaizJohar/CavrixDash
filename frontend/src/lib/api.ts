import { toast } from 'sonner'

const API_URL = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')

const ACCESS_KEY = 'cavrix.access_token'
const REFRESH_KEY = 'cavrix.refresh_token'

export interface ApiError {
  message: string
  code: string
  ref: string
  status: number
}

export class ApiError extends Error {
  constructor(message: string, public code: string, public ref: string, public status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

let refreshPromise: Promise<boolean> | null = null

async function doRefresh(): Promise<boolean> {
  const refresh = tokenStore.refresh
  if (!refresh) return false
  try {
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
    if (!res.ok) {
      tokenStore.clear()
      return false
    }
    const data = await res.json()
    tokenStore.set(data.access_token, data.refresh_token)
    return true
  } catch {
    tokenStore.clear()
    return false
  }
}

export function refreshTokens(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = doRefresh().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

function parseError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: { message?: string; code?: string; ref?: string } })?.detail
  return new ApiError(
    detail?.message || 'Something went wrong.',
    detail?.code || 'INTERNAL',
    detail?.ref || '',
    status,
  )
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  auth?: boolean
  retry?: boolean
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, auth = true, retry = true, headers, ...rest } = options

  const call = async (): Promise<T> => {
    const reqHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(headers as Record<string, string>),
    }
    if (auth && tokenStore.access) {
      reqHeaders.Authorization = `Bearer ${tokenStore.access}`
    }

    const res = await fetch(`${API_URL}${path}`, {
      ...rest,
      headers: reqHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })

    if (res.status === 401 && auth && retry && tokenStore.refresh) {
      const ok = await refreshTokens()
      if (ok) return call()
      throw new ApiError('Your session has expired. Please sign in again.', 'UNAUTHORIZED', '', 401)
    }

    if (!res.ok) {
      let payload: unknown = null
      try {
        payload = await res.json()
      } catch {
        /* ignore */
      }
      throw parseError(res.status, payload)
    }

    if (res.status === 204) return undefined as T
    return (await res.json()) as T
  }

  return call()
}

export const api = {
  get: <T>(path: string, opts?: Omit<RequestOptions, 'body' | 'method'>) =>
    apiFetch<T>(path, { ...opts, method: 'GET' }),
  post: <T>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'body'>) =>
    apiFetch<T>(path, { ...opts, method: 'POST', body }),
  patch: <T>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'body'>) =>
    apiFetch<T>(path, { ...opts, method: 'PATCH', body }),
  put: <T>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'body'>) =>
    apiFetch<T>(path, { ...opts, method: 'PUT', body }),
  delete: <T>(path: string, opts?: Omit<RequestOptions, 'body'>) =>
    apiFetch<T>(path, { ...opts, method: 'DELETE' }),
}

export function getWsUrl(relative: string): string {
  const base = (import.meta.env.VITE_WS_URL || import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
  const origin = base || window.location.origin
  const wsOrigin = origin.replace(/^http/, 'ws')
  return `${wsOrigin}${relative}`
}

export function errorMessage(err: unknown, fallback = 'Something went wrong.'): string {
  if (err instanceof ApiError) return `${err.message}${err.ref ? ` (${err.ref})` : ''}`
  if (err instanceof Error) return err.message
  return fallback
}

export function showError(err: unknown, fallback?: string) {
  toast.error(errorMessage(err, fallback))
}
