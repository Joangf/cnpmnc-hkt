import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useId, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api/endpoints'
import { ApiError } from '../api/http'
import type { DoctorDetail, Slot } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { formatDateTime, formatMoney, formatTime, upcomingDays } from '../lib/format'
import { newIdempotencyKey } from '../lib/ids'
import { ErrorAlert, Field, Notice, Spinner } from './ui'

// Booking flow (design board 03): 1 Find care · 2 Choose doctor · 3 Pick a time · 4 Your details · 5 Confirm.
const STEPS = ['Find care', 'Choose doctor', 'Pick a time', 'Your details', 'Confirm']

/** FR-BOOK-01..04: choose type, date and slot; the server revalidates on submit. */
export function BookingPanel({ doctor }: { doctor: DoctorDetail }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const headingId = useId()
  const dateLabelId = useId()

  const days = useMemo(() => upcomingDays(14), [])
  const [typeId, setTypeId] = useState<number | null>(null)
  const [day, setDay] = useState(days[1]?.value ?? days[0].value)
  const [slot, setSlot] = useState<Slot | null>(null)
  const [reason, setReason] = useState('')
  const [idempotencyKey, setIdempotencyKey] = useState(newIdempotencyKey)

  const types = useQuery({ queryKey: ['appointment-types', doctor.id], queryFn: () => api.directory.appointmentTypes(doctor.id) })
  const selectedType = types.data?.find((t) => t.id === typeId) ?? types.data?.[0]

  const availability = useQuery({
    queryKey: ['availability', doctor.id, selectedType?.id, day],
    queryFn: () => api.directory.availability(doctor.id, day, selectedType!.id),
    enabled: !!selectedType,
  })

  const groups = useMemo(() => {
    const morning: Slot[] = []
    const afternoon: Slot[] = []
    for (const s of availability.data?.slots ?? []) (Number(formatTime(s.start_time).slice(0, 2)) < 12 ? morning : afternoon).push(s)
    return [
      { label: 'Morning', slots: morning },
      { label: 'Afternoon', slots: afternoon },
    ].filter((g) => g.slots.length > 0)
  }, [availability.data])

  const book = useMutation({
    mutationFn: () =>
      api.appointments.create(
        {
          doctor_id: doctor.id,
          appointment_type_id: selectedType!.id,
          start_time: slot!.start_time,
          reason_for_visit: reason.trim() || undefined,
        },
        idempotencyKey,
      ),
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      navigate(`/appointments/${appointment.id}`)
    },
    onError: (err) => {
      setIdempotencyKey(newIdempotencyKey())
      if (err instanceof ApiError && err.status === 409) {
        setSlot(null)
        availability.refetch()
      }
    },
  })

  const fee = selectedType?.fee ?? doctor.consultation_fee
  const step = slot ? 4 : 3

  return (
    <section className="border-3 border-ink bg-white" aria-labelledby={headingId}>
      <div className="border-b-3 border-ink px-5 py-5 sm:px-6">
        <p className="eyebrow text-sm" aria-live="polite">
          Step {step} of {STEPS.length} · {STEPS[step - 1]}
        </p>
        <h2 id={headingId} className="mt-1 text-h2 font-extrabold">
          Book an appointment
        </h2>
        <div className="mt-4 grid grid-cols-5 gap-1.5" aria-hidden="true">
          {STEPS.map((s, i) => (
            <span key={s} className={`h-2.5 border-2 border-ink ${i < step ? 'bg-ink' : 'bg-white'}`} />
          ))}
        </div>
      </div>

      <div className="space-y-6 p-5 sm:p-6">
        {types.isLoading && <Spinner />}
        {types.data && types.data.length === 0 && <Notice>This doctor has no bookable appointment types.</Notice>}
        {types.data && types.data.length > 0 && (
          <Field label="Appointment type">
            <select
              className="input"
              value={selectedType?.id}
              onChange={(e) => {
                setTypeId(Number(e.target.value))
                setSlot(null)
              }}
            >
              {types.data.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} · {t.duration_minutes} min · {formatMoney(t.fee, t.currency)}
                </option>
              ))}
            </select>
          </Field>
        )}

        <div>
          <p id={dateLabelId} className="label">
            Date
          </p>
          <div role="group" aria-labelledby={dateLabelId} className="mt-2 flex gap-2 overflow-x-auto pb-2">
            {days.map((d) => (
              <button
                key={d.value}
                type="button"
                className="day"
                aria-label={d.label}
                aria-pressed={d.value === day}
                onClick={() => {
                  setDay(d.value)
                  setSlot(null)
                }}
              >
                <span>{d.weekday}</span>
                <span>{d.dayMonth}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <p className="label">Available times</p>
          {availability.isLoading && <Spinner />}
          <ErrorAlert error={availability.error} />
          {availability.data && availability.data.slots.length === 0 && (
            <p className="caption">No available times on this day. Try another date.</p>
          )}
          {groups.map((g) => (
            <div key={g.label} role="group" aria-label={g.label}>
              <p className="eyebrow text-[0.9375rem]">{g.label}</p>
              <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-4">
                {g.slots.map((s) => {
                  const selected = slot?.start_time === s.start_time
                  return (
                    <button key={s.start_time} type="button" className="slot" aria-pressed={selected} onClick={() => setSlot(s)}>
                      {formatTime(s.start_time)}
                      {selected && <span aria-hidden="true">✓</span>}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
          {availability.data && availability.data.slots.length > 0 && (
            <p className="caption">
              {availability.data.slots.length} {availability.data.slots.length === 1 ? 'time' : 'times'} available on this day
            </p>
          )}
        </div>

        {slot && selectedType && (
          <div className="space-y-5 border-t-3 border-ink pt-6">
            <Field label="Reason for visit (optional)" hint="Helps the doctor prepare. Only the hospital sees it.">
              <textarea className="input" rows={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
            </Field>
            <dl className="divide-y divide-ink border-3 border-ink">
              <div className="flex justify-between gap-4 px-4 py-3">
                <dt className="font-extrabold">When</dt>
                <dd className="text-right">{formatDateTime(slot.start_time)}</dd>
              </div>
              <div className="flex justify-between gap-4 px-4 py-3">
                <dt className="font-extrabold">Type</dt>
                <dd className="text-right">{selectedType.name}</dd>
              </div>
              <div className="flex justify-between gap-4 bg-grey-100 px-4 py-3">
                <dt className="font-extrabold">Total fee</dt>
                <dd className="text-right font-extrabold">{formatMoney(fee, doctor.currency)}</dd>
              </div>
            </dl>
            <p className="caption">Your request goes to the hospital first. We confirm it as soon as they accept.</p>
            <ErrorAlert error={book.error} />
            {/* Primary action sticks to the bottom on small screens. */}
            <div className="sticky bottom-0 -mb-2 bg-white py-2 lg:static">
              {user?.role === 'PATIENT' ? (
                <button className="btn-primary w-full" disabled={book.isPending} onClick={() => book.mutate()}>
                  {book.isPending ? 'Submitting…' : 'Request booking'}
                </button>
              ) : user ? (
                <Notice>Only patient accounts can book appointments.</Notice>
              ) : (
                <Link className="btn-primary w-full" to={`/login?next=${encodeURIComponent(`${location.pathname}#book`)}`}>
                  Sign in to book
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
