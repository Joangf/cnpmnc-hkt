import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '../api/endpoints'
import { refreshSession, setAccessToken, setAuthFailureHandler } from '../api/http'
import type { RegisterPayload, RegistrationPending, TokenResponse, UserMe } from '../api/types'

interface AuthState {
  user: UserMe | null
  ready: boolean
  login: (email: string, password: string) => Promise<UserMe>
  /** Creates an unverified account and emails an OTP; the session starts after verifyRegistration. */
  register: (payload: RegisterPayload) => Promise<RegistrationPending>
  resendOtp: (email: string) => Promise<RegistrationPending>
  verifyRegistration: (email: string, otp: string) => Promise<UserMe>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserMe | null>(null)
  const [ready, setReady] = useState(false)
  const queryClient = useQueryClient()

  useEffect(() => {
    setAuthFailureHandler(() => {
      setAccessToken(null)
      setUser(null)
    })
    // Restore the session from the refresh cookie on page load.
    refreshSession()
      .then((token) => setUser(token?.user ?? null))
      .finally(() => setReady(true))
  }, [])

  const apply = useCallback((token: TokenResponse) => {
    setAccessToken(token.access_token)
    setUser(token.user)
    return token.user
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      user,
      ready,
      login: async (email, password) => apply(await api.auth.login({ email, password })),
      register: (payload) => api.auth.register(payload),
      resendOtp: (email) => api.auth.resendRegistrationOtp(email),
      verifyRegistration: async (email, otp) => apply(await api.auth.verifyRegistration(email, otp)),
      logout: async () => {
        try {
          await api.auth.logout()
        } finally {
          setAccessToken(null)
          setUser(null)
          queryClient.clear()
        }
      },
    }),
    [user, ready, apply, queryClient],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
