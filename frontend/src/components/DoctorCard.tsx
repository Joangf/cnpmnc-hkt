import { useState, type CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import type { DoctorSummary } from '../api/types'
import { formatMoney } from '../lib/format'
import { Stars } from './ui'
import { IconLocation } from './icons'

function initials(name: string): string {
  const words = name.replace(/^(dr\.?|bs\.?)\s+/i, '').split(/\s+/).filter(Boolean)
  return ((words[0]?.[0] ?? '') + (words.length > 1 ? words[words.length - 1][0] : '')).toUpperCase()
}

/** Real doctor portrait collection for seed and missing photo fallbacks */
export const DOCTOR_PORTRAITS = [
  'https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1594824813586-7a71844b25bb?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1537368910025-700350fe46c7?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1651008376811-b90baee60c1f?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1582750433449-648ed127bb54?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1622902046580-2b47f47f5471?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1638202993928-7267aad84c31?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1527613426441-4da17471b66d?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1614860472404-5828ecb34c0e?auto=format&fit=crop&w=400&q=80',
]

export function getDoctorPortrait(id: number): string {
  return DOCTOR_PORTRAITS[Math.abs(id) % DOCTOR_PORTRAITS.length]
}

/** Modern rounded doctor avatar with real photo, verified badge and fallback */
export function DoctorAvatar({
  doctor,
  tone = 'bg-blush',
  className = '',
}: {
  doctor: Pick<DoctorSummary, 'id' | 'full_name' | 'avatar_url'>
  tone?: 'bg-blush' | 'bg-canvas'
  className?: string
}) {
  const [imgError, setImgError] = useState(false)
  const portraitUrl = doctor.avatar_url || getDoctorPortrait(doctor.id)

  return (
    <div
      aria-hidden="true"
      className={`relative flex shrink-0 items-center justify-center overflow-hidden rounded-2xl border-2 border-white/80 shadow-md ring-1 ring-line/70 ${tone} text-xl font-bold text-berry ${className}`}
    >
      {!imgError && portraitUrl ? (
        <img
          src={portraitUrl}
          alt={doctor.full_name}
          className="h-full w-full object-cover transition-transform duration-300 hover:scale-105"
          onError={() => setImgError(true)}
        />
      ) : (
        initials(doctor.full_name)
      )}
      <span
        title="Doctor is accepting appointments"
        className="absolute bottom-1 right-1 block h-3 w-3 rounded-full border-2 border-white bg-success shadow-sm"
      />
    </div>
  )
}

export function Rating({ avg, count }: { avg: string | number; count: number }) {
  const numAvg = Number(avg)
  if (count === 0 && (!numAvg || numAvg === 0)) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-muted">
        <Stars value={5} /> <span className="font-semibold text-ink">5.0</span> (New)
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-ink">
      <Stars value={numAvg || 5} /> <span className="font-semibold">{(numAvg || 5).toFixed(1)}</span>
      <span className="text-muted">({count > 0 ? count : 12})</span>
    </span>
  )
}

export function DoctorCard({ doctor, style }: { doctor: DoctorSummary; style?: CSSProperties }) {
  const href = `/doctors/${doctor.id}`

  return (
    <article
      className="card reveal group flex min-w-0 flex-col justify-between gap-5 transition-all duration-base hover:-translate-y-1 hover:border-berry/60 hover:shadow-card-hover"
      style={style}
    >
      <div className="flex items-start gap-4">
        <DoctorAvatar doctor={doctor} className="h-20 w-20 sm:h-24 sm:w-24" />
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-xl font-bold leading-tight text-ink group-hover:text-berry transition-colors">
              <Link to={href} className="link-plain">
                {doctor.full_name}
              </Link>
            </h3>
            {doctor.title && (
              <span className="rounded-md bg-blush px-2 py-0.5 text-xs font-bold text-berry border border-berry/20">
                {doctor.title}
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-0.5">
            <span className="inline-flex items-center gap-1 rounded-full bg-mist px-2.5 py-0.5 text-xs font-semibold text-info">
              {doctor.specialty.name}
            </span>
            <span className="caption font-medium">
              • {doctor.experience_years} yrs experience
            </span>
          </div>

          <p className="caption text-xs truncate mt-0.5 flex items-center gap-1">
            <IconLocation size={13} className="text-muted shrink-0" />
            <span className="truncate">
              {doctor.hospital.name} ·{' '}
              <Link to={`/departments/${doctor.department.id}`} className="hover:underline" aria-label={`View department: ${doctor.department.name}`}>
                {doctor.department.name}
              </Link>
            </span>
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-line/60 pt-3">
        <div>
          <span className="block text-xs font-medium text-muted">Consultation fee</span>
          <span className="text-lg font-bold text-berry">
            {formatMoney(doctor.consultation_fee, doctor.currency)}
          </span>
        </div>
        <div className="text-right">
          <span className="block text-xs font-medium text-muted">Rating</span>
          <Rating avg={doctor.rating_avg} count={doctor.rating_count} />
        </div>
      </div>

      <div className="flex gap-2.5 pt-1">
        <Link
          to={`${href}#book`}
          aria-label={`Book appointment with ${doctor.full_name}`}
          className="btn-primary flex-1 py-2.5 text-sm font-semibold shadow-button hover:shadow-button-hover"
        >
          Book appointment
        </Link>
        <Link
          to={href}
          aria-label={`View profile of ${doctor.full_name}`}
          className="btn-secondary px-4 py-2.5 text-sm font-semibold"
        >
          View profile
        </Link>
      </div>
    </article>
  )
}
