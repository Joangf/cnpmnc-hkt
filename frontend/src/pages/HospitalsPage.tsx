import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { IconArrowRight } from '../components/icons'
import { SpecialtyFilter } from '../components/SpecialtyFilter'
import { EmptyState, ErrorAlert, Pagination, Spinner } from '../components/ui'
import { humanize, telHref } from '../lib/format'

export default function HospitalsPage() {
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')
  const specialtyId = params.get('specialty_id') ? Number(params.get('specialty_id')) : undefined
  const page = Number(params.get('page') ?? 1)

  const hospitals = useQuery({
    queryKey: ['hospitals', params.toString()],
    queryFn: () => api.directory.hospitals({ q: params.get('q') ?? undefined, specialty_id: specialtyId, page }),
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
      <h1 className="page-title mb-6">Hospitals &amp; clinics</h1>
      <form
        className="card flex flex-wrap items-end gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          update({ q: q.trim() || undefined })
        }}
      >
        <label className="flex-[1_1_320px]">
          <span className="label">Name, address or city</span>
          <input className="input" type="search" placeholder="e.g. District 1" value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
        <button className="btn-primary w-full sm:w-auto">Search</button>
      </form>
      <SpecialtyFilter value={specialtyId} onChange={(id) => update({ specialty_id: id ? String(id) : undefined })} />

      <div className="mt-8">
        {hospitals.isLoading && <Spinner />}
        <ErrorAlert error={hospitals.error} />
        {hospitals.data?.items.length === 0 && <EmptyState>No facilities match your search.</EmptyState>}
        {!!hospitals.data?.items.length && (
          <div className="grid gap-5 md:grid-cols-2">
            {hospitals.data.items.map((h) => (
              <article key={h.id} className="card flex min-w-0 flex-col gap-3">
                <div className="flex items-start justify-between gap-3">
                  <h2 className="section-title">
                    <Link to={`/hospitals/${h.id}`} className="link-plain">
                      {h.name}
                    </Link>
                  </h2>
                  <span className="tag shrink-0 bg-mist text-info">{humanize(h.facility_type)}</span>
                </div>
                <p className="caption">
                  {h.address}, {h.city}
                </p>
                {h.phone && (
                  <a className="link w-fit" href={telHref(h.phone)}>
                    {h.phone}
                  </a>
                )}
                <div className="flex flex-wrap gap-2">
                  {h.specialties.map((s) => (
                    <span key={s.id} className="tag">
                      {s.name}
                    </span>
                  ))}
                </div>
                <Link to={`/hospitals/${h.id}`} className="link mt-auto inline-flex w-fit items-center gap-2 pt-2" aria-label={`Doctors and departments at ${h.name}`}>
                  Doctors &amp; departments <IconArrowRight size={18} />
                </Link>
              </article>
            ))}
          </div>
        )}
        {hospitals.data && (
          <Pagination page={page} pageSize={hospitals.data.page_size} total={hospitals.data.total} onChange={(p) => update({ page: String(p) })} />
        )}
      </div>
    </div>
  )
}
