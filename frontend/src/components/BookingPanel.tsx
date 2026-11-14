import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useId, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api/endpoints'
import { ApiError } from '../api/http'
import type { DoctorDetail, Slot } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { clinicIsoDay, formatDateTime, formatMoney, formatTime, humanize, upcomingDays } from '../lib/format'
import { newIdempotencyKey } from '../lib/ids'
import { ErrorAlert, Field, Notice, RequiredMark, Spinner } from './ui'

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
  const [nowMs, setNowMs] = useState(() => Date.now())

  useEffect(() => {
    const id = window.setInterval(() => setNowMs(Date.now()), 15_000)
    return () => window.clearInterval(id)
  }, [])

  const types = useQuery({ queryKey: ['appointment-types', doctor.id], queryFn: () => api.directory.appointmentTypes(doctor.id) })
  const selectedType = types.data?.[0]

  const availability = useQuery({
    queryKey: ['availability', doctor.id, selectedType?.id, day],
    queryFn: () => api.directory.availability(doctor.id, day, selectedType?.id),
    enabled: !!selectedType,
    refetchInterval: 15_000,
  })
  const myUpcoming = useQuery({
    queryKey: ['appointments', 'upcoming', 'booking-check'],
    queryFn: () => api.appointments.list('upcoming', 1),
    enabled: user?.role === 'PATIENT',
  })
  const activeAppointments = useMemo(
    () => (myUpcoming.data?.items ?? []).filter((a) => a.status === 'PENDING' || a.status === 'CONFIRMED'),
    [myUpcoming.data],
  )
  const sameDayAppt = useMemo(
    () => activeAppointments.find((a) => a.doctor.id === doctor.id && clinicIsoDay(a.start_time) === day) ?? null,
    [activeAppointments, doctor.id, day],
  )
  const overlappingAppt = useMemo(() => {
    if (!slot) return null
    const sStart = Date.parse(slot.start_time)
    const sEnd = Date.parse(slot.end_time)
    return (
      activeAppointments.find(
        (a) => a.doctor.id !== doctor.id && Date.parse(a.start_time) < sEnd && Date.parse(a.end_time) > sStart,
      ) ?? null
    )
  }, [activeAppointments, doctor.id, slot])

  const manual = availability.data?.source === 'erp-slots'
  const leadCutMs = nowMs + 60 * 60_000
  useEffect(() => {
    if (
      slot &&
      availability.data &&
      !availability.data.slots.some(
        (offer) =>
          offer.start_time === slot.start_time &&
          offer.slot_id === slot.slot_id &&
          offer.version === slot.version &&
          !offer.is_past &&
          Date.parse(offer.start_time) >= leadCutMs &&
          (offer.remaining_places == null || offer.remaining_places > 0),
      )
    ) {
      setSlot(null)
    }
  }, [availability.data, leadCutMs, slot])

  const groups = useMemo(() => {
    const morning: Slot[] = []
    const afternoon: Slot[] = []
    for (const s of availability.data?.slots ?? []) (Number(formatTime(s.start_time).slice(0, 2)) < 12 ? morning : afternoon).push(s)
    return [
      { label: 'Morning', slots: morning },
      { label: 'Afternoon', slots: afternoon },
    ].filter((g) => g.slots.length > 0)
  }, [availability.data])

  const openSlotsCount = useMemo(
    () =>
      (availability.data?.slots ?? []).filter(
        (s) => !s.is_past && Date.parse(s.start_time) >= leadCutMs && (s.remaining_places == null || s.remaining_places > 0),
      ).length,
    [availability.data, leadCutMs],
  )

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
        if (err.code === 'AlreadyBookedSameDay' || err.code === 'PatientTimeConflict') {
          queryClient.invalidateQueries({ queryKey: ['appointments'] })
        } else {
          setSlot(null)
        }
        availability.refetch()
      }
    },
  })

  const fee = selectedType?.fee ?? '0'

  return (
    <section className="panel border border-line bg-canvas" aria-labelledby={headingId}>
      <div className="border-b border-line px-5 py-5 sm:px-6">
        <h2 id={headingId} className="text-h2 font-semibold">
          Request an appointment
        </h2>
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
            <RequiredMark />
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
          <p className="label">
            Available times
            <RequiredMark />
          </p>
          {availability.isLoading && <Spinner />}
          <ErrorAlert error={availability.error} />
          <ErrorAlert error={book.error} />
          {sameDayAppt && (
            <Notice tone="warning" title="Existing appointment on this day">
              <p>
                You already have an appointment with this doctor on this date ({formatTime(sameDayAppt.start_time)}–{formatTime(sameDayAppt.end_time)}, {humanize(sameDayAppt.status)}). Cancel your existing appointment before booking a new one.
              </p>
              <Link className="mt-2 inline-block font-semibold underline" to={`/appointments/${sameDayAppt.id}`}>
                View or cancel existing appointment →
              </Link>
            </Notice>
          )}
          {availability.data && availability.data.slots.length === 0 && (
            <p className="caption">No available times on this day. Try another date.</p>
          )}
          {groups.map((g) => (
            <div key={`${day}-${g.label}`} role="group" aria-label={g.label} className="animate-fade">
              <p className="text-caption font-semibold">{g.label}</p>
              <div className="mt-2 grid grid-cols-2 gap-2.5">
                {g.slots.map((s) => {
                  const selected = slot?.start_time === s.start_time
                  const isFull = s.remaining_places !== null && s.remaining_places !== undefined && s.remaining_places <= 0
                  const isPassed = Boolean(s.is_past) || Date.parse(s.start_time) < leadCutMs
                  const isDisabled = isFull || isPassed
                  const showRange = s.slot_id != null || s.capacity != null || (s.end_time && s.end_time !== s.start_time)
                  return (
                    <button
                      key={s.start_time}
                      type="button"
                      disabled={isDisabled}
                      className={`slot ${
                        isDisabled
                          ? 'opacity-45 bg-mist/60 cursor-not-allowed border-dashed text-muted hover:border-line hover:bg-mist/60'
                          : ''
                      }`}
                      aria-pressed={selected}
                      onClick={() => !isDisabled && setSlot(s)}
                    >
                      <span className="inline-flex max-w-full items-center justify-center gap-1 whitespace-nowrap text-[0.9375rem] font-semibold leading-tight">
                        {selected && <span aria-hidden="true" className="check-pop shrink-0">✓</span>}
                        <span className={isDisabled ? 'line-through' : ''}>
                          {formatTime(s.start_time)}{showRange && `–${formatTime(s.end_time)}`}
                        </span>
                      </span>
                      {(isPassed || s.remaining_places != null) && (
                        <span className={`block max-w-full truncate text-xs leading-tight ${isDisabled ? 'text-muted font-normal' : 'text-ink-2'}`}>
                          {isPassed
                            ? 'Passed'
                            : isFull
                              ? '0 slots'
                              : `${s.remaining_places} ${s.remaining_places === 1 ? 'slot' : 'slots'} left`}
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
          {availability.data && availability.data.slots.length > 0 && (
            <p className="caption">
              {openSlotsCount} {openSlotsCount === 1 ? 'time window' : 'time windows'} available on this day
            </p>
          )}
        </div>

        {slot && selectedType && (
          <div className="reveal space-y-5 border-t border-line pt-6">
            {overlappingAppt && (
              <Notice tone="warning" title="Overlapping appointment">
                <p>
                  You already have an appointment with {overlappingAppt.doctor.name} at {formatTime(overlappingAppt.start_time)}–{formatTime(overlappingAppt.end_time)}. Cancel it first or pick another time.
                </p>
                <Link className="mt-2 inline-block font-semibold underline" to={`/appointments/${overlappingAppt.id}`}>
                  View or cancel overlapping appointment →
                </Link>
              </Notice>
            )}
            <Field label="Reason for visit" hint="Helps the doctor prepare. Only the hospital sees it.">
              <textarea className="input" rows={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
            </Field>
            <dl className="divide-y divide-line overflow-hidden rounded-lg border border-line">
              <div className="flex justify-between gap-4 px-4 py-3">
                <dt className="text-muted">When</dt>
                <dd className="text-right">{formatDateTime(slot.start_time)}{slot.end_time && `–${formatTime(slot.end_time)}`}</dd>
              </div>
              <div className="flex justify-between gap-4 bg-surface px-4 py-3">
                <dt className="font-semibold">Consultation fee</dt>
                <dd className="text-right font-semibold">{formatMoney(fee, selectedType.currency)}</dd>
              </div>
            </dl>
            <p className="caption">{fee && Number(fee) > 0
              ? 'This appointment will be held for 15 minutes for you to complete payment. You will go straight to appointment details and payment.'
              : 'Your request goes to the hospital first. We confirm it as soon as they accept.'}</p>
            {/* Primary action sticks to the bottom on small screens. */}
            <div className="sticky bottom-0 -mx-5 -mb-5 border-t border-line bg-canvas px-5 py-3 sm:-mx-6 sm:-mb-6 sm:px-6 lg:static lg:m-0 lg:border-0 lg:p-0">
              {user?.role === 'PATIENT' ? (
                <button
                  className="btn-primary w-full"
                  disabled={book.isPending || !!sameDayAppt || !!overlappingAppt}
                  onClick={() => book.mutate()}
                >
                  {book.isPending ? 'Submitting…' : 'Request appointment'}
                </button>
              ) : user ? (
                <Notice>Only patient accounts can book appointments.</Notice>
              ) : (
                <Link className="btn-primary w-full" to={`/login?next=${encodeURIComponent(`${location.pathname}#book`)}`}>
                  Sign in to request
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
