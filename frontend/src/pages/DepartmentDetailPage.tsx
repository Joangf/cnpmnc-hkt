import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { ApiError } from '../api/http'
import { DoctorCard } from '../components/DoctorCard'
import { EmptyState, ErrorAlert, Spinner, stagger } from '../components/ui'

export default function DepartmentDetailPage() {
  const id = Number(useParams().departmentId)
  const validId = Number.isFinite(id) && id > 0
  const department = useQuery({
    queryKey: ['department', id],
    queryFn: () => api.directory.department(id),
    enabled: validId,
  })

  if (!validId) return <DepartmentUnavailable />
  if (department.isLoading) return <Spinner />
  if (department.error) {
    if (department.error instanceof ApiError && department.error.status === 404) {
      return <DepartmentUnavailable />
    }
    return <ErrorAlert error={department.error} />
  }
  const d = department.data
  if (!d) return <DepartmentUnavailable />

  const doctorsHref = `/doctors?department_id=${d.id}&hospital_id=${d.hospital.id}`

  return (
    <div className="space-y-10">
      <section className="panel flex flex-col overflow-hidden border border-line md:flex-row">
        <div className="flex-1 space-y-3 bg-mist p-6 sm:p-8">
          <p className="eyebrow">{d.hospital.name}</p>
          <h1 className="page-title">{d.name}</h1>
          <p className="text-muted">
            <Link className="link" to={`/hospitals/${d.hospital.id}`}>
              {d.hospital.name}
            </Link>{' '}
            · {d.specialty.name}
          </p>
          {d.description && <p className="max-w-2xl">{d.description}</p>}
        </div>
        <div className="flex flex-col justify-center gap-3 border-t border-line p-6 sm:p-8 md:w-80 md:border-l md:border-t-0">
          {d.location && (
            <p>
              <span className="label">Location</span>
              {d.location}
            </p>
          )}
          <p>
            <span className="label">Doctors</span>
            {d.doctor_count} {d.doctor_count === 1 ? 'doctor' : 'doctors'} listed
          </p>
          <Link to={doctorsHref} className="btn-primary w-full">
            See all doctors
          </Link>
        </div>
      </section>

      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="section-title">Doctors in this department</h2>
          <Link to="/departments" className="link">
            Back to departments
          </Link>
        </div>
        {d.doctors.length === 0 && (
          <EmptyState>No doctors are listed for this department yet.</EmptyState>
        )}
        {!!d.doctors.length && (
          <div className="grid gap-5 md:grid-cols-2">
            {d.doctors.map((doctor, i) => (
              <DoctorCard key={doctor.id} doctor={doctor} style={stagger(i)} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function DepartmentUnavailable() {
  return (
    <div className="space-y-5">
      <EmptyState>
        This department is not published or no longer exists.{' '}
        <Link className="link" to="/departments">
          Browse all departments
        </Link>
        .
      </EmptyState>
    </div>
  )
}
