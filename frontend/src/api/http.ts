import type { TokenResponse } from './types'

const API_PREFIX = '/api/v1'

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly requestId: string | null = null,
    public readonly details: unknown = null,
  ) {
    super(message)
  }
}

// The access token lives in memory only; the refresh token is an httpOnly cookie.
let accessToken: string | null = null
let refreshPromise: Promise<TokenResponse | null> | null = null
let authFailureHandler: (() => void) | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function setAuthFailureHandler(handler: () => void) {
  authFailureHandler = handler
}

/** Exchanges the refresh cookie for a new access token. Concurrent callers share one request. */
export function refreshSession(): Promise<TokenResponse | null> {
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_PREFIX}/auth/refresh`, { method: 'POST', credentials: 'same-origin' })
      .then(async (res) => (res.ok ? ((await res.json()) as TokenResponse) : null))
      .catch(() => null)
      .then((token) => {
        setAccessToken(token?.access_token ?? null)
        return token
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

type QueryValue = string | number | boolean | null | undefined

export interface RequestOptions {
  body?: unknown
  query?: Record<string, QueryValue>
  headers?: Record<string, string>
  auth?: boolean
}

async function toApiError(res: Response): Promise<ApiError> {
  try {
    const data = await res.json()
    const err = data?.error
    if (err?.code) return new ApiError(res.status, err.code, err.message, err.request_id ?? null, err.details ?? null)
  } catch {
    // not JSON
  }
  return new ApiError(res.status, 'HttpError', `Request failed (${res.status})`, res.headers.get('x-request-id'))
}

export async function request<T>(method: string, path: string, opts: RequestOptions = {}, retried = false): Promise<T> {
  const url = new URL(`${API_PREFIX}${path}`, window.location.origin)
  for (const [key, value] of Object.entries(opts.query ?? {})) {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value))
  }

  const headers: Record<string, string> = { Accept: 'application/json', ...opts.headers }
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  const useAuth = opts.auth !== false
  if (useAuth && accessToken) headers.Authorization = `Bearer ${accessToken}`

  let res: Response
  try {
    res = await fetch(url, {
      method,
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      credentials: 'same-origin',
    })
  } catch {
    throw new ApiError(0, 'NetworkError', 'Cannot reach the server. Check your connection and try again.')
  }

  if (res.status === 401 && useAuth && !retried) {
    const refreshed = await refreshSession()
    if (refreshed) return request<T>(method, path, opts, true)
    authFailureHandler?.()
  }
  if (!res.ok) throw await toApiError(res)
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}
