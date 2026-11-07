import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useId, useMemo, useState } from 'react'
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

/** FR-BOOK-01..04: choose date and slot; the server revalidates on submit. */
export function BookingPanel({ doctor }: { doctor: DoctorDetail }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const headingId = useId()
  const dateLabelId = useId()

  const days = useMemo(() => upcomingDays(14), [])
  const [day, setDay] = useState(days[1]?.value ?? days[0].value)
  const [slot, setSlot] = useState<Slot | null>(null)
  const [reason, setReason] = useState('')
  const [idempotencyKey, setIdempotencyKey] = useState(newIdempotencyKey)

  const types = useQuery({ queryKey: ['appointment-types', doctor.id], queryFn: () => api.directory.appointmentTypes(doctor.id) })
  const selectedType = types.data?.[0]

  const availability = useQuery({
    queryKey: ['availability', doctor.id, selectedType?.id, day],
    queryFn: () => api.directory.availability(doctor.id, day, selectedType?.id),
    enabled: !!selectedType,
  })
  const manual = availability.data?.source === 'manual-slots'
  useEffect(() => {
    if (slot && availability.data && !availability.data.slots.some((offer) =>
      offer.start_time === slot.start_time && offer.slot_id === slot.slot_id && offer.version === slot.version
    )) setSlot(null)
  }, [availability.data, slot])

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
          slot_id: slot?.slot_id ?? undefined,
          slot_version: slot?.version ?? undefined,
          reason_for_visit: reason.trim() || undefined,
        },
        idempotencyKey,
      ),
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['availability', doctor.id] })
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

  const fee = selectedType?.fee ?? '0'
  const step = slot ? 4 : 3

  return (
    <section className="panel border border-line bg-canvas" aria-labelledby={headingId}>
      <div className="border-b border-line px-5 py-5 sm:px-6">
        <p className="eyebrow" aria-live="polite">
          Step {step} of {STEPS.length} · {STEPS[step - 1]}
        </p>
        <h2 id={headingId} className="mt-1 text-h2 font-semibold">
          Book an appointment
        </h2>
        <div className="mt-4 grid grid-cols-5 gap-1.5" aria-hidden="true">
          {STEPS.map((s, i) => (
            <span key={s} className={`h-1.5 rounded-full transition-colors duration-slow ${i < step ? 'bg-berry' : 'bg-blush'}`} />
          ))}
        </div>
      </div>

      <div className="space-y-6 p-5 sm:p-6">
        {types.isLoading && <Spinner />}
        {selectedType && (
          <div className="flex items-center justify-between rounded-lg border border-line bg-surface px-4 py-3">
            <div>
              <p className="text-caption font-semibold text-muted">Consultation fee</p>
              <p className="text-base font-semibold text-ink">{formatMoney(fee, selectedType.currency)}</p>
            </div>
            {manual && (
              <span className="tag bg-blush font-semibold text-berry">
                {slot ? `${(Date.parse(slot.end_time) - Date.parse(slot.start_time)) / 60000} min` : 'Shared slots'}
              </span>
            )}
          </div>
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
          <ErrorAlert error={book.error} />
          {availability.data && availability.data.slots.length === 0 && (
            <p className="caption">No available times on this day. Try another date.</p>
          )}
          {groups.map((g) => (
            <div key={`${day}-${g.label}`} role="group" aria-label={g.label} className="animate-fade">
              <p className="text-caption font-semibold">{g.label}</p>
              <div className={`mt-2 grid gap-2 ${manual ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-3 sm:grid-cols-4'}`}>
                {g.slots.map((s) => {
                  const selected = slot?.start_time === s.start_time
                  return (
                    <button key={s.start_time} type="button" className={`slot ${manual ? 'min-w-0 flex-col px-3 py-3' : ''}`} aria-pressed={selected} onClick={() => setSlot(s)}>
                      <span className="inline-flex items-center justify-center gap-1 whitespace-nowrap">
                        {selected && <span aria-hidden="true" className="check-pop">✓</span>}
                        <span>{formatTime(s.start_time)}{s.slot_id != null && `–${formatTime(s.end_time)}`}</span>
                      </span>
                      {s.remaining_places != null && <span className="mt-1 block text-caption">{s.remaining_places} {s.remaining_places === 1 ? 'place' : 'places'} left</span>}
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
          <div className="reveal space-y-5 border-t border-line pt-6">
            <Field label="Reason for visit (optional)" hint="Helps the doctor prepare. Only the hospital sees it.">
              <textarea className="input" rows={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
            </Field>
            <dl className="divide-y divide-line overflow-hidden rounded-lg border border-line">
              <div className="flex justify-between gap-4 px-4 py-3">
                <dt className="text-muted">When</dt>
                <dd className="text-right">{formatDateTime(slot.start_time)}{manual && `–${formatTime(slot.end_time)}`}</dd>
              </div>
              <div className="flex justify-between gap-4 bg-surface px-4 py-3">
                <dt className="font-semibold">Consultation fee</dt>
                <dd className="text-right font-semibold">{formatMoney(fee, selectedType.currency)}</dd>
              </div>
            </dl>
            <p className="caption">{manual
              ? 'CareBook confirms this reservation immediately when a place is available.'
              : 'Your request goes to the hospital first. We confirm it as soon as they accept.'}</p>
            {/* Primary action sticks to the bottom on small screens. */}
            <div className="sticky bottom-0 -mx-5 -mb-5 border-t border-line bg-canvas px-5 py-3 sm:-mx-6 sm:-mb-6 sm:px-6 lg:static lg:m-0 lg:border-0 lg:p-0">
              {user?.role === 'PATIENT' ? (
                <button className="btn-primary w-full" disabled={book.isPending} onClick={() => book.mutate()}>
                  {book.isPending ? 'Submitting…' : manual ? 'Book appointment' : 'Request booking'}
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
