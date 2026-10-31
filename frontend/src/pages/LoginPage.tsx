import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { ErrorAlert, Field, Panel } from '../components/ui'

/** Only allow same-site relative redirects. Browsers treat "\" like "/", so "/\evil" is external. */
export function safeNext(value: string | null, fallback: string): string {
  return value && value.startsWith('/') && !value.startsWith('//') && !value.includes('\\') ? value : fallback
}

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)

  return (
    <div className="mx-auto max-w-lg">
      <Panel
        tone="blush"
        header={
          <>
            <h1 className="page-title">Sign in</h1>
            <p className="mt-2 text-muted">Book, pay for and manage your appointments.</p>
          </>
        }
      >
        <form
          className="space-y-5"
          onSubmit={async (e) => {
            e.preventDefault()
            setBusy(true)
            setError(null)
            try {
              const user = await login(email.trim(), password)
              navigate(safeNext(params.get('next'), user.role === 'ADMIN' ? '/admin' : '/appointments'), { replace: true })
            } catch (err) {
              setError(err)
            } finally {
              setBusy(false)
            }
          }}
        >
          <Field label="Email">
            <input className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label="Password">
            <input className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <ErrorAlert error={error} />
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <div className="mt-6 flex flex-wrap justify-between gap-4">
          <Link className="link" to="/forgot-password">
            Forgot password?
          </Link>
          <Link className="link" to="/register">
            Create an account
          </Link>
        </div>
      </Panel>
    </div>
  )
}
