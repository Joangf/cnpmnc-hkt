import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { IconSearch } from '../components/icons'
import { DoctorCard } from '../components/DoctorCard'
import {
  availabilityFromParams,
  availabilityToParams,
  AvailabilityPanel,
  DepartmentCombobox,
} from '../components/SearchFilters'
import { EmptyState, ErrorAlert, stagger, Pagination, Spinner } from '../components/ui'

export default function DoctorsPage() {
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')
  const num = (key: string) => (params.get(key) ? Number(params.get(key)) : undefined)
  const page = num('page') ?? 1
  const [departmentId, setDepartmentId] = useState(num('department_id'))
  const [range, setRange] = useState(availabilityFromParams(params.get('available_from'), params.get('available_to')))

  // Back/forward navigation changes the URL; keep the department and time filters in step (the name box keeps what is typed).
  useEffect(() => {
    setDepartmentId(params.get('department_id') ? Number(params.get('department_id')) : undefined)
    setRange(availabilityFromParams(params.get('available_from'), params.get('available_to')))
  }, [params])

  const doctors = useQuery({
    queryKey: ['doctors', params.toString()],
    queryFn: () =>
      api.directory.doctors({
        q: params.get('q') ?? undefined,
        hospital_id: num('hospital_id'),
        department_id: num('department_id'),
        specialty_id: num('specialty_id'),
        available_from: params.get('available_from') ?? undefined,
        available_to: params.get('available_to') ?? undefined,
        page,
      }),
    placeholderData: keepPreviousData,
  })

  const update = (changes: Record<string, string | undefined>) => {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(changes)) {
      if (v) next.set(k, v)
      else next.delete(k)
    }
    if (!('page' in changes)) next.delete('page')
    setParams(next)
  }

  // Department and availability apply as soon as they change (time slider is debounced while dragging).
  useEffect(() => {
    const want = { department_id: departmentId ? String(departmentId) : '', ...availabilityToParams(range) }
    const have = { department_id: params.get('department_id') ?? '', available_from: params.get('available_from') ?? '', available_to: params.get('available_to') ?? '' }
    if (want.department_id === have.department_id && (want.available_from ?? '') === have.available_from && (want.available_to ?? '') === have.available_to) return
    const id = setTimeout(
      () => update({ department_id: want.department_id || undefined, available_from: want.available_from, available_to: want.available_to }),
      300,
    )
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [departmentId, range])

  return (
    <div className="pb-12">
      {/* Page Header */}
      <div className="mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blush text-berry text-xs font-semibold tracking-wider uppercase mb-3 border border-berry/20">
          Specialist Medical Directory
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-ink mb-3">
          Find &amp; Book a Specialist Doctor
        </h1>
        <p className="text-muted text-base sm:text-lg max-w-2xl leading-relaxed">
          Discover top medical specialists across HKT Hospital. Book consultations quickly with transparent fees and trusted care.
        </p>
      </div>

      {/* Search Form */}
      <form
        className="rounded-2xl border border-line/80 bg-canvas p-5 shadow-card hover:shadow-card-hover transition-all duration-base sm:p-6 mb-6"
        onSubmit={(e) => {
          e.preventDefault()
          update({
            q: q.trim() || undefined,
            department_id: departmentId ? String(departmentId) : undefined,
            available_from: availabilityToParams(range).available_from,
            available_to: availabilityToParams(range).available_to,
          })
        }}
      >
        <div className="flex min-w-0 flex-col gap-5">
          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <label htmlFor="doctor-name" className="block text-sm font-semibold text-ink mb-1.5">
                Doctor name
              </label>
              <div className="relative">
                <input
                  id="doctor-name"
                  className="input mt-0 pl-10"
                  type="search"
                  placeholder="e.g. Nguyen, Le, Smith..."
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                />
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted pointer-events-none flex items-center">
                  <IconSearch size={18} />
                </span>
              </div>
            </div>
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

      <div className="mt-8">
        {doctors.isLoading && (
          <div className="py-12 text-center">
            <Spinner />
          </div>
        )}
        <ErrorAlert error={doctors.error} />
        {doctors.data && (
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-muted" aria-live="polite">
              Found <span className="font-bold text-ink">{doctors.data.total}</span> matching {doctors.data.total === 1 ? 'doctor' : 'doctors'}
            </h2>
          </div>
        )}
        {doctors.data?.items.length === 0 && (
          <EmptyState>No doctors match your search filters. Try selecting another specialty or time window.</EmptyState>
        )}
        {!!doctors.data?.items.length && (
          <div className="grid gap-6 md:grid-cols-2">
            {doctors.data.items.map((d, i) => (
              <DoctorCard key={d.id} doctor={d} style={stagger(i)} />
            ))}
          </div>
        )}
        {doctors.data && (
          <div className="mt-8">
            <Pagination
              page={page}
              pageSize={doctors.data.page_size}
              total={doctors.data.total}
              onChange={(p) => update({ page: String(p) })}
            />
          </div>
        )}
      </div>
    </div>
  )
}
