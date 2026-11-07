import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { api } from '../api/endpoints'
import type { AppointmentDetail, Payment, PaymentSummary } from '../api/types'
import { formatDateTime, formatMoney } from '../lib/format'
import { Card, ErrorAlert, Field, Notice, Spinner } from './ui'

// SCRUM-31: full refund of a paid appointment that was cancelled or rejected (plan D12-D15).
// Renders nothing unless a refund can be requested or one already exists.

interface Bank {
  bin: string
  shortName: string
  name: string
}

const BANKS_URL = 'https://api.vietqr.io/v2/banks'
const MANUAL = 'manual'

async function fetchBanks(): Promise<Bank[]> {
  const res = await fetch(BANKS_URL)
  if (!res.ok) throw new Error(`Bank list unavailable (${res.status})`)
  const body = (await res.json()) as { data?: Bank[] }
  if (!body.data?.length) throw new Error('Bank list is empty')
  return body.data
}

/** The payment the refund is about: the one already carrying a refund, else the settled one. */
function refundTarget(payments: PaymentSummary[]): PaymentSummary | undefined {
  return [...payments].reverse().find((p) => p.refund_status) ?? payments.find((p) => p.status === 'PAID')
}

export function RefundPanel({ appointment, onDone }: { appointment: AppointmentDetail; onDone: () => void }) {
  const target = refundTarget(appointment.payments)
  const hasRefund = !!target?.refund_status
  const payment = useQuery({
    queryKey: ['payment', target?.id],
    queryFn: () => api.payments.get(target!.id),
    enabled: hasRefund,
  })
  if (!target || (!hasRefund && !appointment.can_request_refund)) return null

  return (
    <Card className="space-y-5">
      <h2 className="section-title">Refund</h2>
      {hasRefund && payment.isLoading && <Spinner />}
      <ErrorAlert error={payment.error} />
      {payment.data && <RefundStatusNotice payment={payment.data} />}
      {appointment.can_request_refund && (
        <RefundForm
          // Remount when the refund changes so a resubmission starts from the latest details.
          key={payment.data?.refund_requested_at ?? 'new'}
          paymentId={target.id}
          amount={formatMoney(target.amount, target.currency)}
          previous={payment.data}
          resubmit={target.refund_status === 'REJECTED'}
          onDone={onDone}
        />
      )}
    </Card>
  )
}

function RefundStatusNotice({ payment: p }: { payment: Payment }) {
  const account = `${p.refund_bank_name} · ${p.refund_account_number} · ${p.refund_account_name}`
  if (p.refund_status === 'REQUESTED') {
    return (
      <Notice tone="info" title="Refund requested">
        <p>
          The hospital will transfer {formatMoney(p.amount, p.currency)} to {account}. Transfer content:{' '}
          <strong>{p.refund_reference}</strong>.
        </p>
        {p.refund_requested_at && <p className="caption mt-1">Requested {formatDateTime(p.refund_requested_at)}</p>}
      </Notice>
    )
  }
  if (p.refund_status === 'COMPLETED') {
    return (
      <Notice tone="success" title="Refund completed">
        <p>
          {formatMoney(p.amount, p.currency)} was transferred to {account}
          {p.refunded_at && ` on ${formatDateTime(p.refunded_at)}`}. Transfer content: <strong>{p.refund_reference}</strong>.
        </p>
        {p.refund_note && <p className="caption mt-1">Bank reference: {p.refund_note}</p>}
      </Notice>
    )
  }
  if (p.refund_status === 'REJECTED') {
    return (
      <Notice tone="danger" title="Refund request rejected">
        <p>Reason: {p.refund_note ?? 'not given'}</p>
        <p className="mt-1">Correct the details below and send the request again.</p>
      </Notice>
    )
  }
  return null
}

type Errors = Partial<Record<'bank' | 'bin' | 'account_number' | 'account_name', string>>

function RefundForm({
  paymentId,
  amount,
  previous,
  resubmit,
  onDone,
}: {
  paymentId: number
  amount: string
  previous?: Payment
  resubmit: boolean
  onDone: () => void
}) {
  const queryClient = useQueryClient()
  const banks = useQuery({ queryKey: ['vietqr-banks'], queryFn: fetchBanks, staleTime: Infinity, retry: 1 })
  const prevBank = banks.data?.find((b) => b.shortName === previous?.refund_bank_name)
  const [choice, setChoice] = useState<string>('')
  const [manualName, setManualName] = useState(previous?.refund_bank_name ?? '')
  const [manualBin, setManualBin] = useState('')
  const [accountNumber, setAccountNumber] = useState(previous?.refund_account_number ?? '')
  const [accountName, setAccountName] = useState(previous?.refund_account_name ?? '')
  const [reason, setReason] = useState(previous?.refund_reason ?? '')
  const [errors, setErrors] = useState<Errors>({})

  // The bank list is third-party: if it fails, the patient types the bank in by hand (D15).
  const manual = banks.isError || choice === MANUAL
  const selected = choice || prevBank?.bin || ''
  const bank = manual ? undefined : banks.data?.find((b) => b.bin === selected)

  const submit = useMutation({
    mutationFn: () =>
      api.payments.requestRefund(paymentId, {
        bank_bin: manual ? manualBin.trim() : bank!.bin,
        bank_name: manual ? manualName.trim() : bank!.shortName,
        account_number: accountNumber.trim(),
        account_name: accountName.trim(),
        reason: reason.trim() || undefined,
      }),
    onSuccess: (payment) => {
      queryClient.setQueryData(['payment', paymentId], payment)
      onDone()
    },
  })

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    const next: Errors = {}
    if (manual) {
      if (manualName.trim().length < 2) next.bank = 'Enter the bank name.'
      if (!/^[0-9]{6}$/.test(manualBin.trim())) next.bin = 'The bank BIN has 6 digits (e.g. 970448 for OCB).'
    } else if (!bank) {
      next.bank = 'Choose your bank.'
    }
    if (!/^[0-9A-Za-z]{4,32}$/.test(accountNumber.trim())) next.account_number = 'Use 4-32 letters or digits, no spaces.'
    if (accountName.trim().length < 2) next.account_name = 'Enter the account holder name as the bank shows it.'
    setErrors(next)
    if (Object.keys(next).length === 0) submit.mutate()
  }

  return (
    <form className="space-y-5" onSubmit={onSubmit} noValidate>
      <p>
        You get a <strong>100% refund</strong> ({amount}) because this appointment was cancelled or rejected. The hospital
        transfers it manually to the account below, usually within a few working days.
      </p>
      {banks.isLoading ? (
        <Spinner label="Loading banks…" />
      ) : manual ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Bank name" error={errors.bank} hint={banks.isError ? 'The bank list could not be loaded; type it in.' : undefined}>
            <input className="input" maxLength={64} value={manualName} onChange={(e) => setManualName(e.target.value)} />
          </Field>
          <Field label="Bank BIN" error={errors.bin} hint="6 digits, shown in your banking app">
            <input className="input" inputMode="numeric" maxLength={6} value={manualBin} onChange={(e) => setManualBin(e.target.value)} />
          </Field>
          {!banks.isError && (
            <button type="button" className="btn-secondary btn-sm justify-self-start" onClick={() => setChoice('')}>
              Choose from the list instead
            </button>
          )}
        </div>
      ) : (
        <Field label="Bank" error={errors.bank}>
          <select className="input" value={selected} onChange={(e) => setChoice(e.target.value)}>
            <option value="">Choose your bank</option>
            {banks.data?.map((b) => (
              <option key={b.bin} value={b.bin}>
                {b.shortName} — {b.name}
              </option>
            ))}
            <option value={MANUAL}>My bank is not listed</option>
          </select>
        </Field>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Account number" error={errors.account_number}>
          <input
            className="input"
            inputMode="numeric"
            autoComplete="off"
            maxLength={32}
            value={accountNumber}
            onChange={(e) => setAccountNumber(e.target.value.replace(/\s/g, ''))}
          />
        </Field>
        <Field label="Account holder name" error={errors.account_name} hint="Without accents, as your bank shows it">
          <input
            className="input uppercase"
            autoComplete="off"
            maxLength={128}
            value={accountName}
            onChange={(e) => setAccountName(e.target.value.toUpperCase())}
          />
        </Field>
      </div>
      <Field label="Reason (optional)">
        <textarea className="input" rows={2} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
      </Field>
      <ErrorAlert error={submit.error} />
      <button className="btn-primary" type="submit" disabled={submit.isPending}>
        {submit.isPending ? 'Sending…' : resubmit ? 'Send refund request again' : 'Request refund'}
      </button>
    </form>
  )
}
