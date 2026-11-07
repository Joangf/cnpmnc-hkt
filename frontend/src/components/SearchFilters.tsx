import { useQuery } from '@tanstack/react-query'
import { useMemo, useRef, type MouseEvent as ReactMouseEvent, type ReactNode } from 'react'
import { api } from '../api/endpoints'
import { upcomingDays } from '../lib/format'
import { IconArrowLeft, IconArrowRight, IconCalendar } from './icons'

/** Department picker: a plain dropdown. */
export function DepartmentCombobox({ value, onChange }: { value?: number; onChange: (id?: number) => void }) {
  const departments = useQuery({ queryKey: ['departments', 'all'], queryFn: () => api.directory.departments({ page_size: 100 }) })
  // Several facilities seed the same department name; list each name once.
  const items = [...new Map((departments.data?.items ?? []).map((d) => [d.name, d])).values()]

  return (
    <label className="flex-[1_1_220px]">
      <span className="label">Department</span>
      <select
        className="input bg-surface"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
      >
        <option value="">All departments</option>
        {items.map((d) => (
          <option key={d.id} value={d.id}>
            {d.name}
          </option>
        ))}
      </select>
    </label>
  )
}

export interface Availability {
  /** `YYYY-MM-DD`, or '' for "any day" (the time slider is then ignored). */
  date: string
  /** Minutes since midnight, 0..1440. */
  start: number
  end: number
}

export const ANY_TIME: Availability = { date: '', start: 0, end: 1440 }
const STEP = 30

const pad = (n: number) => String(n).padStart(2, '0')
/** 1440 shows as 24:00 on the slider label. */
export const formatMinutes = (m: number) => `${pad(Math.floor(m / 60))}:${pad(m % 60)}`
const stamp = (date: string, m: number) => (m >= 1440 ? `${date}T23:59` : `${date}T${formatMinutes(m)}`)

/** URL/API params (`available_from`/`available_to`) for a selection. */
export function availabilityToParams(a: Availability): { available_from?: string; available_to?: string } {
  if (!a.date) return {}
  return { available_from: stamp(a.date, a.start), available_to: stamp(a.date, a.end) }
}

export function availabilityFromParams(from?: string | null, to?: string | null): Availability {
  const date = (from ?? to ?? '').slice(0, 10)
  if (!date) return ANY_TIME
  const mins = (v?: string | null, fallback = 0) => {
    const m = v?.match(/T(\d{2}):(\d{2})/)
    return m ? Number(m[1]) * 60 + Number(m[2]) : fallback
  }
  const end = mins(to, 1440)
  return { date, start: mins(from, 0), end: end >= 1439 ? 1440 : end }
}

function DayBlock({
  pressed,
  onClick,
  top,
  big,
  bottom,
  day,
}: {
  pressed: boolean
  onClick: () => void
  top: string
  big: ReactNode
  bottom: string
  /** `YYYY-MM-DD` ('' = any day). Blocks without it are skipped while scrubbing. */
  day?: string
}) {
  return (
    <button
      data-day={day}
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={`flex h-[84px] w-[68px] shrink-0 snap-start flex-col items-center justify-center rounded-lg border-1.5 transition-[color,background-color,border-color,transform] duration-fast active:scale-[0.97] ${
        pressed ? 'border-berry bg-berry text-on-accent' : 'border-line bg-canvas text-ink hover:border-berry'
      }`}
    >
      <span className={`text-xs font-semibold uppercase tracking-wide ${pressed ? 'text-on-accent' : 'text-muted'}`}>{top}</span>
      <span className="text-2xl font-bold leading-tight">{big}</span>
      <span className={`text-xs ${pressed ? 'text-on-accent' : 'text-muted'}`}>{bottom}</span>
    </button>
  )
}

const MONTH_FMT = new Intl.DateTimeFormat('en-GB', { month: 'short', timeZone: 'UTC' })
const WEEKDAY_FMT = new Intl.DateTimeFormat('en-GB', { weekday: 'short', timeZone: 'UTC' })
const parts = (iso: string) => {
  const d = new Date(`${iso}T00:00:00Z`)
  return { weekday: WEEKDAY_FMT.format(d), day: iso.slice(8), month: MONTH_FMT.format(d) }
}

/**
 * "Available on" as a strip of day blocks (Any day, the next 14 days, or another date from a calendar),
 * with the time-window slider underneath. The slider is disabled until a day is chosen.
 */
export function AvailabilityPanel({ value, onChange }: { value: Availability; onChange: (next: Availability) => void }) {
  const { date, start, end } = value
  const days = useMemo(() => upcomingDays(14), [])
  const today = days[0].value
  const inStrip = days.some((d) => d.value === date)
  const calendar = useRef<HTMLInputElement>(null)
  const strip = useRef<HTMLDivElement>(null)
  const scrollStrip = (dir: -1 | 1) => strip.current?.scrollBy({ left: dir * 280, behavior: 'smooth' })
  // Press a day and slide across the strip: the day under the pointer is selected (like a slider thumb).
  // Touch keeps native swipe-to-scroll; tap still selects.
  const scrub = (e: ReactMouseEvent<HTMLDivElement>) => {
    const el = strip.current
    if (!el || e.button !== 0) return
    let last: string | null = null
    const move = (ev: MouseEvent) => {
      const rect = el.getBoundingClientRect()
      if (ev.clientX < rect.left + 40)
        el.scrollLeft -= 14 // nudge the strip when sliding past an edge
      else if (ev.clientX > rect.right - 40) el.scrollLeft += 14
      const x = Math.min(Math.max(ev.clientX, rect.left + 1), rect.right - 1)
      const block = document.elementFromPoint(x, rect.top + rect.height / 2)?.closest<HTMLElement>('[data-day]')
      const day = block?.dataset.day
      if (day === undefined || day === last) return
      last = day
      if (day) onChangeRef.current({ ...valueRef.current, date: day })
      else onChangeRef.current(ANY_TIME)
    }
    const up = () => {
      window.removeEventListener('mousemove', move)
      window.removeEventListener('mouseup', up)
    }
    window.addEventListener('mousemove', move)
    window.addEventListener('mouseup', up)
  }
  const valueRef = useRef(value)
  const onChangeRef = useRef(onChange)
  valueRef.current = value
  onChangeRef.current = onChange
  const pct = (m: number) => `${(m / 1440) * 100}%`
  const disabled = !date
  const pick = (d: string) => onChange({ ...value, date: d })

  return (
    <div className="min-w-0 rounded-lg bg-surface px-5 py-4">
      <div className="flex items-center justify-between gap-3">
        <span id="avail-day-label" className="text-sm font-semibold text-ink">
          Available on
        </span>
        <span
          className={`rounded-full px-3 py-0.5 text-sm font-semibold ${disabled ? 'bg-canvas text-muted' : 'bg-blush text-berry'}`}
          aria-live="polite"
        >
          {disabled ? 'Any day' : `${formatMinutes(start)} – ${formatMinutes(end)}`}
        </span>
      </div>

      <div className="relative mt-3">
        <button type="button" aria-label="Earlier days" onClick={() => scrollStrip(-1)} className="day-nav left-0 hidden sm:flex">
          <IconArrowLeft size={18} />
        </button>
        <button type="button" aria-label="Later days" onClick={() => scrollStrip(1)} className="day-nav right-0 hidden sm:flex">
          <IconArrowRight size={18} />
        </button>
        <div
          ref={strip}
          role="group"
          aria-labelledby="avail-day-label"
          onMouseDown={scrub}
          className="flex select-none gap-2 overflow-x-auto px-1 pb-2 [scrollbar-width:none] sm:px-9 [&::-webkit-scrollbar]:hidden"
        >
          <DayBlock day="" pressed={!date} onClick={() => onChange(ANY_TIME)} top="Any" big="∞" bottom="day" />
          {days.map((d, i) => {
            const p = parts(d.value)
            return (
              <DayBlock
                key={d.value}
                day={d.value}
                pressed={date === d.value}
                onClick={() => pick(d.value)}
                top={i === 0 ? 'Today' : p.weekday}
                big={p.day}
                bottom={p.month}
              />
            )
          })}
          {date && !inStrip && (
            <DayBlock
              day={date}
              pressed
              onClick={() => calendar.current?.showPicker?.()}
              top={parts(date).weekday}
              big={parts(date).day}
              bottom={parts(date).month}
            />
          )}
          <div className="relative shrink-0">
            <DayBlock
              pressed={false}
              onClick={() => {
                try {
                  calendar.current?.showPicker()
                } catch {
                  calendar.current?.focus()
                }
              }}
              top="Other"
              big={<IconCalendar size={24} />}
              bottom="date"
            />
            <input
              ref={calendar}
              type="date"
              aria-label="Choose another date"
              min={today}
              value={date}
              tabIndex={-1}
              className="pointer-events-none absolute inset-0 h-full w-full opacity-0"
              onChange={(e) => e.target.value && pick(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className={`mt-2 ${disabled ? 'opacity-50' : ''}`}>
        <div className="range-dual">
          <div className="range-dual-track" aria-hidden="true">
            <div className="range-dual-fill" style={{ left: pct(start), right: `calc(100% - ${pct(end)})` }} />
          </div>
          <input
            type="range"
            aria-label="Earliest time"
            min={0}
            max={1440}
            step={STEP}
            value={start}
            disabled={disabled}
            aria-valuetext={formatMinutes(start)}
            onChange={(e) => onChange({ ...value, start: Math.min(Number(e.target.value), end - STEP) })}
          />
          <input
            type="range"
            aria-label="Latest time"
            min={0}
            max={1440}
            step={STEP}
            value={end}
            disabled={disabled}
            aria-valuetext={formatMinutes(end)}
            onChange={(e) => onChange({ ...value, end: Math.max(Number(e.target.value), start + STEP) })}
          />
        </div>
        <div className="flex justify-between text-xs text-muted" aria-hidden="true">
          {['00:00', '06:00', '12:00', '18:00', '24:00'].map((t) => (
            <span key={t}>{t}</span>
          ))}
        </div>
        {disabled && <p className="caption mt-1">Pick a day to set a time window.</p>}
      </div>
    </div>
  )
}
