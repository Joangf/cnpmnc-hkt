import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import type { z } from 'zod'
import { api } from '../api/endpoints'
import { ErrorAlert, Field, Notice, Panel, Spinner } from '../components/ui'
import { profileSchema } from '../lib/validation'

type FormValues = z.input<typeof profileSchema>

export default function ProfilePage() {
  const queryClient = useQueryClient()
  const profile = useQuery({ queryKey: ['profile'], queryFn: api.profile.get })
  const save = useMutation({
    mutationFn: (values: FormValues) => {
      const parsed = profileSchema.parse(values)
      return api.profile.update({ ...parsed, address: parsed.address || null })
    },
    onSuccess: (data) => queryClient.setQueryData(['profile'], data),
  })
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<FormValues>({ resolver: zodResolver(profileSchema) })

  useEffect(() => {
    if (profile.data) {
      const { full_name, date_of_birth, phone_number, address } = profile.data
      reset({ full_name, date_of_birth, phone_number, address: address ?? '' })
    }
  }, [profile.data, reset])

  if (profile.isLoading) return <Spinner />
  if (profile.error) return <ErrorAlert error={profile.error} />

  return (
    <div className="mx-auto max-w-2xl">
      <Panel
        header={
          <>
            <h1 className="page-title">My profile</h1>
            <p className="caption mt-2">
              Patient ID <span className="font-mono font-semibold text-ink">{profile.data?.id}</span> · {profile.data?.email}
            </p>
          </>
        }
      >
        <form className="space-y-5" onSubmit={handleSubmit((v) => save.mutate(v))} noValidate>
          <Field label="Full name" hint="As shown on your ID" error={errors.full_name?.message}>
            <input className="input" {...register('full_name')} />
          </Field>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Date of birth" hint="Hospitals use it to find your medical record" error={errors.date_of_birth?.message}>
              <input className="input" type="date" {...register('date_of_birth')} />
            </Field>
            <Field label="Phone number" hint="So the hospital can reach you about a visit" error={errors.phone_number?.message}>
              <input className="input" type="tel" {...register('phone_number')} />
            </Field>
          </div>
          <Field label="Address (optional)" error={errors.address?.message}>
            <input className="input" {...register('address')} />
          </Field>
          <ErrorAlert error={save.error} />
          {save.isSuccess && !isDirty && <Notice tone="success">Profile saved.</Notice>}
          <button className="btn-primary" disabled={save.isPending || !isDirty}>
            {save.isPending ? 'Saving…' : 'Save changes'}
          </button>
        </form>
      </Panel>
    </div>
  )
}
