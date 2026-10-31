import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import type { PaymentStatus } from '../api/types'
import { IconAlert, IconCheck, IconClock, IconRefund, type IconComponent } from '../components/icons'
import { ErrorAlert, Spinner } from '../components/ui'
import { formatMoney } from '../lib/format'

const RESULT: Partial<Record<PaymentStatus, { title: string; className: string; icon: IconComponent }>> = {
  PAID: { title: 'Payment received', className: 'bg-success-soft text-success-strong', icon: IconCheck },
  FAILED: { title: 'Payment failed', className: 'bg-alert-soft text-alert-strong', icon: IconAlert },
  PENDING: { title: 'Waiting for confirmation', className: 'bg-notice-soft text-notice-strong', icon: IconClock },
  REFUNDED: { title: 'Payment refunded', className: 'bg-mist text-info-strong', icon: IconRefund },
}

/** Return URL from the gateway (FR-PAY-05). The result shown is the one the backend validated. */
export default function PaymentResultPage() {
  const [params] = useSearchParams()
  const paymentId = Number(params.get('payment_id'))
  const payment = useQuery({
    queryKey: ['payment', paymentId],
    queryFn: () => api.payments.get(paymentId),
    enabled: Number.isFinite(paymentId) && paymentId > 0,
    refetchInterval: (q) => (q.state.data?.status === 'PENDING' && q.state.dataUpdateCount < 15 ? 2000 : false),
  })

  if (!paymentId) return <ErrorAlert error={new Error('Missing payment reference.')} />
  if (payment.isLoading) return <Spinner label="Checking payment status…" />
  if (payment.error) return <ErrorAlert error={payment.error} />
  const p = payment.data!
  const result = RESULT[p.status] ?? { title: 'Payment result', className: 'bg-surface', icon: IconClock }
  const Icon = result.icon

  return (
    <div className="mx-auto max-w-xl">
      <section className="panel overflow-hidden border border-line">
        <div className={`flex items-start gap-4 p-6 sm:p-8 ${result.className}`}>
          <Icon size={32} />
          <div>
            <p className="eyebrow">Payment result</p>
            <h1 className="page-title">{result.title}</h1>
          </div>
        </div>
        <div className="space-y-5 p-6 sm:p-8">
          {p.status === 'PAID' && <p>Payment of {formatMoney(p.amount, p.currency)} received.</p>}
          {p.status === 'FAILED' && <p>The payment did not go through. {p.failure_reason} You can try again from your appointment.</p>}
          {p.status === 'PENDING' && <p>We are still waiting for confirmation from the payment provider. Check back shortly.</p>}
          {p.status === 'REFUNDED' && <p>This payment has been refunded.</p>}
          <p>
            Booking reference <span className="font-mono font-bold tracking-[0.1em] text-berry">{p.booking_reference}</span>
          </p>
          <Link className="btn-primary" to={`/appointments/${p.appointment_id}`}>
            View appointment
          </Link>
        </div>
      </section>
    </div>
  )
}
