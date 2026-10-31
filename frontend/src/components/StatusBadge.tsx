import type { AppointmentStatus, CheckInStatus, PaymentStatus } from '../api/types'
import { humanize } from '../lib/format'
import { IconAlert, IconCheck, IconClock, IconMinus, IconRefund, IconX, type IconComponent } from './icons'

// Status = colour + icon + word. Bright fills carry black text; only Alert red carries white.
const STYLES: Record<string, { className: string; icon: IconComponent }> = {
  PENDING: { className: 'bg-sun', icon: IconClock },
  CONFIRMED: { className: 'bg-mint', icon: IconCheck },
  COMPLETED: { className: 'bg-sky', icon: IconCheck },
  REJECTED: { className: 'bg-alert text-white', icon: IconX },
  CANCELLED: { className: 'bg-white', icon: IconX },
  NO_SHOW: { className: 'bg-white', icon: IconX },
  UNPAID: { className: 'bg-white', icon: IconMinus },
  PAID: { className: 'bg-mint', icon: IconCheck },
  FAILED: { className: 'bg-alert text-white', icon: IconAlert },
  REFUNDED: { className: 'bg-white', icon: IconRefund },
  CHECKED_IN: { className: 'bg-mint', icon: IconCheck },
  NOT_CHECKED_IN: { className: 'bg-white', icon: IconMinus },
  PUBLISHED: { className: 'bg-mint', icon: IconCheck },
  HIDDEN: { className: 'bg-white', icon: IconMinus },
  REMOVED: { className: 'bg-white', icon: IconX },
}
const FALLBACK = { className: 'bg-white', icon: IconMinus }

// FR-BOOK-07: always say clearly what a status means for the patient.
const LABELS: Record<string, string> = {
  PENDING: 'Awaiting hospital confirmation',
  CONFIRMED: 'Confirmed',
  NOT_CHECKED_IN: 'Not checked in',
  CHECKED_IN: 'Checked in',
  NO_SHOW: 'Missed',
}

export function StatusBadge({
  status,
  kind,
}: {
  status: AppointmentStatus | PaymentStatus | CheckInStatus | string
  kind?: 'payment' | 'check-in'
}) {
  const prefix = kind === 'payment' ? 'Payment: ' : ''
  const label = kind === 'payment' ? humanize(status) : (LABELS[status] ?? humanize(status))
  const { className, icon: Icon } = STYLES[status] ?? FALLBACK
  return (
    <span className={`badge ${className}`}>
      <Icon size={16} />
      {prefix}
      {label}
    </span>
  )
}
