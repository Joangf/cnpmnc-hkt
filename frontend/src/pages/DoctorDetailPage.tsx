import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { BookingPanel } from '../components/BookingPanel'
import { DoctorAvatar, Rating } from '../components/DoctorCard'
import { EmptyState, ErrorAlert, Spinner, Stars } from '../components/ui'
import { formatDateTime, formatMoney } from '../lib/format'
import { IconAcademic, IconLocation, IconStethoscope } from '../components/icons'

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
    <div className="grid gap-8 lg:grid-cols-3 pb-12">
      <div className="min-w-0 space-y-8 lg:col-span-2">
        <section className="panel overflow-hidden border border-line shadow-card rounded-2xl">
          <div className="flex flex-col gap-6 bg-gradient-to-r from-blush via-canvas to-mist/40 p-6 sm:flex-row sm:items-center sm:p-8">
            <DoctorAvatar doctor={d} tone="bg-canvas" className="h-28 w-28 text-[2rem] sm:h-36 sm:w-36 shadow-lg rounded-2xl" />
            <div className="flex min-w-0 flex-col justify-center gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md bg-berry/10 px-3 py-1 text-xs font-bold text-berry border border-berry/20">
                  {d.specialty.name}
                </span>
                {d.title && (
                  <span className="rounded-md bg-surface px-2.5 py-1 text-xs font-bold text-muted border border-line">
                    {d.title}
                  </span>
                )}
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-ink tracking-tight">{d.full_name}</h1>
              <p className="text-sm font-medium text-muted flex items-center gap-1.5 flex-wrap">
                <IconLocation size={15} className="text-muted shrink-0" />
                <Link className="link hover:underline font-semibold" to={`/hospitals/${d.hospital.id}`}>
                  {d.hospital.name}
                </Link>
                <span>·</span>
                <span>{d.department.name}</span>
              </p>
            </div>
          </div>
          <dl className="grid divide-y divide-line border-t border-line sm:grid-cols-3 sm:divide-x sm:divide-y-0 bg-surface/50">
            <div className="p-5 sm:p-6 text-center sm:text-left">
              <dt className="text-xs font-semibold uppercase tracking-wider text-muted">Experience</dt>
              <dd className="mt-1 text-2xl font-extrabold text-ink">{d.experience_years} years</dd>
            </div>
            <div className="p-5 sm:p-6 text-center sm:text-left">
              <dt className="text-xs font-semibold uppercase tracking-wider text-muted">Consultation fee</dt>
              <dd className="mt-1 text-2xl font-extrabold text-berry">{formatMoney(d.consultation_fee, d.currency)}</dd>
            </div>
            <div className="p-5 sm:p-6 text-center sm:text-left">
              <dt className="text-xs font-semibold uppercase tracking-wider text-muted">Patient rating</dt>
              <dd className="mt-1 font-bold text-ink">
                <Rating avg={d.rating_avg} count={d.rating_count} />
              </dd>
            </div>
          </dl>
          {(d.qualifications || d.introduction) && (
            <div className="space-y-6 border-t border-line p-6 sm:p-8 bg-canvas">
              {d.qualifications && (
                <div>
                  <h2 className="text-sm font-bold uppercase tracking-wider text-ink mb-2 flex items-center gap-2">
                    <IconAcademic size={17} className="text-berry" /> Education &amp; Board Certifications
                  </h2>
                  <p className="text-base text-muted leading-relaxed pl-6 border-l-2 border-berry/30">{d.qualifications}</p>
                </div>
              )}
              {d.introduction && (
                <div>
                  <h2 className="text-sm font-bold uppercase tracking-wider text-ink mb-2 flex items-center gap-2">
                    <IconStethoscope size={17} className="text-berry" /> About the Doctor
                  </h2>
                  <p className="text-base text-muted leading-relaxed pl-6 border-l-2 border-berry/30">{d.introduction}</p>
                </div>
              )}
            </div>
          )}
        </section>

        <section className="card p-6 sm:p-8 rounded-2xl">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-ink">
              Patient Reviews
            </h2>
            {reviews.data && (
              <span className="text-xs font-semibold text-muted bg-surface px-3 py-1 rounded-full border border-line">
                {reviews.data.items.length} reviews
              </span>
            )}
          </div>
          {reviews.isLoading && <Spinner />}
          {reviews.data?.items.length === 0 && (
            <EmptyState>No reviews yet for this doctor. Be the first patient to share your consultation experience.</EmptyState>
          )}
          <ul className="divide-y divide-line">
            {reviews.data?.items.map((r) => (
              <li key={r.id} className="py-4 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5">
                    <Stars value={r.rating} />
                    <span className="text-xs font-bold text-ink">{r.rating}/5</span>
                  </span>
                  <span className="caption text-xs">
                    {r.author} · {formatDateTime(r.created_at)}
                  </span>
                </div>
                {r.comment && <p className="mt-2 text-sm text-ink/90 leading-relaxed bg-surface/60 p-3 rounded-xl border border-line/50">{r.comment}</p>}
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
