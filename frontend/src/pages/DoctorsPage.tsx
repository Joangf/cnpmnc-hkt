import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { DoctorCard } from '../components/DoctorCard'
import { SpecialtyFilter } from '../components/SpecialtyFilter'
import { EmptyState, ErrorAlert, Pagination, Spinner } from '../components/ui'

export default function DoctorsPage() {
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')
  const num = (key: string) => (params.get(key) ? Number(params.get(key)) : undefined)
  const page = num('page') ?? 1

  const hospitals = useQuery({ queryKey: ['hospitals', 'all'], queryFn: () => api.directory.hospitals({ page_size: 100 }) })
  const doctors = useQuery({
    queryKey: ['doctors', params.toString()],
    queryFn: () =>
      api.directory.doctors({
        q: params.get('q') ?? undefined,
        hospital_id: num('hospital_id'),
        department_id: num('department_id'),
        specialty_id: num('specialty_id'),
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

  return (
    <div>
      <h1 className="page-title mb-6">Find a doctor</h1>
      <form
        className="card flex flex-wrap items-end gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          update({ q: q.trim() || undefined })
        }}
      >
        <label className="flex-[2_1_260px]">
          <span className="label">Doctor name</span>
          <input className="input" type="search" placeholder="e.g. Nguyen" value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
        <label className="flex-[1_1_220px]">
          <span className="label">Location</span>
          <select className="input" value={num('hospital_id') ?? ''} onChange={(e) => update({ hospital_id: e.target.value || undefined, department_id: undefined })}>
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
        value={num('specialty_id')}
        onChange={(id) => update({ specialty_id: id ? String(id) : undefined, department_id: undefined })}
      />

      <div className="mt-8">
        {doctors.isLoading && <Spinner />}
        <ErrorAlert error={doctors.error} />
        {doctors.data && (
          <p className="caption mb-3" aria-live="polite">
            {doctors.data.total} {doctors.data.total === 1 ? 'doctor' : 'doctors'}
          </p>
        )}
        {doctors.data?.items.length === 0 && <EmptyState>No doctors match your filters. Try another specialty or location.</EmptyState>}
        {!!doctors.data?.items.length && (
          <div className="grid gap-5 md:grid-cols-2">
            {doctors.data.items.map((d) => (
              <DoctorCard key={d.id} doctor={d} />
            ))}
          </div>
        )}
        {doctors.data && (
          <Pagination page={page} pageSize={doctors.data.page_size} total={doctors.data.total} onChange={(p) => update({ page: String(p) })} />
        )}
      </div>
    </div>
  )
}
