import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import type { HospitalSummary } from '../api/types'
import { IconArrowRight } from '../components/icons'
import { SpecialtyFilter } from '../components/SpecialtyFilter'
import { EmptyState, ErrorAlert, Pagination, Spinner, stagger } from '../components/ui'
import { humanize, telHref } from '../lib/format'

function hospitalInitials(name: string): string {
  const words = name.split(/\s+/).filter(Boolean)
  return ((words[0]?.[0] ?? '') + (words.length > 1 ? words[1][0] : '')).toUpperCase()
}

export function HospitalAvatar({
  hospital,
  tone = 'bg-blush',
  className = '',
}: {
  hospital: Pick<HospitalSummary, 'id' | 'name' | 'avatar_url'>
  tone?: 'bg-blush' | 'bg-mist' | 'bg-canvas'
  className?: string
}) {
  const [imgError, setImgError] = useState(false)
  useEffect(() => {
    setImgError(false)
  }, [hospital.avatar_url])

  const showImg = Boolean(hospital.avatar_url && !imgError)
  return (
    <div
      aria-hidden="true"
      className={`flex shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-line ${tone} text-xl font-bold text-berry ${className}`}
    >
      {showImg ? (
        <img
          src={hospital.avatar_url!}
          alt=""
          className="h-full w-full object-cover"
          onError={() => setImgError(true)}
        />
      ) : (
        hospitalInitials(hospital.name)
      )}
    </div>
  )
}

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
            {hospitals.data.items.map((h, i) => (
              <article key={h.id} className="card reveal flex min-w-0 flex-col gap-4" style={stagger(i)}>
                <div className="flex items-start gap-4">
                  <HospitalAvatar hospital={h} className="h-20 w-20 sm:h-24 sm:w-24" />
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex items-start justify-between gap-2">
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
                      <a className="link inline-block w-fit text-caption" href={telHref(h.phone)}>
                        {h.phone}
                      </a>
                    )}
                  </div>
                </div>
                {h.description && <p className="line-clamp-2 text-muted">{h.description}</p>}
                <div className="flex flex-wrap gap-2">
                  {h.specialties.map((s) => (
                    <span key={s.id} className="tag">
                      {s.name}
                    </span>
                  ))}
                </div>
                <Link to={`/hospitals/${h.id}`} className="link mt-auto inline-flex w-fit items-center gap-2 pt-1" aria-label={`Doctors and departments at ${h.name}`}>
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
