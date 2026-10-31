import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import type { DoctorSummary } from '../api/types'
import { formatMoney } from '../lib/format'
import { Stars } from './ui'

function initials(name: string): string {
  const words = name.replace(/^(dr\.?|bs\.?)\s+/i, '').split(/\s+/).filter(Boolean)
  return ((words[0]?.[0] ?? '') + (words.length > 1 ? words[words.length - 1][0] : '')).toUpperCase()
}

/** Round blush avatar with initials (or the photo, when the directory has one). */
export function DoctorAvatar({
  doctor,
  tone = 'bg-blush',
  className = '',
}: {
  doctor: Pick<DoctorSummary, 'id' | 'full_name' | 'avatar_url'>
  tone?: 'bg-blush' | 'bg-canvas'
  className?: string
}) {
  return (
    <div
      aria-hidden="true"
      className={`flex shrink-0 items-center justify-center overflow-hidden rounded-full ${tone} text-xl font-bold text-berry ${className}`}
    >
      {doctor.avatar_url ? <img src={doctor.avatar_url} alt="" className="h-full w-full object-cover" /> : initials(doctor.full_name)}
    </div>
  )
}

export function Rating({ avg, count }: { avg: string | number; count: number }) {
  if (count === 0) return <>No reviews yet</>
  return (
    <>
      <Stars value={Number(avg)} /> {Number(avg).toFixed(1)} ({count})
    </>
  )
}

export function DoctorCard({ doctor, style }: { doctor: DoctorSummary; style?: CSSProperties }) {
  const href = `/doctors/${doctor.id}`
  return (
    <article className="card reveal flex min-w-0 flex-col gap-5" style={style}>
      <div className="flex items-center gap-[18px]">
        <DoctorAvatar doctor={doctor} className="h-[76px] w-[76px]" />
        <div className="flex min-w-0 flex-col gap-1">
          <h3 className="text-xl font-semibold leading-tight">
            <Link to={href} className="link-plain">
              {doctor.full_name}
            </Link>
          </h3>
          <p className="caption">
            {doctor.specialty.name} · {doctor.experience_years} yrs experience
          </p>
          <p className="caption">{doctor.hospital.name}</p>
        </div>
      </div>
      <div className="flex flex-1 flex-wrap content-start gap-2">
        <span className="tag">Fee: {formatMoney(doctor.consultation_fee, doctor.currency)}</span>
        <span className="tag">{doctor.department.name}</span>
        <span className="tag">
          <Rating avg={doctor.rating_avg} count={doctor.rating_count} />
        </span>
        {doctor.title && <span className="tag">{doctor.title}</span>}
      </div>
      <div className="flex gap-3">
        <Link to={`${href}#book`} aria-label={`Book with ${doctor.full_name}`} className="btn-primary flex-1 px-4">
          Book
        </Link>
        <Link to={href} aria-label={`View profile: ${doctor.full_name}`} className="btn-secondary flex-1 px-4">
          View profile
        </Link>
      </div>
    </article>
  )
}
