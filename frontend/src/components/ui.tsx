import { cloneElement, isValidElement, useId, type ReactElement, type ReactNode } from 'react'
import { ApiError } from '../api/http'
import { IconAlert, IconCheck, IconClock, IconInfo, type IconComponent } from './icons'

export const EMERGENCY_NUMBER = '0342036817'

/** Stagger list entrances by 40ms per item, capped so long lists never wait. */
export const stagger = (index: number) => ({ animationDelay: `${Math.min(index, 8) * 40}ms` })

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`card ${className}`}>{children}</div>
}

const PANEL_TONES = { blush: 'bg-blush', mist: 'bg-mist', peach: 'bg-peach', white: 'bg-canvas' }

/** Card with a soft tinted header (form pages). */
export function Panel({
  header,
  tone = 'white',
  children,
  className = '',
}: {
  header: ReactNode
  tone?: keyof typeof PANEL_TONES
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`panel overflow-hidden border border-line bg-canvas ${className}`}>
      <div className={`px-5 py-6 sm:px-8 sm:py-7 ${PANEL_TONES[tone]} ${tone === 'white' ? 'border-b border-line' : ''}`}>{header}</div>
      <div className="p-5 sm:p-8">{children}</div>
    </section>
  )
}

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-6 text-muted" role="status">
      <span aria-hidden="true" className="h-5 w-5 animate-spin rounded-full border-2 border-blush border-t-berry" />
      {label}
    </div>
  )
}

export function ErrorAlert({ error }: { error: unknown }) {
  if (!error) return null
  const message = error instanceof Error ? error.message : 'Something went wrong.'
  const requestId = error instanceof ApiError ? error.requestId : null
  return (
    <div className="reveal flex gap-3 rounded-lg border border-alert-line bg-alert-soft px-5 py-4 text-alert-strong" role="alert">
      <IconAlert size={22} className="mt-0.5 text-alert" />
      <div>
        <p className="font-semibold">{message}</p>
        {requestId && <p className="mt-1 text-caption">Reference: {requestId}</p>}
      </div>
    </div>
  )
}

type Tone = 'info' | 'warning' | 'danger' | 'success'
const NOTICE_TONES: Record<Tone, { className: string; iconClass: string; icon: IconComponent }> = {
  info: { className: 'border-info-line bg-mist text-info-strong', iconClass: 'text-info', icon: IconInfo },
  warning: { className: 'border-notice-line bg-notice-soft text-notice-strong', iconClass: 'text-notice', icon: IconClock },
  danger: { className: 'border-alert-line bg-alert-soft text-alert-strong', iconClass: 'text-alert', icon: IconAlert },
  success: { className: 'border-success-line bg-success-soft text-success-strong', iconClass: 'text-success', icon: IconCheck },
}

/** Soft tint + icon + bold lead: status is never colour alone. */
export function Notice({
  tone = 'info',
  title,
  children,
  className = '',
}: {
  tone?: Tone
  title?: ReactNode
  children?: ReactNode
  className?: string
}) {
  const { className: toneClass, iconClass, icon: Icon } = NOTICE_TONES[tone]
  return (
    <div className={`reveal flex gap-3 rounded-[14px] border px-5 py-4 text-base leading-normal shadow-card ${toneClass} ${className}`}>
      <Icon size={22} className={`mt-0.5 ${iconClass}`} />
      <div className="min-w-0 flex-1">
        {title && <strong className="block font-semibold">{title}</strong>}
        {children}
      </div>
    </div>
  )
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="rounded-lg border border-dashed border-line bg-surface px-6 py-10 text-center text-muted">{children}</p>
}

/** Label above the control, then a hint or an error. The hint/error sit outside the <label>
 * (so they aren't part of the accessible name) and are linked via aria-describedby. */
export function Field({
  label,
  hint,
  error,
  children,
  className = '',
}: {
  label: string
  hint?: string
  error?: string
  children: ReactNode
  className?: string
}) {
  const describedId = useId()
  const description = error ?? hint
  const control =
    description && isValidElement(children)
      ? cloneElement(children as ReactElement<{ 'aria-invalid'?: boolean; 'aria-describedby'?: string }>, {
          'aria-invalid': error ? true : undefined,
          'aria-describedby': describedId,
        })
      : children
  return (
    <div className={className}>
      <label className="block">
        <span className="label">{label}</span>
        {control}
      </label>
      {description && (
        <p id={describedId} className={error ? 'field-error' : 'field-hint'}>
          {description}
        </p>
      )}
    </div>
  )
}

/** Toggle chip for filters (specialties, symptoms, tabs). */
export function FilterChip({ pressed, onClick, children }: { pressed: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" className="chip" aria-pressed={pressed} onClick={onClick}>
      {pressed && (
        <span aria-hidden="true" className="check-pop">
          ✓
        </span>
      )}
      {children}
    </button>
  )
}

export function Pagination({ page, pageSize, total, onChange }: { page: number; pageSize: number; total: number; onChange: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (pages <= 1) return null
  return (
    <nav aria-label="Pagination" className="mt-8 flex items-center justify-between gap-4">
      <button className="btn-secondary btn-sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        Previous
      </button>
      <span className="text-muted">
        Page {page} of {pages}
      </span>
      <button className="btn-secondary btn-sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Next
      </button>
    </nav>
  )
}

export function Stars({ value }: { value: number }) {
  const rounded = Math.round(value)
  return (
    <span role="img" aria-label={`${value.toFixed(1)} out of 5`} className="tracking-[0.08em] text-notice">
      {'★'.repeat(rounded)}
      {'☆'.repeat(5 - rounded)}
    </span>
  )
}
