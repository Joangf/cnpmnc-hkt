import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { Card, ErrorAlert, Field, Notice, Panel } from '../components/ui'
import { passwordSchema } from '../lib/validation'

export default function ForgotPasswordPage() {
  const [params] = useSearchParams()
  const [email, setEmail] = useState('')
  const [token, setToken] = useState(params.get('token') ?? '')
  const [password, setPassword] = useState('')
  const [passwordError, setPasswordError] = useState<string>()

  const requestReset = useMutation({
    mutationFn: () => api.auth.requestPasswordReset(email.trim()),
    onSuccess: (res) => res.dev_reset_token && setToken(res.dev_reset_token),
  })
  const confirmReset = useMutation({ mutationFn: () => api.auth.confirmPasswordReset(token, password) })

  return (
    <div className="mx-auto max-w-lg space-y-8">
      <Panel tone="sun" header={<h1 className="page-title">Reset your password</h1>}>
        <form
          className="space-y-5"
          onSubmit={(e) => {
            e.preventDefault()
            requestReset.mutate()
          }}
        >
          <Field label="Email" hint="We send reset instructions to this address">
            <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <ErrorAlert error={requestReset.error} />
          {requestReset.data && <Notice tone="success">{requestReset.data.message}</Notice>}
          {requestReset.data?.dev_reset_token && (
            <Notice tone="warning">Development mode: no email service is configured, so the reset token was filled in below.</Notice>
          )}
          <button className="btn-secondary w-full" disabled={requestReset.isPending}>
            Send reset instructions
          </button>
        </form>
      </Panel>

      {token && (
        <Card>
          <form
            className="space-y-5"
            onSubmit={(e) => {
              e.preventDefault()
              const check = passwordSchema.safeParse(password)
              setPasswordError(check.success ? undefined : check.error.issues[0]?.message)
              if (check.success) confirmReset.mutate()
            }}
          >
            <Field label="New password" hint="At least 8 characters, with a letter and a number" error={passwordError}>
              <input className="input" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </Field>
            <ErrorAlert error={confirmReset.error} />
            {confirmReset.data ? (
              <Notice tone="success">
                {confirmReset.data.message}{' '}
                <Link className="link" to="/login">
                  Sign in
                </Link>
              </Notice>
            ) : (
              <button className="btn-primary w-full" disabled={confirmReset.isPending}>
                Set new password
              </button>
            )}
          </form>
        </Card>
      )}
    </div>
  )
}
