import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { IconArrowRight } from '../components/icons'
import { SpecialtyFilter } from '../components/SpecialtyFilter'
import { EmptyState, ErrorAlert, Pagination, Spinner, stagger } from '../components/ui'

export default function DepartmentsPage() {
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')
  const specialtyId = params.get('specialty_id') ? Number(params.get('specialty_id')) : undefined
  const hospitalId = params.get('hospital_id') ? Number(params.get('hospital_id')) : undefined
  const page = Number(params.get('page') ?? 1)

  const hospitals = useQuery({
    queryKey: ['hospitals', 'all'],
    queryFn: () => api.directory.hospitals({ page_size: 100 }),
  })
  const departments = useQuery({
    queryKey: ['departments', params.toString()],
    queryFn: () =>
      api.directory.departments({
        q: params.get('q') ?? undefined,
        hospital_id: hospitalId,
        specialty_id: specialtyId,
        page,
      }),
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

  return (
    <div>
      <h1 className="page-title mb-2">Departments &amp; clinics</h1>
      <p className="mb-6 max-w-2xl text-muted">
        Browse every published department at HKT Hospital and the other facilities in our directory.
        No account is needed to look around.
      </p>

      <form
        className="card flex flex-wrap items-end gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          update({ q: q.trim() || undefined })
        }}
      >
        <label className="flex-[2_1_260px]">
          <span className="label">Name, specialty or location</span>
          <input
            className="input"
            type="search"
            placeholder="e.g. Tim mạch or Tầng 3"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </label>
        <label className="flex-[1_1_220px]">
          <span className="label">Facility</span>
          <select
            className="input"
            value={hospitalId ?? ''}
            onChange={(e) => update({ hospital_id: e.target.value || undefined })}
          >
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

      <SpecialtyFilter
        value={specialtyId}
        onChange={(id) => update({ specialty_id: id ? String(id) : undefined })}
      />

      <div className="mt-8">
        {departments.isLoading && <Spinner />}
        <ErrorAlert error={departments.error} />
        {departments.data && (
          <p className="caption mb-3" aria-live="polite">
            {departments.data.total}{' '}
            {departments.data.total === 1 ? 'department or clinic' : 'departments and clinics'}
          </p>
        )}
        {departments.data?.items.length === 0 && (
          <EmptyState>No departments or clinics match your filters.</EmptyState>
        )}
        {!!departments.data?.items.length && (
          <div className="grid gap-5 md:grid-cols-2">
            {departments.data.items.map((d, i) => (
              <article key={d.id} className="card reveal flex min-w-0 flex-col gap-3" style={stagger(i)}>
                <div className="flex items-start justify-between gap-3">
                  <h2 className="section-title">
                    <Link to={`/departments/${d.id}`} className="link-plain">
                      {d.name}
                    </Link>
                  </h2>
                  <span className="tag shrink-0 bg-mist text-info">{d.specialty.name}</span>
                </div>
                <p className="caption">{d.hospital.name}</p>
                {d.description && <p className="line-clamp-3 text-muted">{d.description}</p>}
                <div className="flex flex-wrap gap-2">
                  {d.location && <span className="tag">Location: {d.location}</span>}
                  <span className="tag">
                    {d.doctor_count} {d.doctor_count === 1 ? 'doctor' : 'doctors'}
                  </span>
                </div>
                <Link
                  to={`/departments/${d.id}`}
                  className="link mt-auto inline-flex w-fit items-center gap-2 pt-2"
                  aria-label={`View ${d.name} and its doctors`}
                >
                  View department &amp; doctors <IconArrowRight size={18} />
                </Link>
              </article>
            ))}
          </div>
        )}
        {departments.data && (
          <Pagination
            page={page}
            pageSize={departments.data.page_size}
            total={departments.data.total}
            onChange={(p) => update({ page: String(p) })}
          />
        )}
      </div>
    </div>
  )
}
