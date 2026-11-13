import { useEffect, useState } from 'react'
import type { Payment } from '../api/types'
import { IconClock } from './icons'
import { Notice } from './ui'
import { formatDateTime, formatMoney } from '../lib/format'

/** Seconds until `iso`, ticking every second; null when there is no deadline. */
export function useSecondsLeft(iso: string | null): number | null {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!iso) return
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [iso])
  if (!iso) return null
  return Math.max(0, Math.floor((new Date(iso).getTime() - now) / 1000))
}

export function formatCountdown(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export function CopyRow({
  label,
  value,
  display,
  emphasis,
}: {
  label: string
  value: string
  display?: string
  emphasis?: boolean
}) {
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
        <dd className={`break-all font-semibold ${emphasis ? 'font-mono text-h2 tracking-[0.1em] text-berry' : ''}`}>
          {display ?? value}
        </dd>
      </div>
      <button type="button" className="btn-secondary btn-sm shrink-0" onClick={copy} aria-label={`Copy ${label.toLowerCase()}`}>
        {state === 'copied' ? 'Copied' : state === 'failed' ? 'Copy failed' : 'Copy'}
      </button>
    </div>
  )
}

export function BankTransferDetails({ payment: p }: { payment: Payment }) {
  const left = useSecondsLeft(p.expires_at)

  return (
    <div className="space-y-5">
      <div className="grid gap-6 md:grid-cols-[auto_1fr]">
        <div className="flex flex-col items-center gap-3">
          <img
            src={p.qr_image_url}
            alt={`VietQR code: transfer ${formatMoney(p.amount, p.currency)} with content ${p.payment_code}`}
            className="h-60 w-60 rounded-md border border-line bg-white object-contain p-2"
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
            Keep the transfer content exactly <strong className="font-mono">{p.payment_code}</strong>, otherwise we cannot match your
            payment.
          </p>
        </div>
      </div>

      {p.failure_reason && (
        <Notice tone="danger" title="We received a transfer we could not accept">
          {p.failure_reason}
        </Notice>
      )}
      {left === null ? null : left > 0 ? (
        <Notice tone="warning" title={`Time left: ${formatCountdown(left)}`}>
          Pay before {formatDateTime(p.expires_at!)} to keep this slot and confirm your appointment.
        </Notice>
      ) : (
        <Notice tone="warning" title="Time is up">
          If you have already transferred, the payment is still recorded when the bank reports it. Otherwise the appointment will be
          released shortly.
        </Notice>
      )}
      <p className="flex items-center gap-2 text-muted" role="status">
        <IconClock size={18} /> Waiting for the bank. We confirm your appointment automatically once the transfer arrives.
      </p>
    </div>
  )
}
