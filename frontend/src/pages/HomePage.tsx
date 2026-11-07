import { useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/endpoints'
import { IconArrowRight, IconBone, IconFemale, IconHeart, IconPerson, IconStethoscope, type IconComponent } from '../components/icons'
import { EMERGENCY_NUMBER, stagger } from '../components/ui'

// Specialty tiles get a line icon when the name suggests one; the rest use a stethoscope.
const SPECIALTY_ICONS: [RegExp, IconComponent][] = [
  [/cardio|heart|vascular/i, IconHeart],
  [/pediatr|paediatr|child/i, IconPerson],
  [/obstet|gyn|women/i, IconFemale],
  [/ortho|bone|joint|rheum/i, IconBone],
]
const specialtyIcon = (name: string) => SPECIALTY_ICONS.find(([re]) => re.test(name))?.[1] ?? IconStethoscope

/** Placeholder art on Peach cream (design board 04) until real, consented photos are available. */
function HeroArt() {
  return (
    <svg viewBox="0 0 320 320" className="h-auto w-[200px] sm:w-[260px]" fill="none" aria-hidden="true" focusable="false">
      <circle cx="160" cy="160" r="140" className="fill-blush" />
      <rect x="128" y="70" width="64" height="180" rx="14" className="fill-berry" />
      <rect x="70" y="128" width="180" height="64" rx="14" className="fill-berry" />
      <path d="M40 160h60l16-30 22 60 18-44 12 14h112" className="stroke-on-accent" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
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
    <div className="mx-auto w-full max-w-page px-4 sm:px-6">
      {/* Hero stacks on small screens: text above image. */}
      <section className="flex flex-wrap gap-6 pt-6 sm:pt-10">
        <div className="panel flex min-h-[420px] flex-[1_1_460px] flex-col justify-center gap-6 bg-blush px-6 py-12 sm:px-14 sm:py-16 lg:min-h-[480px]">
          <h1 className="text-[2.5rem] font-bold leading-[1.1] tracking-[-0.02em] sm:text-hero">
            Find the right care,
            <br />
            booked in minutes.
          </h1>
          <p className="max-w-[500px] text-[1.1875rem] leading-relaxed text-muted">
            See real availability across HKT Hospital and our partner clinics. Browse departments
            and doctors without an account and sign in only when you book.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/doctors" className="btn-primary">
              Find a doctor
            </Link>
            <Link to="/departments" className="btn-secondary">
              Browse departments
            </Link>
            <Link to="/symptoms" className="btn-secondary">
              Not sure which specialty?
            </Link>
          </div>
        </div>
        <div className="panel flex min-h-[260px] flex-[1_1_460px] items-center justify-center bg-peach sm:min-h-[360px] lg:min-h-[480px]">
          <HeroArt />
        </div>
      </section>

      <form onSubmit={search} className="card mt-8 flex flex-wrap items-end gap-4" aria-label="Search doctors">
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
        <button className="btn-primary w-full px-[30px] sm:w-auto">Search</button>
      </form>

      <h2 className="mb-6 mt-14 text-[1.75rem] font-bold sm:mt-[72px] sm:text-h1">Popular specialties</h2>
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {specialties.data?.map((s, i) => {
          const Icon = specialtyIcon(s.name)
          return (
            <Link key={s.id} to={`/doctors?specialty_id=${s.id}`} className="card-link reveal group flex flex-col gap-8" style={stagger(i)}>
              <span className="icon-tile transition-colors duration-base group-hover:bg-berry group-hover:text-on-accent">
                <Icon size={24} />
              </span>
              <span className="flex flex-col gap-1.5">
                <span className="hyphens-auto break-words text-xl font-semibold leading-tight">{s.name}</span>
                {s.description && <span className="caption line-clamp-2">{s.description}</span>}
                <span className="inline-flex items-center gap-1.5 text-caption font-semibold text-berry group-hover:underline">
                  See doctors <IconArrowRight size={16} className="transition-transform duration-base group-hover:translate-x-1" />
                </span>
              </span>
            </Link>
          )
        })}
      </div>

      <section className="panel my-14 flex flex-wrap items-center justify-between gap-4 rounded-lg border border-alert-line bg-alert-soft px-6 py-5 sm:my-[72px] sm:px-7">
        <p className="text-lg font-semibold text-alert-strong">Severe symptoms? Don't wait for an appointment.</p>
        <a href={`tel:${EMERGENCY_NUMBER}`} className="btn-danger min-h-12 px-[22px] text-base">
          Call {EMERGENCY_NUMBER}
        </a>
      </section>
    </div>
  )
}
