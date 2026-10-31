import { useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/endpoints'
import { IconArrowRight } from '../components/icons'
import { EMERGENCY_NUMBER } from '../components/ui'

// Tiles alternate one bright colour with white, so no three bright blocks touch.
const TILE_TONES = ['bg-mint', 'bg-white', 'bg-sun', 'bg-white']

/** Flat geometric illustration on Blush (design board 04). Decorative only. */
function HeroIllustration() {
  const line = { stroke: '#111111', strokeWidth: 3, vectorEffect: 'non-scaling-stroke' as const }
  return (
    <svg viewBox="0 0 600 560" preserveAspectRatio="xMidYMid slice" className="absolute inset-0 h-full w-full" aria-hidden="true" focusable="false">
      <circle cx="300" cy="280" r="200" fill="#1652C8" {...line} />
      <path d="M20 490V460A130 140 0 0 1 280 460V490Z" fill="#5EE07A" {...line} />
      <circle cx="540" cy="60" r="130" fill="#FFC72C" {...line} />
      <rect x="360" y="130" width="160" height="160" fill="#12B5E5" {...line} />
      <rect x="421" y="157" width="40" height="110" fill="#FFFFFF" />
      <rect x="386" y="192" width="110" height="40" fill="#FFFFFF" />
      <circle cx="89" cy="465" r="17" fill="#FFFFFF" {...line} />
    </svg>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const specialties = useQuery({ queryKey: ['specialties'], queryFn: api.directory.specialties })
  const hospitals = useQuery({ queryKey: ['hospitals', 'all'], queryFn: () => api.directory.hospitals({ page_size: 100 }) })
  const [q, setQ] = useState('')
  const [specialtyId, setSpecialtyId] = useState('')
  const [hospitalId, setHospitalId] = useState('')

  const search = (e: FormEvent) => {
    e.preventDefault()
    const params = new URLSearchParams()
    if (q.trim()) params.set('q', q.trim())
    if (specialtyId) params.set('specialty_id', specialtyId)
    if (hospitalId) params.set('hospital_id', hospitalId)
    navigate(`/doctors${params.size ? `?${params}` : ''}`)
  }

  return (
    <>
      {/* Split hero: stacks with the colour block on top on small screens. */}
      <section className="flex flex-col border-b-3 border-ink lg:flex-row">
        <div className="flex flex-1 flex-col justify-center gap-7 border-b-3 border-ink bg-sky px-4 py-14 sm:px-[7%] sm:py-20 lg:min-h-[560px] lg:border-b-0 lg:border-r-3">
          <h1 className="text-[2.75rem] font-extrabold leading-none tracking-[-0.02em] sm:text-[4.5rem]">
            Find the right care.
            <br />
            Book in minutes.
          </h1>
          <p className="max-w-[560px] text-[1.25rem] leading-relaxed sm:text-[1.375rem]">
            See real availability across our hospitals and clinics. Browse without an account and sign in only when you book.
          </p>
          <div className="flex flex-wrap gap-4">
            <Link to="/doctors" className="btn-dark min-h-[60px] px-8">
              Find a doctor
            </Link>
            <Link to="/symptoms" className="btn-secondary min-h-[60px] px-8">
              Not sure which specialty?
            </Link>
          </div>
        </div>
        <div className="relative min-h-[260px] flex-1 overflow-hidden bg-blush sm:min-h-[360px] lg:min-h-[560px]">
          <HeroIllustration />
        </div>
      </section>

      <div className="mx-auto w-full max-w-[1180px] px-4 sm:px-6">
        <form onSubmit={search} className="mt-12 flex flex-wrap items-end gap-5 border-3 border-ink p-5 sm:mt-[72px] sm:p-7" aria-label="Search doctors">
          <label className="flex-[2_1_280px]">
            <span className="label">Doctor name</span>
            <input className="input" type="search" placeholder="e.g. Nguyen" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
          <label className="flex-[1_1_200px]">
            <span className="label">Specialty</span>
            <select className="input" value={specialtyId} onChange={(e) => setSpecialtyId(e.target.value)}>
              <option value="">Any specialty</option>
              {specialties.data?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex-[1_1_200px]">
            <span className="label">Location</span>
            <select className="input" value={hospitalId} onChange={(e) => setHospitalId(e.target.value)}>
              <option value="">All facilities</option>
              {hospitals.data?.items.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.name}
                </option>
              ))}
            </select>
          </label>
          <button className="btn-primary w-full sm:w-auto">Search</button>
        </form>

        <h2 className="mb-6 mt-12 text-[2rem] font-extrabold tracking-[-0.01em] sm:mt-[72px] sm:text-[2.5rem]">Popular specialties</h2>
        <div className="tile-grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
          {specialties.data?.map((s, i) => (
            <Link
              key={s.id}
              to={`/doctors?specialty_id=${s.id}`}
              className={`group flex min-h-[180px] flex-col justify-between gap-8 p-7 hover:text-ink ${TILE_TONES[i % TILE_TONES.length]}`}
            >
              <span>
                <span className="block hyphens-auto break-words text-[1.625rem] font-extrabold leading-tight">{s.name}</span>
                {s.description && <span className="mt-2 line-clamp-2 block text-caption">{s.description}</span>}
              </span>
              <span className="inline-flex items-center gap-2 font-semibold underline decoration-2 underline-offset-4 group-hover:no-underline">
                See doctors <IconArrowRight size={20} />
              </span>
            </Link>
          ))}
        </div>
      </div>

      <section className="mt-12 flex flex-wrap items-center justify-between gap-4 border-t-3 border-ink bg-alert px-4 py-6 text-white sm:mt-[72px] sm:px-[7%]">
        <p className="text-[1.25rem] font-extrabold">Severe symptoms? Don't wait for an appointment.</p>
        <a href={`tel:${EMERGENCY_NUMBER}`} className="btn-secondary min-h-[52px] px-6">
          Call {EMERGENCY_NUMBER}
        </a>
      </section>
    </>
  )
}
