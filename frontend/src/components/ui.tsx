import { cloneElement, isValidElement, useId, type ReactElement, type ReactNode } from 'react'
import { ApiError } from '../api/http'
import { IconAlert, IconCheck, IconClock, IconInfo, type IconComponent } from './icons'

export const EMERGENCY_NUMBER = '115'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`card ${className}`}>{children}</div>
}

const BAND_TONES = { sky: 'bg-sky', mint: 'bg-mint', sun: 'bg-sun', blush: 'bg-blush', white: 'bg-white' }

/** Bordered panel with a colour band on top (the one loud block of a form page). */
export function Panel({
  header,
  tone = 'white',
  children,
  className = '',
}: {
  header: ReactNode
  tone?: keyof typeof BAND_TONES
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`border-3 border-ink bg-white ${className}`}>
      <div className={`border-b-3 border-ink px-5 py-6 sm:px-7 ${BAND_TONES[tone]}`}>{header}</div>
      <div className="p-5 sm:p-7">{children}</div>
    </section>
  )
}

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-6 font-semibold" role="status">
      <span aria-hidden="true" className="h-5 w-5 animate-spin border-3 border-ink border-t-sun" />
      {label}
    </div>
  )
}

export function ErrorAlert({ error }: { error: unknown }) {
  if (!error) return null
  const message = error instanceof Error ? error.message : 'Something went wrong.'
  const requestId = error instanceof ApiError ? error.requestId : null
  return (
    <div className="flex gap-3.5 border-3 border-ink bg-alert p-4 text-white" role="alert">
      <IconAlert size={26} />
      <div>
        <p className="font-semibold">{message}</p>
        {requestId && <p className="mt-1 text-caption">Reference: {requestId}</p>}
      </div>
    </div>
  )
}

type Tone = 'info' | 'warning' | 'danger' | 'success'
const NOTICE_TONES: Record<Tone, { className: string; icon: IconComponent }> = {
  info: { className: 'bg-white', icon: IconInfo },
  warning: { className: 'bg-sun', icon: IconClock },
  danger: { className: 'bg-alert text-white', icon: IconAlert },
  success: { className: 'bg-mint', icon: IconCheck },
}

/** Colour block + icon + bold lead: status is never colour alone. */
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
  const { className: toneClass, icon: Icon } = NOTICE_TONES[tone]
  return (
    <div className={`flex gap-3.5 border-3 border-ink p-4 sm:p-5 ${toneClass} ${className}`}>
      <Icon size={26} />
      <div className="min-w-0 flex-1">
        {title && <strong className="block font-extrabold">{title}</strong>}
        {children}
      </div>
    </div>
  )
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="border-3 border-ink px-6 py-10 text-center text-muted">{children}</p>
}

/** Caps label above the control, then a hint or an error. The hint/error sit outside the <label>
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
      {children}
      {pressed && <span aria-hidden="true">✓</span>}
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
      <span className="font-semibold">
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
    <span role="img" aria-label={`${value.toFixed(1)} out of 5`} className="tracking-[0.08em]">
      {'★'.repeat(rounded)}
      {'☆'.repeat(5 - rounded)}
    </span>
  )
}
