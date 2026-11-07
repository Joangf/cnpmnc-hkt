export const CLINIC_TZ = import.meta.env.VITE_CLINIC_TIMEZONE ?? 'Asia/Ho_Chi_Minh'

const dateTimeFmt = new Intl.DateTimeFormat('en-GB', {
  timeZone: CLINIC_TZ,
  weekday: 'short',
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})
const timeFmt = new Intl.DateTimeFormat('en-GB', { timeZone: CLINIC_TZ, hour: '2-digit', minute: '2-digit' })
const dayLabelFmt = new Intl.DateTimeFormat('en-GB', { timeZone: CLINIC_TZ, weekday: 'short', day: '2-digit', month: 'short' })
const weekdayFmt = new Intl.DateTimeFormat('en-GB', { timeZone: CLINIC_TZ, weekday: 'short' })
const dayMonthFmt = new Intl.DateTimeFormat('en-GB', { timeZone: CLINIC_TZ, day: '2-digit', month: 'short' })
const isoDayFmt = new Intl.DateTimeFormat('en-CA', { timeZone: CLINIC_TZ, year: 'numeric', month: '2-digit', day: '2-digit' })

export function formatDateTime(iso: string): string {
  return dateTimeFmt.format(new Date(iso))
}

export function formatTime(iso: string): string {
  return timeFmt.format(new Date(iso))
}

export function formatMoney(amount: string | number | null | undefined, currency = 'VND'): string {
  if (amount === null || amount === undefined) return '-'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency, maximumFractionDigits: 0 }).format(Number(amount))
}

/** Next `count` days as clinic-local YYYY-MM-DD strings, starting today. */
export function upcomingDays(
  count: number,
  now: Date = new Date(),
): { value: string; label: string; weekday: string; dayMonth: string }[] {
  return Array.from({ length: count }, (_, i) => {
    const d = new Date(now.getTime() + i * 86_400_000)
    return {
      value: isoDayFmt.format(d),
      label: i === 0 ? 'Today' : dayLabelFmt.format(d),
      weekday: i === 0 ? 'Today' : weekdayFmt.format(d),
      dayMonth: dayMonthFmt.format(d),
    }
  })
}

/** Clinic-local parts for a date tile: { weekday: 'Tue', day: '04', month: 'Nov', time: '09:30' }. */
export function dateParts(iso: string): { weekday: string; day: string; month: string; time: string } {
  const d = new Date(iso)
  const parts = Object.fromEntries(dayMonthFmt.formatToParts(d).map((p) => [p.type, p.value]))
  return { weekday: weekdayFmt.format(d), day: parts.day, month: parts.month, time: timeFmt.format(d) }
}

/** Tap-to-call link for any displayed phone number. */
export function telHref(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, '')}`
}

export function humanize(value: string): string {
  return value.charAt(0) + value.slice(1).toLowerCase().replace(/_/g, ' ')
}
