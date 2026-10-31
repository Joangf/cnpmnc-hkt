import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import type { z } from 'zod'
import { useAuth } from '../auth/AuthContext'
import { ErrorAlert, Field, Panel } from '../components/ui'
import { registerSchema } from '../lib/validation'

type FormValues = z.input<typeof registerSchema>

export default function RegisterPage() {
  const { register: registerAccount } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<unknown>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(registerSchema) })

  const onSubmit = handleSubmit(async (values) => {
    setError(null)
    const parsed = registerSchema.parse(values)
    try {
      await registerAccount({
        email: parsed.email,
        password: parsed.password,
        full_name: parsed.full_name,
        date_of_birth: parsed.date_of_birth,
        phone_number: parsed.phone_number,
      })
      navigate('/doctors', { replace: true })
    } catch (err) {
      setError(err)
    }
  })

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
