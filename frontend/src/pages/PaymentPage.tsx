import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { StatusBadge } from '../components/StatusBadge'
import { Card, ErrorAlert, Spinner } from '../components/ui'
import { formatMoney } from '../lib/format'

// PHASE 0 STUB - owned by S3-B (docs/sprint3-sepay-plan.md, section 4 "Session B").
export default function PaymentPage() {
  const id = Number(useParams().paymentId)
  const payment = useQuery({ queryKey: ['payment', id], queryFn: () => api.payments.get(id) })
  if (payment.isLoading) return <Spinner />
  if (payment.error) return <ErrorAlert error={payment.error} />
  const p = payment.data!
  return (
    <Card className="mx-auto max-w-lg space-y-4">
      <h1 className="page-title">Payment {p.booking_reference}</h1>
      <StatusBadge status={p.status} kind="payment" />
      <img src={p.qr_image_url} alt={`VietQR for ${p.payment_code}`} className="mx-auto w-64" />
      <p>
        {formatMoney(p.amount, p.currency)} · {p.bank_code} {p.account_number} · {p.payment_code}
      </p>
      <Link to={`/appointments/${p.appointment_id}`}>View appointment</Link>
    </Card>
  )
}
