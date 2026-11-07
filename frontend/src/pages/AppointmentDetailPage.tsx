import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { QRCodeSVG } from 'qrcode.react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import type { AppointmentDetail } from '../api/types'
import { IconArrowLeft, IconClock } from '../components/icons'
import { RefundPanel } from '../components/RefundPanel'
import { StatusBadge } from '../components/StatusBadge'
import { Card, ErrorAlert, Field, Notice, Spinner } from '../components/ui'
import { formatDateTime, formatMoney, humanize } from '../lib/format'
import { reviewSchema } from '../lib/validation'

const SOURCE_LABELS: Record<string, string> = {
  PATIENT: 'You',
  ERP: 'Hospital',
  ADMIN: 'Administrator',
  SYSTEM: 'System',
  PLATFORM: 'CareBook',
}

export default function AppointmentDetailPage() {
  const id = Number(useParams().appointmentId)
  const queryClient = useQueryClient()
  const appointment = useQuery({
    queryKey: ['appointment', id],
    queryFn: () => api.appointments.get(id),
    // Poll while the hospital or the gateway has not answered yet (FR-APT-04).
    refetchInterval: (q) =>
      q.state.data?.status === 'PENDING' || q.state.data?.payment_status === 'PENDING' ? 5000 : false,
  })

  const refresh = (data: AppointmentDetail) => {
    queryClient.setQueryData(['appointment', id], data)
    queryClient.invalidateQueries({ queryKey: ['appointments'] })
  }

  if (appointment.isLoading) return <Spinner />
  if (appointment.error) return <ErrorAlert error={appointment.error} />
  const a = appointment.data!

  const facts = [
    { label: 'Fee', value: formatMoney(a.fee_amount, a.currency) },
    ...(a.reason_for_visit ? [{ label: 'Reason for visit', value: a.reason_for_visit }] : []),
    ...(a.can_cancel ? [{ label: 'Free cancellation until', value: formatDateTime(a.cancellation_deadline) }] : []),
  ]

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <Link to="/appointments" className="link inline-flex min-h-12 items-center gap-2">
        <IconArrowLeft size={20} /> My appointments
      </Link>

      <section className="panel overflow-hidden border border-line">
        <div className="flex flex-col md:flex-row">
          <div className="min-w-0 flex-1 space-y-2 p-6 sm:p-8">
            <p className="eyebrow">{a.appointment_type.name}</p>
            <h1 className="page-title">{formatDateTime(a.start_time)}</h1>
            <p>
              <Link className="link" to={`/doctors/${a.doctor.id}`}>
                {a.doctor.name}
              </Link>{' '}
              · {a.department.name}
            </p>
            <p className="caption">{a.hospital.name}</p>
            {/* BR-07: three independent statuses */}
            <div className="flex flex-wrap gap-2 pt-3">
              <StatusBadge status={a.status} />
              <StatusBadge status={a.payment_status} kind="payment" />
              <StatusBadge status={a.check_in_status} kind="check-in" />
            </div>
            {a.status_reason && ['REJECTED', 'CANCELLED', 'NO_SHOW'].includes(a.status) && (
              <p className="caption pt-1">Reason: {a.status_reason}</p>
            )}
          </div>
          {/* FR-CIN-01: reference to present at the hospital */}
          <div className="flex flex-col items-center justify-center gap-2 bg-blush p-6 text-center sm:p-8 md:w-72">
            <p className="eyebrow">Booking reference</p>
            {a.status === 'CONFIRMED' && (
              // Check-in QR (encodes the booking reference) for reception to scan.
              <QRCodeSVG
                value={a.booking_reference}
                size={128}
                marginSize={2}
                className="rounded-lg bg-white"
                role="img"
                aria-label={`Check-in QR code for ${a.booking_reference}`}
              />
            )}
            <p className="break-all font-mono text-[1.75rem] font-bold tracking-[0.15em] text-berry">{a.booking_reference}</p>
            <p className="caption">Show this code or QR at reception. Staff record your check-in when you arrive.</p>
          </div>
        </div>
        <dl className="grid divide-y divide-line border-t border-line sm:auto-cols-fr sm:grid-flow-col sm:divide-x sm:divide-y-0">
          {facts.map((f) => (
            <div key={f.label} className="min-w-0 p-5 sm:p-6">
              <dt className="label">{f.label}</dt>
              <dd className="mt-1 break-words font-semibold">{f.value}</dd>
            </div>
          ))}
        </dl>
      </section>

      {a.status === 'PENDING' && (
        <Notice tone="warning" title="Waiting for the hospital">
          Your request has been sent and is awaiting confirmation. This page updates automatically.
        </Notice>
      )}

      {a.can_pay && <PaymentCard appointment={a} />}
      {a.can_cancel && <CancelCard appointment={a} onDone={refresh} />}
      {/* Owned by S3-C (components/RefundPanel.tsx): renders nothing unless a refund applies. */}
      <RefundPanel appointment={a} onDone={() => appointment.refetch()} />
      {a.can_review && <ReviewCard appointmentId={a.id} onDone={() => appointment.refetch()} />}
      {a.has_review && <Notice tone="success">Thank you - you have reviewed this appointment.</Notice>}

      {a.payments.length > 0 && (
        <Card>
          <h2 className="section-title mb-3">Payments</h2>
          <ul className="divide-y divide-line">
            {a.payments.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                <span>
                  {formatDateTime(p.created_at)} · <strong>{formatMoney(p.amount, p.currency)}</strong> ·{' '}
                  <Link className="link font-mono" to={`/payments/${p.id}`}>
                    {p.payment_code}
                  </Link>
                  {p.failure_reason && <span className="caption block">{p.failure_reason}</span>}
                </span>
                <StatusBadge status={p.status} kind="payment" />
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card>
        <h2 className="section-title mb-3">History</h2>
        <ol className="divide-y divide-line">
          {a.history.map((h, i) => (
            <li key={i} className="flex flex-wrap justify-between gap-x-4 gap-y-1 py-3 first:pt-0 last:pb-0">
              <span className="font-semibold">
                {h.field === 'status' ? 'Status' : h.field === 'check_in_status' ? 'Check-in' : 'Time'}:{' '}
                {h.field === 'start_time' ? formatDateTime(h.to_value) : humanize(h.to_value)}
                {h.reason && <span className="caption block font-normal">{h.reason}</span>}
              </span>
              <span className="caption shrink-0">
                {formatDateTime(h.created_at)} · {SOURCE_LABELS[h.source] ?? humanize(h.source)}
              </span>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  )
}

function PaymentCard({ appointment }: { appointment: AppointmentDetail }) {
  const navigate = useNavigate()
  // The backend hands back the open PENDING payment if there is one, so "continue" is the same call.
  const pay = useMutation({
    mutationFn: () => api.appointments.pay(appointment.id),
    onSuccess: (res) => navigate(`/payments/${res.id}`),
  })
  const inProgress = appointment.payments.some(
    (p) => p.status === 'PENDING' && (!p.expires_at || new Date(p.expires_at).getTime() > Date.now()),
  )
  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="section-title">Payment</h2>
          <p className="mt-1">
            Amount due: <strong className="text-h2 font-semibold">{formatMoney(appointment.fee_amount, appointment.currency)}</strong>
          </p>
        </div>
        <button className="btn-primary" disabled={pay.isPending} onClick={() => pay.mutate()}>
          {pay.isPending ? 'Preparing…' : inProgress ? 'Continue payment' : 'Pay by bank transfer'}
        </button>
      </div>
      {appointment.payment_due_at && (
        <p className="flex items-center gap-2 font-semibold text-notice-strong">
          <IconClock size={18} /> Pay before {formatDateTime(appointment.payment_due_at)} to keep your appointment.
        </p>
      )}
      <ErrorAlert error={pay.error} />
    </Card>
  )
}

function CancelCard({ appointment, onDone }: { appointment: AppointmentDetail; onDone: (a: AppointmentDetail) => void }) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const cancel = useMutation({ mutationFn: () => api.appointments.cancel(appointment.id, reason.trim() || undefined), onSuccess: onDone })

  if (!open) {
    return (
      <button className="btn-secondary" onClick={() => setOpen(true)}>
        Cancel appointment
      </button>
    )
  }
  return (
    <Card className="space-y-5">
      <h2 className="section-title">Cancel this appointment?</h2>
      {appointment.payment_status === 'PAID' && (
        <p>Cancelling does not refund your payment automatically. After cancelling you can send a refund request.</p>
      )}
      <Field label="Why are you cancelling?">
        <textarea className="input" rows={2} maxLength={500} placeholder="Reason (optional)" value={reason} onChange={(e) => setReason(e.target.value)} />
      </Field>
      <ErrorAlert error={cancel.error} />
      <div className="flex flex-wrap gap-3">
        <button className="btn-danger" disabled={cancel.isPending} onClick={() => cancel.mutate()}>
          {cancel.isPending ? 'Cancelling…' : 'Confirm cancellation'}
        </button>
        <button className="btn-secondary" onClick={() => setOpen(false)}>
          Keep appointment
        </button>
      </div>
    </Card>
  )
}

function ReviewCard({ appointmentId, onDone }: { appointmentId: number; onDone: () => void }) {
  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState('')
  const [validation, setValidation] = useState<string>()
  const submit = useMutation({
    mutationFn: () => api.appointments.review(appointmentId, { rating, comment: comment.trim() || undefined }),
    onSuccess: onDone,
  })

  return (
    <Card className="space-y-5">
      <h2 className="section-title">Review your doctor</h2>
      <div className="flex gap-2" role="radiogroup" aria-label="Rating">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={rating === n}
            aria-label={`${n} star${n > 1 ? 's' : ''}`}
            className={`flex h-12 w-12 items-center justify-center rounded-md border-1.5 text-2xl transition-colors ${n <= rating ? 'border-berry bg-blush text-berry' : 'border-line bg-canvas text-muted hover:border-berry'}`}
            onClick={() => setRating(n)}
          >
            {n <= rating ? '★' : '☆'}
          </button>
        ))}
      </div>
      <Field label="Your experience (optional)">
        <textarea className="input" rows={3} maxLength={2000} placeholder="Share your experience" value={comment} onChange={(e) => setComment(e.target.value)} />
      </Field>
      {validation && <p className="field-error">{validation}</p>}
      <ErrorAlert error={submit.error} />
      <button
        className="btn-primary"
        disabled={submit.isPending}
        onClick={() => {
          const check = reviewSchema.safeParse({ rating, comment })
          setValidation(check.success ? undefined : check.error.issues[0]?.message)
          if (check.success) submit.mutate()
        }}
      >
        Submit review
      </button>
    </Card>
  )
}
