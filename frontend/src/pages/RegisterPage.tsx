import { zodResolver } from '@hookform/resolvers/zod'
import { useState, type FormEvent } from 'react'
import type { RegistrationPending } from '../api/types'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import type { z } from 'zod'
import { useAuth } from '../auth/AuthContext'
import { ErrorAlert, Field, Notice, Panel } from '../components/ui'
import { registerSchema } from '../lib/validation'

type FormValues = z.input<typeof registerSchema>

export default function RegisterPage() {
  const { register: registerAccount, resendOtp, verifyRegistration } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<unknown>(null)
  const [pending, setPending] = useState<RegistrationPending | null>(null)
  const [otp, setOtp] = useState('')
  const [busy, setBusy] = useState(false)
  const [resent, setResent] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(registerSchema) })

  const onSubmit = handleSubmit(async (values) => {
    setError(null)
    const parsed = registerSchema.parse(values)
    try {
      const res = await registerAccount({
        email: parsed.email,
        password: parsed.password,
        full_name: parsed.full_name,
        date_of_birth: parsed.date_of_birth,
        phone_number: parsed.phone_number,
      })
      setOtp(res.dev_otp ?? '')
      setPending(res)
    } catch (err) {
      setError(err)
    }
  })

  const run = async (action: () => Promise<void>) => {
    setError(null)
    setBusy(true)
    try {
      await action()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  const onVerify = (e: FormEvent) => {
    e.preventDefault()
    if (!pending) return
    void run(async () => {
      await verifyRegistration(pending.email, otp.trim())
      navigate('/doctors', { replace: true })
    })
  }

  const onResend = () =>
    pending &&
    void run(async () => {
      setPending(await resendOtp(pending.email))
      setResent(true)
    })

  if (pending) {
    return (
      <div className="mx-auto max-w-lg">
        <Panel
          tone="blush"
          header={
            <>
              <h1 className="page-title">Verify your email</h1>
              <p className="mt-2 text-muted">
                We sent a 6-digit code to <strong>{pending.email}</strong>. It expires in {Math.round(pending.expires_in / 60)} minutes.
              </p>
            </>
          }
        >
          <form className="space-y-5" onSubmit={onVerify} noValidate>
            <Field label="Verification code">
              <input
                className="input tracking-[0.4em]"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
              />
            </Field>
            {pending.dev_otp && (
              <Notice tone="warning">Development mode: no email service is configured, so the code was filled in for you.</Notice>
            )}
            {resent && !error && <Notice tone="success">A new code is on its way.</Notice>}
            <ErrorAlert error={error} />
            <button className="btn-primary w-full" disabled={busy || otp.length !== 6}>
              {busy ? 'Verifying…' : 'Verify and continue'}
            </button>
          </form>
          <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
            <button type="button" className="link" onClick={onResend} disabled={busy}>
              Resend code
            </button>
            <button
              type="button"
              className="link"
              onClick={() => {
                setPending(null)
                setError(null)
                setResent(false)
              }}
            >
              Use a different email
            </button>
          </div>
        </Panel>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Panel
        tone="blush"
        header={
          <>
            <h1 className="page-title">Create an account</h1>
            <p className="mt-2 text-muted">We only collect the information needed to book and manage your appointments.</p>
          </>
        }
      >
        <form className="space-y-5" onSubmit={onSubmit} noValidate>
          <Field label="Full name" hint="As shown on your ID" error={errors.full_name?.message}>
            <input className="input" autoComplete="name" {...register('full_name')} />
          </Field>
          <Field label="Email" hint="For your sign-in and booking updates" error={errors.email?.message}>
            <input className="input" type="email" autoComplete="email" {...register('email')} />
          </Field>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Date of birth" hint="Hospitals use it to find your medical record" error={errors.date_of_birth?.message}>
              <input className="input" type="date" {...register('date_of_birth')} />
            </Field>
            <Field label="Phone number" hint="So the hospital can reach you about a visit" error={errors.phone_number?.message}>
              <input className="input" type="tel" autoComplete="tel" {...register('phone_number')} />
            </Field>
          </div>
          <Field label="Password" hint="At least 8 characters, with a letter and a number" error={errors.password?.message}>
            <input className="input" type="password" autoComplete="new-password" {...register('password')} />
          </Field>
          <Field label="Confirm password" error={errors.confirm_password?.message}>
            <input className="input" type="password" autoComplete="new-password" {...register('confirm_password')} />
          </Field>
          <ErrorAlert error={error} />
          <button className="btn-primary w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>
        <p className="mt-6">
          Already registered?{' '}
          <Link className="link" to="/login">
            Sign in
          </Link>
        </p>
      </Panel>
    </div>
  )
}
