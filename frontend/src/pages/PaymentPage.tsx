import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import type { Payment } from '../api/types'
import { IconArrowLeft, IconCheck, IconClock } from '../components/icons'
import { StatusBadge } from '../components/StatusBadge'
import { ErrorAlert, Notice, Spinner } from '../components/ui'
import { formatDateTime, formatMoney } from '../lib/format'

/** VietQR bank transfer (SCRUM-27/30). The page polls until the bank reports the money (SePay). */
export default function PaymentPage() {
  const id = Number(useParams().paymentId)
  const payment = useQuery({
    queryKey: ['payment', id],
    queryFn: () => api.payments.get(id),
    // Money can still arrive for an expired code (it is then recorded as PAID), so keep an eye on it for ~10 min.
    refetchInterval: (q) =>
      q.state.data?.status === 'PENDING' ? 3000 : q.state.data?.status === 'EXPIRED' && q.state.dataUpdateCount < 60 ? 10000 : false,
  })

  // A payment status change also changes the appointment (payment_status, can_pay, can_request_refund).
  const queryClient = useQueryClient()
  const appointmentId = payment.data?.appointment_id
  const status = payment.data?.status
  useEffect(() => {
    if (!appointmentId) return
    queryClient.invalidateQueries({ queryKey: ['appointment', appointmentId] })
    queryClient.invalidateQueries({ queryKey: ['appointments'] })
  }, [queryClient, appointmentId, status])

  if (payment.isLoading) return <Spinner />
  // A failed refetch keeps the last known payment on screen; only a first-load failure is fatal.
  if (!payment.data) return <ErrorAlert error={payment.error} />
  const p = payment.data

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link to={`/appointments/${p.appointment_id}`} className="link inline-flex min-h-12 items-center gap-2">
        <IconArrowLeft size={20} /> Back to appointment
      </Link>

      {payment.error && (
        <div className="space-y-3">
          <ErrorAlert error={payment.error} />
          <button className="btn-secondary btn-sm" onClick={() => payment.refetch()} disabled={payment.isFetching}>
            {payment.isFetching ? 'Retrying…' : 'Try again'}
          </button>
        </div>
      )}

      {p.status === 'PENDING' && <PendingTransfer payment={p} />}
      {p.status === 'PAID' && <Paid payment={p} />}
      {p.status === 'EXPIRED' && <Expired payment={p} />}
      {p.status === 'REFUNDED' && (
        <Notice tone="info" title="This payment has been refunded">
          {formatMoney(p.amount, p.currency)} was sent back{p.refunded_at ? ` on ${formatDateTime(p.refunded_at)}` : ''}.
        </Notice>
      )}
    </div>
  )
}

function PendingTransfer({ payment: p }: { payment: Payment }) {
  const left = useSecondsLeft(p.expires_at)
  return (
    <section className="panel overflow-hidden border border-line">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-6 sm:p-8">
        <div>
          <p className="eyebrow">Booking {p.booking_reference}</p>
          <h1 className="page-title">Pay by bank transfer</h1>
        </div>
        <StatusBadge status={p.status} kind="payment" />
      </div>

      <div className="grid gap-6 p-6 sm:p-8 md:grid-cols-[auto_1fr]">
        <div className="flex flex-col items-center gap-3">
          <img
            src={p.qr_image_url}
            alt={`VietQR code: transfer ${formatMoney(p.amount, p.currency)} with content ${p.payment_code}`}
            className="h-64 w-64 rounded-md border border-line bg-white object-contain p-2"
          />
          <p className="caption text-center">Scan with your banking app</p>
        </div>

        <div className="min-w-0 space-y-4">
          <dl className="divide-y divide-line rounded-md border border-line">
            <CopyRow label="Bank" value={p.bank_code} />
            <CopyRow label="Account number" value={p.account_number} />
            <CopyRow label="Account name" value={p.account_name} />
            <CopyRow label="Amount" display={formatMoney(p.amount, p.currency)} value={String(Number(p.amount))} />
            <CopyRow label="Transfer content" value={p.payment_code} emphasis />
          </dl>
          <p className="caption">
            Keep the transfer content exactly <strong className="font-mono">{p.payment_code}</strong>, otherwise we cannot match your payment.
          </p>
        </div>
      </div>

      <div className="space-y-4 border-t border-line p-6 sm:p-8">
        {p.failure_reason && (
          <Notice tone="danger" title="We received a transfer we could not accept">
            {p.failure_reason}
          </Notice>
        )}
        {left === null ? null : left > 0 ? (
          <Notice tone="warning" title={`Time left: ${formatCountdown(left)}`}>
            Pay before {formatDateTime(p.expires_at!)} to keep your appointment.
          </Notice>
        ) : (
          <Notice tone="warning" title="Time is up">
            If you have already transferred, the payment is still recorded when the bank reports it. Otherwise the appointment will be
            released shortly.
          </Notice>
        )}
        <p className="flex items-center gap-2 text-muted" role="status">
          <IconClock size={18} /> Waiting for the bank. We confirm the payment only when the bank reports the money has arrived. This
          page updates automatically.
        </p>
      </div>
    </section>
  )
}

function Paid({ payment: p }: { payment: Payment }) {
  const appointment = useQuery({
    queryKey: ['appointment', p.appointment_id],
    queryFn: () => api.appointments.get(p.appointment_id),
  })
  const a = appointment.data
  const closed = a && (a.status === 'CANCELLED' || a.status === 'REJECTED')
  return (
    <section className="panel overflow-hidden border border-line">
      <div className="flex items-start gap-4 bg-success-soft p-6 text-success-strong sm:p-8">
        <IconCheck size={32} />
        <div>
          <p className="eyebrow">Booking {p.booking_reference}</p>
          <h1 className="page-title">Payment received</h1>
        </div>
      </div>
      <div className="space-y-5 p-6 sm:p-8">
        <p>
          We received {formatMoney(p.amount, p.currency)}
          {p.paid_at ? ` on ${formatDateTime(p.paid_at)}` : ''}.{closed ? '' : ' Your appointment is paid.'}
        </p>
        {closed && (
          <Notice tone="warning" title={a.status === 'CANCELLED' ? 'The appointment was already cancelled' : 'The appointment was declined'}>
            {a.can_request_refund
              ? 'You can request a full refund from the appointment page.'
              : 'Please contact the hospital about this payment.'}
          </Notice>
        )}
        <Link className="btn-primary" to={`/appointments/${p.appointment_id}`}>
          View appointment
        </Link>
      </div>
    </section>
  )
}

function Expired({ payment: p }: { payment: Payment }) {
  const navigate = useNavigate()
  const appointment = useQuery({
    queryKey: ['appointment', p.appointment_id],
    queryFn: () => api.appointments.get(p.appointment_id),
  })
  const pay = useMutation({
    mutationFn: () => api.appointments.pay(p.appointment_id),
    onSuccess: (res) => navigate(`/payments/${res.id}`),
  })
  const a = appointment.data

  return (
    <section className="panel space-y-5 border border-line p-6 sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="eyebrow">Booking {p.booking_reference}</p>
          <h1 className="page-title">This payment code has expired</h1>
        </div>
        <StatusBadge status={p.status} kind="payment" />
      </div>
      <p>
        Code <span className="font-mono font-bold">{p.payment_code}</span> can no longer be used. Do not transfer money with it.
      </p>
      {appointment.isLoading && <Spinner />}
      <ErrorAlert error={appointment.error} />
      {a &&
        (a.can_pay ? (
          <button className="btn-primary" disabled={pay.isPending} onClick={() => pay.mutate()}>
            {pay.isPending ? 'Preparing…' : 'Create a new code'}
          </button>
        ) : a.payment_status === 'PAID' ? (
          <Notice tone="success">This appointment is already paid.</Notice>
        ) : a.status === 'CANCELLED' ? (
          <Notice tone="warning" title="The appointment was cancelled">
            {a.status_reason ?? 'Payment was not received in time.'}
          </Notice>
        ) : (
          <Notice tone="info">This appointment can no longer be paid online.</Notice>
        ))}
      <ErrorAlert error={pay.error} />
    </section>
  )
}

function CopyRow({ label, value, display, emphasis }: { label: string; value: string; display?: string; emphasis?: boolean }) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle')
  useEffect(() => {
    if (state === 'idle') return
    const t = setTimeout(() => setState('idle'), 2000)
    return () => clearTimeout(t)
  }, [state])
  const copy = () =>
    navigator.clipboard
      .writeText(value)
      .then(() => setState('copied'))
      .catch(() => setState('failed'))

  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3">
      <div className="min-w-0">
        <dt className="label">{label}</dt>
        <dd className={`break-all font-semibold ${emphasis ? 'font-mono text-h2 tracking-[0.1em] text-berry' : ''}`}>{display ?? value}</dd>
      </div>
      <button type="button" className="btn-secondary btn-sm shrink-0" onClick={copy} aria-label={`Copy ${label.toLowerCase()}`}>
        {state === 'copied' ? 'Copied' : state === 'failed' ? 'Copy failed' : 'Copy'}
      </button>
    </div>
  )
}

/** Seconds until `iso`, ticking every second; null when there is no deadline. */
function useSecondsLeft(iso: string | null): number | null {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!iso) return
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [iso])
  if (!iso) return null
  return Math.max(0, Math.floor((new Date(iso).getTime() - now) / 1000))
}

function formatCountdown(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}
