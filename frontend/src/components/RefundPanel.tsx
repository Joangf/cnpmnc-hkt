import type { AppointmentDetail } from '../api/types'

// PHASE 0 STUB - owned by S3-C (docs/sprint3-sepay-plan.md, section 4 "Session C").
// Shown on the appointment page; renders nothing unless a refund can be requested or exists.
export function RefundPanel({ appointment }: { appointment: AppointmentDetail; onDone: () => void }) {
  if (!appointment.can_request_refund) return null
  return null
}
