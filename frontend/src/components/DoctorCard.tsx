import { Link } from 'react-router-dom'
import type { DoctorSummary } from '../api/types'
import { formatMoney } from '../lib/format'
import { Stars } from './ui'

const AVATAR_TONES = ['bg-sky', 'bg-mint', 'bg-sun', 'bg-blush']

function initials(name: string): string {
  const words = name.replace(/^(dr\.?|bs\.?)\s+/i, '').split(/\s+/).filter(Boolean)
  return ((words[0]?.[0] ?? '') + (words.length > 1 ? words[words.length - 1][0] : '')).toUpperCase()
}

/** Square colour block with initials (or the photo, when the directory has one). */
export function DoctorAvatar({ doctor, className = '' }: { doctor: Pick<DoctorSummary, 'id' | 'full_name' | 'avatar_url'>; className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`flex shrink-0 items-center justify-center overflow-hidden border-ink text-[1.75rem] font-extrabold ${
        AVATAR_TONES[doctor.id % AVATAR_TONES.length]
      } ${className}`}
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

export function DoctorCard({ doctor }: { doctor: DoctorSummary }) {
  const href = `/doctors/${doctor.id}`
  const actionClass =
    'flex min-h-[60px] flex-1 items-center justify-center text-base font-extrabold uppercase tracking-label transition-colors hover:bg-sun hover:text-ink'
  return (
    <article className="flex min-w-0 flex-col bg-white">
      <div className="flex border-b-3 border-ink">
        <DoctorAvatar doctor={doctor} className="h-24 w-24 border-r-3 sm:h-[140px] sm:w-[140px]" />
        <div className="flex min-w-0 flex-col justify-center gap-1 px-5 py-4 sm:px-6">
          <h3 className="text-[1.25rem] font-extrabold leading-tight sm:text-h2">
            <Link to={href} className="hover:underline">
              {doctor.full_name}
            </Link>
          </h3>
          <p>
            {doctor.specialty.name} · {doctor.experience_years} yrs experience
          </p>
          <p className="text-muted">{doctor.hospital.name}</p>
        </div>
      </div>
      <div className="flex flex-1 flex-wrap content-start gap-2.5 border-b-3 border-ink px-5 py-4 sm:px-6">
        <span className="tag">Fee: {formatMoney(doctor.consultation_fee, doctor.currency)}</span>
        <span className="tag">{doctor.department.name}</span>
        <span className="tag">
          <Rating avg={doctor.rating_avg} count={doctor.rating_count} />
        </span>
        {doctor.title && <span className="tag">{doctor.title}</span>}
      </div>
      <div className="flex">
        <Link to={`${href}#book`} aria-label={`Book with ${doctor.full_name}`} className={`${actionClass} border-r-3 border-ink bg-cobalt text-white`}>
          Book
        </Link>
        <Link to={href} aria-label={`View profile: ${doctor.full_name}`} className={actionClass}>
          View profile
        </Link>
      </div>
    </article>
  )
}
