import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { DoctorCard } from '../components/DoctorCard'
import { EmptyState, ErrorAlert, Spinner } from '../components/ui'
import { humanize, telHref } from '../lib/format'

export default function HospitalDetailPage() {
  const id = Number(useParams().hospitalId)
  const hospital = useQuery({ queryKey: ['hospital', id], queryFn: () => api.directory.hospital(id) })
  const doctors = useQuery({ queryKey: ['doctors', 'hospital', id], queryFn: () => api.directory.doctors({ hospital_id: id, page_size: 100 }) })

  if (hospital.isLoading) return <Spinner />
  if (hospital.error) return <ErrorAlert error={hospital.error} />
  const h = hospital.data!

  return (
    <div className="space-y-10">
      <section className="flex flex-col border-3 border-ink md:flex-row">
        <div className="flex-1 space-y-3 border-b-3 border-ink bg-sky p-6 sm:p-8 md:border-b-0 md:border-r-3">
          <p className="eyebrow">{humanize(h.facility_type)}</p>
          <h1 className="page-title">{h.name}</h1>
          <p>
            {h.address}, {h.city}
          </p>
        </div>
        <div className="flex flex-col justify-center gap-2 p-6 sm:p-8 md:w-80">
          {h.phone && (
            <a className="link w-fit" href={telHref(h.phone)}>
              {h.phone}
            </a>
          )}
          {h.email && (
            <a className="link w-fit break-all" href={`mailto:${h.email}`}>
              {h.email}
            </a>
          )}
          {h.website && (
            <a className="link w-fit break-all" href={h.website} target="_blank" rel="noreferrer">
              Website
            </a>
          )}
        </div>
      </section>
      {h.description && <p className="max-w-3xl">{h.description}</p>}

      <section>
        <h2 className="section-title mb-4">Departments</h2>
        <div className="flex flex-wrap gap-3">
          {h.departments.map((d) => (
            <Link key={d.id} to={`/doctors?department_id=${d.id}`} className="chip hover:text-ink">
              {d.name}
            </Link>
          ))}
        </div>
      </section>

      <section>
        <h2 className="section-title mb-4">Doctors</h2>
        {doctors.isLoading && <Spinner />}
        {doctors.data?.items.length === 0 && <EmptyState>No doctors listed here yet.</EmptyState>}
        {!!doctors.data?.items.length && (
          <div className="tile-grid md:grid-cols-2">
            {doctors.data.items.map((d) => (
              <DoctorCard key={d.id} doctor={d} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
