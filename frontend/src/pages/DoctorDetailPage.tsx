import { useInfiniteQuery, useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useLocation, useParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import type { ReviewPublic } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { BookingPanel } from '../components/BookingPanel'
import { DoctorAvatar, Rating } from '../components/DoctorCard'
import { EmptyState, ErrorAlert, Field, Spinner, Stars } from '../components/ui'
import { formatDateTime } from '../lib/format'

export default function DoctorDetailPage() {
  const id = Number(useParams().doctorId)
  const { hash } = useLocation()
  const doctor = useQuery({ queryKey: ['doctor', id], queryFn: () => api.directory.doctor(id) })
  // SCRUM-46: page through every published review, newest first, without dropping any.
  const reviews = useInfiniteQuery({
    queryKey: ['doctor-reviews', id],
    queryFn: ({ pageParam }) => api.directory.doctorReviews(id, pageParam),
    initialPageParam: 1,
    getNextPageParam: (last) => (last.page * last.page_size < last.total ? last.page + 1 : undefined),
  })
  const reviewItems = reviews.data?.pages.flatMap((p) => p.items) ?? []
  const reviewTotal = reviews.data?.pages[0]?.total ?? 0
  // A failing AI summary must never block the profile, so its errors are not shown.
  const summary = useQuery({
    queryKey: ['doctor-review-summary', id],
    queryFn: () => api.directory.doctorReviewSummary(id),
    retry: false,
  })

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
        <section className="panel overflow-hidden border border-line">
          <div className="flex flex-col gap-6 bg-blush p-6 sm:flex-row sm:items-center sm:p-8">
            <DoctorAvatar doctor={d} tone="bg-canvas" className="h-28 w-28 text-[2rem] sm:h-32 sm:w-32" />
            <div className="flex min-w-0 flex-col justify-center gap-2">
              <p className="eyebrow">{d.specialty.name}</p>
              <h1 className="page-title">{d.full_name}</h1>
              {d.title && <p>{d.title}</p>}
              <p className="text-muted">
                {d.hospital.name} · {d.department.name}
              </p>
            </div>
          </div>
          <dl className="grid divide-y divide-line border-t border-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
            <div className="p-5 sm:p-6">
              <dt className="label">Experience</dt>
              <dd className="mt-1 text-h2 font-semibold">{d.experience_years} years</dd>
            </div>
            <div className="p-5 sm:p-6">
              <dt className="label">Specialty</dt>
              <dd className="mt-1 text-h2 font-semibold">{d.specialty.name}</dd>
            </div>
            <div className="p-5 sm:p-6">
              <dt className="label">Rating</dt>
              <dd className="mt-1 font-semibold">
                <Rating avg={d.rating_avg} count={d.rating_count} />
              </dd>
            </div>
          </dl>
          {(d.qualifications || d.introduction) && (
            <div className="space-y-5 border-t border-line p-6 sm:p-8">
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
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="section-title">Patient reviews</h2>
            {reviews.data && reviewTotal > 0 && (
              <span className="caption">
                {reviewTotal} {reviewTotal === 1 ? 'review' : 'reviews'}
              </span>
            )}
          </div>
          {summary.data?.status === 'ready' && summary.data.summary && (
            <div className="mb-6 rounded-xl border border-berry/30 bg-blush p-4">
              <p className="text-xs font-bold uppercase tracking-wider text-berry">AI summary of {summary.data.review_count} reviews</p>
              <p className="mt-2 text-sm text-ink">{summary.data.summary}</p>
              {summary.data.points.length > 0 && (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink/90">
                  {summary.data.points.map((p) => (
                    <li key={p.text}>
                      {p.text} <span className="caption text-xs">({p.review_ids.length} review{p.review_ids.length === 1 ? '' : 's'})</span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="caption mt-2 text-xs">Written by AI from published reviews only. Read the reviews below for details.</p>
            </div>
          )}
          {reviews.isLoading && <Spinner />}
          <ErrorAlert error={reviews.error} />
          {reviews.data && reviewTotal === 0 && <EmptyState>No reviews yet.</EmptyState>}
          <ul className="divide-y divide-line">
            {reviewItems.map((r) => (
              <li key={r.id} className="py-4 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span>
                    <Stars value={r.rating} />
                  </span>
                  <span className="caption">
                    {r.author} · {formatDateTime(r.created_at)}
                    {r.is_edited && <span className="ml-1 text-muted italic">(Edited)</span>}
                  </span>
                </div>
                {r.comment && <p className="mt-1">{r.comment}</p>}
                <ReportReview review={r} />
              </li>
            ))}
          </ul>
          {reviews.hasNextPage && (
            <button className="btn-secondary btn-sm mt-4" disabled={reviews.isFetchingNextPage} onClick={() => reviews.fetchNextPage()}>
              {reviews.isFetchingNextPage ? 'Loading…' : `Show more reviews (${reviewTotal - reviewItems.length} left)`}
            </button>
          )}
        </section>
      </div>
      <aside id="book" className="min-w-0 scroll-mt-4">
        <BookingPanel doctor={d} />
      </aside>
    </div>
  )
}

/** SCRUM-50: a signed-in patient reports a review; a moderator decides what happens to it. */
function ReportReview({ review }: { review: ReviewPublic }) {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [details, setDetails] = useState('')
  const reasons = useQuery({ queryKey: ['review-report-reasons'], queryFn: api.directory.reportReasons, enabled: open })
  const report = useMutation({ mutationFn: () => api.directory.reportReview(review.id, { reason, details: details.trim() || undefined }) })
  if (user?.role !== 'PATIENT') return null
  if (report.data) {
    return (
      <p className="caption mt-2 text-xs">
        {report.data.already_reported
          ? 'You have already reported this review. A moderator will look at it.'
          : 'Thanks — a moderator will look at this review. It stays visible until they decide.'}
      </p>
    )
  }
  if (!open) {
    return (
      <button type="button" className="link mt-1 text-xs" onClick={() => setOpen(true)}>
        Report this review
      </button>
    )
  }
  return (
    <form
      className="mt-2 space-y-2 rounded-lg border border-line p-3"
      onSubmit={(e) => {
        e.preventDefault()
        if (reason) report.mutate()
      }}
    >
      <Field label="Why is this review inappropriate?">
        <select className="input" value={reason} onChange={(e) => setReason(e.target.value)} required>
          <option value="">Choose a reason…</option>
          {reasons.data?.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Details (optional)">
        <input className="input" maxLength={500} value={details} onChange={(e) => setDetails(e.target.value)} />
      </Field>
      <ErrorAlert error={report.error} />
      <div className="flex gap-2">
        <button className="btn-primary btn-sm" disabled={!reason || report.isPending}>
          {report.isPending ? 'Sending…' : 'Send report'}
        </button>
        <button type="button" className="btn-secondary btn-sm" onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
    </form>
  )
}
