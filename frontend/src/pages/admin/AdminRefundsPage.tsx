import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api/endpoints'
import type { AdminRefund, RefundStatus } from '../../api/types'
import { StatusBadge } from '../../components/StatusBadge'
import { EmptyState, ErrorAlert, Field, FilterChip, Pagination, Spinner } from '../../components/ui'
import { formatDateTime, formatMoney, humanize } from '../../lib/format'
import { AdminNav } from './AdminNav'

// SCRUM-32: the admin pays refunds out by hand from the hospital's bank app (plan D14).
const FILTERS: (RefundStatus | '')[] = ['REQUESTED', 'COMPLETED', 'REJECTED', '']

export default function AdminRefundsPage() {
  const [status, setStatus] = useState<RefundStatus | ''>('REQUESTED')
  const [page, setPage] = useState(1)
  const [openId, setOpenId] = useState<number | null>(null)
  const refunds = useQuery({
    queryKey: ['admin', 'refunds', status, page],
    queryFn: () => api.admin.refunds({ refund_status: status || undefined, page }),
    placeholderData: keepPreviousData,
  })

  return (
    <div>
      <h1 className="page-title mb-6">Administration</h1>
      <AdminNav />
      <div className="mb-6 flex flex-wrap gap-3">
        {FILTERS.map((f) => (
          <FilterChip
            key={f || 'all'}
            pressed={f === status}
            onClick={() => {
              setStatus(f)
              setPage(1)
              setOpenId(null)
            }}
          >
            {f ? humanize(f) : 'All'}
          </FilterChip>
        ))}
      </div>
      {refunds.isLoading && <Spinner />}
      <ErrorAlert error={refunds.error} />
      {refunds.data?.items.length === 0 && <EmptyState>No refund requests.</EmptyState>}
      {!!refunds.data?.items.length && (
        <ul className="card divide-y divide-line p-0 sm:p-0">
          {refunds.data.items.map((r) => (
            <li key={r.id} className="p-4 sm:p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-semibold">
                    {r.patient_name} <span className="caption font-normal">{r.patient_email}</span>
                  </div>
                  <p className="mt-1">
                    Appointment <strong>{r.booking_reference}</strong> · {formatMoney(r.amount, r.currency)}
                  </p>
                  <p className="caption mt-1">
                    {r.refund_bank_name} · {r.refund_account_number} · {r.refund_account_name} · Ref {r.refund_reference}
                  </p>
                  {r.refund_requested_at && <p className="caption">Requested {formatDateTime(r.refund_requested_at)}</p>}
                </div>
                <div className="flex flex-col items-end gap-2">
                  {r.refund_status && <StatusBadge status={r.refund_status} />}
                  <button
                    className="btn-secondary btn-sm"
                    aria-expanded={openId === r.id}
                    onClick={() => setOpenId(openId === r.id ? null : r.id)}
                  >
                    {openId === r.id ? 'Close' : r.refund_status === 'REQUESTED' ? 'Process' : 'Details'}
                  </button>
                </div>
              </div>
              {openId === r.id && <RefundDetail refund={r} onDone={() => setOpenId(null)} />}
            </li>
          ))}
        </ul>
      )}
      {refunds.data && <Pagination page={page} pageSize={refunds.data.page_size} total={refunds.data.total} onChange={setPage} />}
    </div>
  )
}

function RefundDetail({ refund: r, onDone }: { refund: AdminRefund; onDone: () => void }) {
  const queryClient = useQueryClient()
  const [note, setNote] = useState('')
  const [reason, setReason] = useState('')
  const [reasonError, setReasonError] = useState<string>()
  const onSuccess = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin', 'refunds'] })
    onDone()
  }
  const complete = useMutation({ mutationFn: () => api.admin.completeRefund(r.id, note.trim() || undefined), onSuccess })
  const reject = useMutation({ mutationFn: () => api.admin.rejectRefund(r.id, reason.trim()), onSuccess })
  const busy = complete.isPending || reject.isPending

  return (
    <div className="mt-4 grid gap-6 rounded-lg border border-line bg-surface p-4 sm:grid-cols-[220px_1fr] sm:p-5">
      {r.refund_qr_image_url ? (
        <img
          src={r.refund_qr_image_url}
          alt={`VietQR refund of ${formatMoney(r.amount, r.currency)} to ${r.refund_account_name}`}
          className="w-full max-w-[220px] rounded-md border border-line bg-canvas"
        />
      ) : (
        <p className="caption">No QR: bank details are incomplete.</p>
      )}
      <div className="space-y-4">
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
          <dt className="caption">Bank</dt>
          <dd>{r.refund_bank_name}</dd>
          <dt className="caption">Account</dt>
          <dd>
            {r.refund_account_number} · {r.refund_account_name}
          </dd>
          <dt className="caption">Amount</dt>
          <dd className="font-semibold">{formatMoney(r.amount, r.currency)}</dd>
          <dt className="caption">Transfer content</dt>
          <dd className="font-semibold">{r.refund_reference}</dd>
          <dt className="caption">Paid by patient</dt>
          <dd>
            {r.payment_code}
            {r.paid_at && ` · ${formatDateTime(r.paid_at)}`}
          </dd>
          {r.refund_reason && (
            <>
              <dt className="caption">Patient's reason</dt>
              <dd>{r.refund_reason}</dd>
            </>
          )}
          {r.refund_note && (
            <>
              <dt className="caption">{r.refund_status === 'REJECTED' ? 'Rejection reason' : 'Note'}</dt>
              <dd>{r.refund_note}</dd>
            </>
          )}
          {r.refunded_at && (
            <>
              <dt className="caption">Refunded</dt>
              <dd>{formatDateTime(r.refunded_at)}</dd>
            </>
          )}
        </dl>
        {r.refund_status === 'REQUESTED' && (
          <>
            <p className="caption">Scan the QR in the hospital's bank app, transfer, then mark it as transferred.</p>
            <ErrorAlert error={complete.error ?? reject.error} />
            <div className="flex flex-wrap items-end gap-3">
              <Field label="Bank transaction reference (optional)" className="min-w-[220px] flex-1">
                <input className="input" maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
              </Field>
              <button className="btn-primary" disabled={busy} onClick={() => complete.mutate()}>
                {complete.isPending ? 'Saving…' : 'Mark as transferred'}
              </button>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <Field label="Rejection reason" error={reasonError} className="min-w-[220px] flex-1">
                <input className="input" maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
              </Field>
              <button
                className="btn-danger"
                disabled={busy}
                onClick={() => {
                  const ok = reason.trim().length >= 3
                  setReasonError(ok ? undefined : 'Tell the patient why (at least 3 characters).')
                  if (ok) reject.mutate()
                }}
              >
                {reject.isPending ? 'Saving…' : 'Reject'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
