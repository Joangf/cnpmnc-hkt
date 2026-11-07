import { useQuery } from '@tanstack/react-query'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/endpoints'
import { IconArrowRight, IconBone, IconFemale, IconHeart, IconPerson, IconSearch, IconStethoscope, type IconComponent } from '../components/icons'
import { ANY_TIME, availabilityToParams, AvailabilityPanel, DepartmentCombobox } from '../components/SearchFilters'
import { EMERGENCY_NUMBER, stagger } from '../components/ui'

// Specialty tiles get a line icon when the name suggests one; the rest use a stethoscope.
const SPECIALTY_ICONS: [RegExp, IconComponent][] = [
  [/cardio|heart|vascular/i, IconHeart],
  [/pediatr|paediatr|child/i, IconPerson],
  [/obstet|gyn|women/i, IconFemale],
  [/ortho|bone|joint|rheum/i, IconBone],
]
const specialtyIcon = (name: string) => SPECIALTY_ICONS.find(([re]) => re.test(name))?.[1] ?? IconStethoscope

/** Placeholder art on Peach cream (design board 04) when hospital photo is not available. */
function HeroArt() {
  return (
    <svg viewBox="0 0 320 320" className="h-auto w-[200px] sm:w-[260px]" fill="none" aria-hidden="true" focusable="false">
      <circle cx="160" cy="160" r="140" className="fill-blush" />
      <rect x="128" y="70" width="64" height="180" rx="14" className="fill-berry" />
      <rect x="70" y="128" width="180" height="64" rx="14" className="fill-berry" />
      <path
        d="M40 160h60l16-30 22 60 18-44 12 14h112"
        className="stroke-on-accent"
        strokeWidth="6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const specialties = useQuery({ queryKey: ['specialties'], queryFn: api.directory.specialties })
  const hospitals = useQuery({ queryKey: ['hospitals'], queryFn: () => api.directory.hospitals({ page_size: 1 }) })
  const [q, setQ] = useState('')
  const [specialtyId, setSpecialtyId] = useState('')
  const [departmentId, setDepartmentId] = useState<number>()
  const [range, setRange] = useState(ANY_TIME)
  const [imgError, setImgError] = useState(false)

  // Bệnh viện duy nhất của hệ thống (lấy record đầu tiên)
  const hospital = hospitals.data?.items?.[0]

  useEffect(() => {
    setImgError(false)
  }, [hospital?.avatar_url])

  const showImage = Boolean(hospital?.avatar_url && !imgError)

  const search = (e: FormEvent) => {
    e.preventDefault()
    const params = new URLSearchParams()
    if (q.trim()) params.set('q', q.trim())
    if (specialtyId) params.set('specialty_id', specialtyId)
    if (departmentId) params.set('department_id', String(departmentId))
    for (const [k, v] of Object.entries(availabilityToParams(range))) params.set(k, v)
    navigate(`/doctors${params.size ? `?${params}` : ''}`)
  }

  return (
    <div className="mx-auto w-full max-w-page px-4 sm:px-6">
      {/* Hero stacks on small screens: text above image. */}
      <section className="flex flex-wrap gap-6 pt-6 sm:pt-10">
        <div className="panel flex min-h-[420px] flex-[1_1_460px] flex-col justify-center gap-6 bg-blush px-6 py-12 sm:px-14 sm:py-16 lg:min-h-[480px]">
          <div className="space-y-3">
            {hospital && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="tag border border-line bg-canvas font-semibold text-berry shadow-sm">{hospital.name}</span>
                <span className="caption text-muted">
                  {hospital.address}, {hospital.city}
                </span>
              </div>
            )}
            <h1 className="text-[2.5rem] font-bold leading-[1.1] tracking-[-0.02em] sm:text-hero">
              Find the right care,
              <br />
              booked in minutes.
            </h1>
          </div>
          <p className="max-w-[500px] text-[1.1875rem] leading-relaxed text-muted">
            {hospital?.description ||
              'See real availability across our doctors and clinics. Browse without an account and sign in only when you book.'}
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/doctors" className="btn-primary">
              Doctors
            </Link>
            <Link to="/departments" className="btn-secondary">
              Browse departments
            </Link>
            <Link to="/symptoms" className="btn-secondary">
              Not sure which specialty?
            </Link>
          </div>
        </div>
        <div className="panel relative flex min-h-[260px] flex-[1_1_460px] items-center justify-center overflow-hidden bg-peach sm:min-h-[360px] lg:min-h-[480px]">
          {showImage ? (
            <img
              src={hospital!.avatar_url!}
              alt={hospital?.name ?? 'Hospital'}
              className="h-full w-full object-cover transition-transform duration-slow hover:scale-105"
              onError={() => setImgError(true)}
            />
          ) : (
            <HeroArt />
          )}
        </div>
      </section>

      <form onSubmit={search} className="card mt-8" aria-label="Search doctors">
        <div className="flex min-w-0 flex-col gap-5">
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label htmlFor="doctor-name" className="label">Doctor name</label>
              <input
                id="doctor-name"
                className="input bg-surface"
                type="search"
                placeholder="e.g. Nguyen"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </div>
            <label className="flex-[1_1_200px]">
              <span className="label">Specialty</span>
              <select className="input bg-surface" value={specialtyId} onChange={(e) => setSpecialtyId(e.target.value)}>
                <option value="">Any specialty</option>
                {specialties.data?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex items-end gap-3">
              <DepartmentCombobox value={departmentId} onChange={setDepartmentId} />
              <button type="submit" aria-label="Search doctors" title="Search" className="btn-primary h-[52px] w-[60px] shrink-0 px-0">
                <IconSearch size={24} />
              </button>
            </div>
          </div>
          <AvailabilityPanel value={range} onChange={setRange} />
        </div>
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
