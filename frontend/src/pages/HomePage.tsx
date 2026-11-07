import { useQuery } from '@tanstack/react-query'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/endpoints'
import {
  IconAlert,
  IconArrowRight,
  IconBone,
  IconCheck,
  IconClock,
  IconFemale,
  IconHeart,
  IconLocation,
  IconPerson,
  IconSearch,
  IconShield,
  IconStethoscope,
  type IconComponent,
} from '../components/icons'
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

const DEFAULT_HOSPITAL_HERO =
  'https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=1200&q=80'

// The site is branded for HKT Hospital, while extra facilities are seeded for demo data.
const BRAND_HOSPITAL = 'HKT Hospital'

export default function HomePage() {
  const navigate = useNavigate()
  const specialties = useQuery({
    queryKey: ['specialties'],
    queryFn: api.directory.specialties,
  })
  const hospitals = useQuery({
    queryKey: ['hospitals', 'all'],
    queryFn: () => api.directory.hospitals({ page_size: 100 }),
  })
  const [q, setQ] = useState('')
  const [specialtyId, setSpecialtyId] = useState('')
  const [departmentId, setDepartmentId] = useState<number>()
  const [range, setRange] = useState(ANY_TIME)
  const [imgError, setImgError] = useState(false)

  // Prefer the branded hospital; fall back to the first record in the directory.
  const hospital =
    hospitals.data?.items?.find((h) => h.name === BRAND_HOSPITAL) ?? hospitals.data?.items?.[0]

  useEffect(() => {
    setImgError(false)
  }, [hospital?.avatar_url])

  const heroImage = (!imgError && hospital?.avatar_url) ? hospital.avatar_url : DEFAULT_HOSPITAL_HERO

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
    <div className="mx-auto w-full max-w-page px-4 sm:px-6 pb-16">
      {/* Hero Section */}
      <section className="flex flex-wrap gap-6 pt-6 sm:pt-10">
        <div className="panel flex min-h-[460px] flex-[1_1_500px] flex-col justify-center gap-6 bg-gradient-to-br from-blush via-canvas to-mist/40 p-8 sm:p-12 lg:p-14 border border-line/80 shadow-card">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full bg-berry/10 px-3.5 py-1 text-xs font-bold text-berry border border-berry/20">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-berry opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-berry"></span>
              </span>
              HKT GENERAL HOSPITAL · INTERNATIONAL STANDARDS
            </div>

            <h1 className="text-3xl sm:text-5xl font-extrabold leading-[1.15] tracking-tight text-ink">
              Compassionate care,
              <br />
              <span className="text-berry">easy booking.</span>
            </h1>
          </div>

          <p className="max-w-[520px] text-base sm:text-lg leading-relaxed text-muted">
            {hospital?.description ||
              'HKT Hospital delivers high-quality medical care with leading specialists. Book online 24/7 without waiting in line.'}
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Link to="/doctors" className="btn-primary shadow-button hover:shadow-button-hover font-semibold px-6 py-3">
              Find a doctor now
            </Link>
            <Link to="/departments" className="btn-secondary font-semibold px-5 py-3">
              Browse specialties
            </Link>
            <Link to="/symptoms" className="inline-flex items-center gap-1.5 text-sm font-semibold text-berry hover:underline px-3 py-2">
              Check symptoms
            </Link>
          </div>

          {/* Quick stats banner */}
          <div className="grid grid-cols-3 gap-4 border-t border-line/80 pt-6 mt-2">
            <div>
              <div className="text-2xl font-extrabold text-ink">28+</div>
              <div className="text-xs text-muted font-medium">Specialist doctors</div>
            </div>
            <div>
              <div className="text-2xl font-extrabold text-ink">14+</div>
              <div className="text-xs text-muted font-medium">Departments</div>
            </div>
            <div>
              <div className="text-2xl font-extrabold text-success">24/7</div>
              <div className="text-xs text-muted font-medium">Booking support</div>
            </div>
          </div>
        </div>

        <div className="panel relative flex min-h-[300px] flex-[1_1_440px] items-center justify-center overflow-hidden rounded-2xl border border-line shadow-card bg-surface sm:min-h-[400px] lg:min-h-[480px]">
          <img
            src={heroImage}
            alt={hospital?.name ?? 'HKT Hospital'}
            className="h-full w-full object-cover transition-transform duration-700 hover:scale-105"
            onError={() => setImgError(true)}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/10 to-transparent pointer-events-none" />
          <div className="absolute bottom-6 left-6 right-6 text-white pointer-events-none">
            <div className="inline-flex items-center gap-1.5 rounded-full bg-white/20 backdrop-blur-md px-3 py-1 text-xs font-semibold text-white mb-2">
              <IconLocation size={14} className="shrink-0" />
              <span>{hospital ? `${hospital.address}, ${hospital.city}` : '12 HKT Street, District 1, Ho Chi Minh City'}</span>
            </div>
            <h3 className="text-xl font-bold">{hospital?.name ?? 'HKT International General Hospital'}</h3>
            <p className="text-xs text-white/80 mt-1">Modern facilities · Compassionate care 24/7</p>
          </div>
        </div>
      </section>

      {/* Quick Search Card */}
      <form
        onSubmit={search}
        className="rounded-2xl border border-line bg-canvas p-6 shadow-card hover:shadow-card-hover transition-all duration-base mt-8 mb-14"
        aria-label="Search doctors"
      >
        <div className="flex min-w-0 flex-col gap-5">
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label htmlFor="doctor-name" className="block text-sm font-semibold text-ink mb-1.5">
                Doctor name
              </label>
              <div className="relative">
                <input
                  id="doctor-name"
                  className="input mt-0 pl-10"
                  type="search"
                  placeholder="e.g. Nguyen, Le, Ha..."
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                />
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted flex items-center pointer-events-none">
                  <IconSearch size={18} />
                </span>
              </div>
            </div>
            <label className="flex-[1_1_200px]">
              <span className="block text-sm font-semibold text-ink mb-1.5">Specialty</span>
              <select className="input mt-0" value={specialtyId} onChange={(e) => setSpecialtyId(e.target.value)}>
                <option value="">All specialties</option>
                {specialties.data?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex items-end gap-3">
              <DepartmentCombobox value={departmentId} onChange={setDepartmentId} />
              <button
                type="submit"
                aria-label="Search doctors"
                title="Search"
                className="btn-primary min-w-[120px] font-semibold py-3 shadow-button hover:shadow-button-hover"
              >
                Search
              </button>
            </div>
          </div>
          <AvailabilityPanel value={range} onChange={setRange} />
        </div>
      </form>

      {/* Why Choose HKT Hospital Section */}
      <section className="my-14 sm:my-20">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-mist px-3.5 py-1 text-xs font-semibold text-info mb-3 uppercase tracking-wider">
            Standard medical services
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-ink tracking-tight">
            Why choose HKT Hospital?
          </h2>
          <p className="text-muted text-sm sm:text-base mt-2">
            A thoughtful, modern and convenient care experience for you and your family.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="card p-6 rounded-2xl flex flex-col gap-3 hover:-translate-y-1 transition-transform duration-base">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-blush text-berry">
              <IconStethoscope size={24} />
            </span>
            <h3 className="text-lg font-bold text-ink">Leading specialists</h3>
            <p className="text-sm text-muted leading-relaxed">
              Experienced doctors and consultants who listen carefully and stay by your side.
            </p>
          </div>

          <div className="card p-6 rounded-2xl flex flex-col gap-3 hover:-translate-y-1 transition-transform duration-base">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-mist text-info">
              <IconClock size={24} />
            </span>
            <h3 className="text-lg font-bold text-ink">Book 24/7</h3>
            <p className="text-sm text-muted leading-relaxed">
              Choose the time that suits you, get instant confirmation, and skip the queue.
            </p>
          </div>

          <div className="card p-6 rounded-2xl flex flex-col gap-3 hover:-translate-y-1 transition-transform duration-base">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-success-soft text-success">
              <IconCheck size={24} />
            </span>
            <h3 className="text-lg font-bold text-ink">Transparent pricing</h3>
            <p className="text-sm text-muted leading-relaxed">
              Every consultation and service fee is shown clearly before you book, with no surprise charges.
            </p>
          </div>

          <div className="card p-6 rounded-2xl flex flex-col gap-3 hover:-translate-y-1 transition-transform duration-base">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-peach text-notice">
              <IconShield size={24} />
            </span>
            <h3 className="text-lg font-bold text-ink">Secure &amp; thoughtful</h3>
            <p className="text-sm text-muted leading-relaxed">
              Your medical information is encrypted, and we remind you about upcoming appointments.
            </p>
          </div>
        </div>
      </section>

      {/* Popular Specialties Section */}
      <section className="my-14 sm:my-20">
        <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4 mb-8">
          <div>
            <div className="inline-flex items-center gap-1.5 rounded-full bg-blush px-3.5 py-1 text-xs font-semibold text-berry mb-2 uppercase tracking-wider">
              Featured specialties
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-ink tracking-tight">
              Popular specialties
            </h2>
          </div>
          <Link to="/departments" className="link inline-flex items-center gap-1.5 text-sm font-semibold">
            View all departments <IconArrowRight size={16} />
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {specialties.data?.map((s, i) => {
            const Icon = specialtyIcon(s.name)
            return (
              <Link
                key={s.id}
                to={`/doctors?specialty_id=${s.id}`}
                className="card-link reveal group flex flex-col justify-between gap-6 p-6 rounded-2xl hover:border-berry/60 transition-all duration-base"
                style={stagger(i)}
              >
                <div className="flex items-center justify-between">
                  <span className="icon-tile rounded-xl h-12 w-12 transition-colors duration-base group-hover:bg-berry group-hover:text-on-accent">
                    <Icon size={24} />
                  </span>
                  <span className="text-xs font-semibold text-muted bg-surface px-2.5 py-1 rounded-full border border-line">
                    Specialty
                  </span>
                </div>
                <div className="flex flex-col gap-1.5">
                  <h3 className="text-lg font-bold text-ink group-hover:text-berry transition-colors leading-tight">
                    {s.name}
                  </h3>
                  {s.description && <p className="caption line-clamp-2 text-xs">{s.description}</p>}
                </div>
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-berry group-hover:underline pt-1">
                  See a doctor <IconArrowRight size={14} className="transition-transform duration-base group-hover:translate-x-1" />
                </span>
              </Link>
            )
          })}
        </div>
      </section>

      {/* Emergency Alert Banner */}
      <section className="panel my-14 flex flex-wrap items-center justify-between gap-6 rounded-2xl border border-alert-line bg-alert-soft p-6 sm:p-8 shadow-sm">
        <div className="flex items-center gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-alert text-white">
            <IconAlert size={24} />
          </span>
          <div>
            <h3 className="text-lg font-bold text-alert-strong">Need urgent medical help?</h3>
            <p className="text-sm text-alert-strong/80 mt-0.5">
              If you have dangerous symptoms, do not wait for an appointment - call emergency services 24/7.
            </p>
          </div>
        </div>
        <a href={`tel:${EMERGENCY_NUMBER}`} className="btn-danger min-h-12 px-6 text-base font-bold shadow-alert">
          Call {EMERGENCY_NUMBER} now
        </a>
      </section>
    </div>
  )
}
