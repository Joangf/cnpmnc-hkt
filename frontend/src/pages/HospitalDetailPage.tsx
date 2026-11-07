import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { DoctorCard } from '../components/DoctorCard'
import { EmptyState, ErrorAlert, stagger, Spinner } from '../components/ui'
import { humanize, telHref } from '../lib/format'
import { HospitalAvatar } from './HospitalsPage'

export default function HospitalDetailPage() {
  const id = Number(useParams().hospitalId)
  const hospital = useQuery({ queryKey: ['hospital', id], queryFn: () => api.directory.hospital(id) })
  const doctors = useQuery({ queryKey: ['doctors', 'hospital', id], queryFn: () => api.directory.doctors({ hospital_id: id, page_size: 100 }) })

  if (hospital.isLoading) return <Spinner />
  if (hospital.error) return <ErrorAlert error={hospital.error} />
  const h = hospital.data!

  return (
    <div className="space-y-10">
      <section className="panel overflow-hidden border border-line bg-canvas">
        <div className="flex flex-col md:flex-row">
          <div className="flex flex-1 flex-col gap-6 bg-mist p-6 sm:flex-row sm:items-center sm:p-8">
            <HospitalAvatar hospital={h} tone="bg-canvas" className="h-28 w-28 text-[2rem] shadow-card sm:h-36 sm:w-36" />
            <div className="min-w-0 space-y-2">
              <p className="eyebrow">{humanize(h.facility_type)}</p>
              <h1 className="page-title">{h.name}</h1>
              <p className="text-muted">
                {h.address}, {h.city}
              </p>
            </div>
          </div>
          <div className="flex flex-col justify-center gap-2 border-t border-line p-6 sm:p-8 md:w-80 md:border-l md:border-t-0">
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
        </div>
        {h.description && (
          <div className="border-t border-line p-6 sm:p-8">
            <h2 className="label">About this facility</h2>
            <p className="mt-1 max-w-3xl whitespace-pre-line">{h.description}</p>
          </div>
        )}
      </section>

      <section>
        <h2 className="section-title mb-4">Departments</h2>
        <div className="flex flex-wrap gap-3">
          {h.departments.map((d) => (
            <Link key={d.id} to={`/doctors?department_id=${d.id}`} className="chip no-underline hover:text-berry">
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
          <div className="grid gap-5 md:grid-cols-2">
            {doctors.data.items.map((d, i) => (
              <DoctorCard key={d.id} doctor={d} style={stagger(i)} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
