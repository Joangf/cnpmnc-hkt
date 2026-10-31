import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { BookingPanel } from '../components/BookingPanel'
import { DoctorAvatar, Rating } from '../components/DoctorCard'
import { EmptyState, ErrorAlert, Spinner, Stars } from '../components/ui'
import { formatDateTime, formatMoney } from '../lib/format'

export default function DoctorDetailPage() {
  const id = Number(useParams().doctorId)
  const { hash } = useLocation()
  const doctor = useQuery({ queryKey: ['doctor', id], queryFn: () => api.directory.doctor(id) })
  const reviews = useQuery({ queryKey: ['doctor-reviews', id], queryFn: () => api.directory.doctorReviews(id) })

  // "Book" on a doctor card links to #book; scroll there once the panel exists.
  const loaded = !!doctor.data
  useEffect(() => {
    if (loaded && hash === '#book') document.getElementById('book')?.scrollIntoView({ block: 'start' })
  }, [loaded, hash])

  if (doctor.isLoading) return <Spinner />
  if (doctor.error) return <ErrorAlert error={doctor.error} />
  const d = doctor.data!

  return (
    <div className="grid gap-8 lg:grid-cols-3">
      <div className="min-w-0 space-y-8 lg:col-span-2">
        <section className="border-3 border-ink">
          <div className="flex flex-col border-b-3 border-ink sm:flex-row">
            <DoctorAvatar doctor={d} className="h-40 w-full border-b-3 text-[2.5rem] sm:h-auto sm:min-h-[180px] sm:w-[180px] sm:border-b-0 sm:border-r-3" />
            <div className="flex min-w-0 flex-col justify-center gap-2 p-6 sm:p-8">
              <p className="eyebrow">{d.specialty.name}</p>
              <h1 className="page-title">{d.full_name}</h1>
              {d.title && <p>{d.title}</p>}
              <p className="text-muted">
                <Link className="link text-ink" to={`/hospitals/${d.hospital.id}`}>
                  {d.hospital.name}
                </Link>{' '}
                · {d.department.name}
              </p>
            </div>
          </div>
          <dl className="grid divide-y-3 divide-ink sm:grid-cols-3 sm:divide-x-3 sm:divide-y-0">
            <div className="p-5 sm:p-6">
              <dt className="label">Experience</dt>
              <dd className="mt-1 text-h2 font-extrabold">{d.experience_years} years</dd>
            </div>
            <div className="p-5 sm:p-6">
              <dt className="label">Consultation fee</dt>
              <dd className="mt-1 text-h2 font-extrabold">{formatMoney(d.consultation_fee, d.currency)}</dd>
            </div>
            <div className="p-5 sm:p-6">
              <dt className="label">Rating</dt>
              <dd className="mt-1 font-extrabold">
                <Rating avg={d.rating_avg} count={d.rating_count} />
              </dd>
            </div>
          </dl>
          {(d.qualifications || d.introduction) && (
            <div className="space-y-5 border-t-3 border-ink p-6 sm:p-8">
              {d.qualifications && (
                <div>
                  <h2 className="label">Qualifications</h2>
                  <p className="mt-1">{d.qualifications}</p>
                </div>
              )}
              {d.introduction && (
                <div>
                  <h2 className="label">About</h2>
                  <p className="mt-1">{d.introduction}</p>
                </div>
              )}
            </div>
          )}
        </section>

        <section className="card">
          <h2 className="section-title mb-4">Patient reviews</h2>
          {reviews.isLoading && <Spinner />}
          {reviews.data?.items.length === 0 && <EmptyState>No reviews yet.</EmptyState>}
          <ul className="divide-y divide-ink">
            {reviews.data?.items.map((r) => (
              <li key={r.id} className="py-4 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-extrabold">
                    <Stars value={r.rating} />
                  </span>
                  <span className="caption">
                    {r.author} · {formatDateTime(r.created_at)}
                  </span>
                </div>
                {r.comment && <p className="mt-1">{r.comment}</p>}
              </li>
            ))}
          </ul>
        </section>
      </div>
      <aside id="book" className="min-w-0 scroll-mt-4">
        <BookingPanel doctor={d} />
      </aside>
    </div>
  )
}
