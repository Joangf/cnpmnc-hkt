import type { AppointmentStatus, CheckInStatus, PaymentStatus } from '../api/types'
import { humanize } from '../lib/format'
import { IconCheck, IconClock, IconMinus, IconRefund, IconX, type IconComponent } from './icons'

// Status = colour + icon + word, on soft tints (strong colour is for urgent help only).
const GOOD = 'bg-success-soft text-success'
const WAIT = 'bg-notice-soft text-notice'
const BAD = 'bg-alert-soft text-alert'
const INFO = 'bg-mist text-info'
const NEUTRAL = 'bg-surface text-muted'
const STYLES: Record<string, { className: string; icon: IconComponent }> = {
  PENDING: { className: WAIT, icon: IconClock },
  CONFIRMED: { className: GOOD, icon: IconCheck },
  COMPLETED: { className: INFO, icon: IconCheck },
  REJECTED: { className: BAD, icon: IconX },
  CANCELLED: { className: NEUTRAL, icon: IconX },
  NO_SHOW: { className: NEUTRAL, icon: IconX },
  UNPAID: { className: NEUTRAL, icon: IconMinus },
  PAID: { className: GOOD, icon: IconCheck },
  EXPIRED: { className: NEUTRAL, icon: IconClock },
  REQUESTED: { className: WAIT, icon: IconClock },
  REFUNDED: { className: INFO, icon: IconRefund },
  CHECKED_IN: { className: GOOD, icon: IconCheck },
  NOT_CHECKED_IN: { className: NEUTRAL, icon: IconMinus },
  PUBLISHED: { className: GOOD, icon: IconCheck },
  HIDDEN: { className: NEUTRAL, icon: IconMinus },
  REMOVED: { className: NEUTRAL, icon: IconX },
}
const FALLBACK = { className: NEUTRAL, icon: IconMinus }

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
