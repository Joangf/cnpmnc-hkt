import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import type { Payment } from '../api/types'
import { BankTransferDetails } from '../components/PaymentTransferPanel'
import { IconArrowLeft, IconCheck } from '../components/icons'
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

  // A payment status change also changes the appointment (payment_status, can_pay, can_request_refund)
  // and adds notifications (bell badge).
  const queryClient = useQueryClient()
  const appointmentId = payment.data?.appointment_id
  const status = payment.data?.status
  useEffect(() => {
    if (!appointmentId) return
    queryClient.invalidateQueries({ queryKey: ['appointment', appointmentId] })
    queryClient.invalidateQueries({ queryKey: ['appointments'] })
    queryClient.invalidateQueries({ queryKey: ['notifications'] })
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
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [confirmCancel, setConfirmCancel] = useState(false)
  const cancel = useMutation({
    mutationFn: () => api.appointments.cancel(p.appointment_id, 'Cancelled by patient from payment page'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointment', p.appointment_id] })
      queryClient.invalidateQueries({ queryKey: ['payment', p.id] })
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
      queryClient.invalidateQueries({ queryKey: ['availability'] })
      navigate(`/appointments/${p.appointment_id}`)
    },
  })
  return (
    <section className="panel overflow-hidden border border-line">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-6 sm:p-8">
        <div>
          <p className="eyebrow">Booking {p.booking_reference}</p>
          <h1 className="page-title">Pay by bank transfer</h1>
        </div>
        <StatusBadge status={p.status} kind="payment" />
      </div>

      <div className="space-y-5 p-6 sm:p-8">
        <BankTransferDetails payment={p} />
        <ErrorAlert error={cancel.error} />
        <div className="border-t border-line pt-4">
          {!confirmCancel ? (
            <button type="button" className="btn-secondary btn-sm text-danger" onClick={() => setConfirmCancel(true)}>
              Cancel booking &amp; release slot (no refund)
            </button>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-surface p-4">
              <p className="text-sm font-medium">Cancel this booking and release the held slot? No payment was completed, so no refund is needed.</p>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="btn-danger btn-sm" disabled={cancel.isPending} onClick={() => cancel.mutate()}>
                  {cancel.isPending ? 'Releasing slot…' : 'Confirm cancel'}
                </button>
                <button type="button" className="btn-secondary btn-sm" onClick={() => setConfirmCancel(false)}>
                  Keep hold
                </button>
              </div>
            </div>
          )}
        </div>
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
