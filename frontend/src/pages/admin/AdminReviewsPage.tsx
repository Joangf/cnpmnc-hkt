import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api/endpoints'
import type { ReviewStatus } from '../../api/types'
import { StatusBadge } from '../../components/StatusBadge'
import { EmptyState, ErrorAlert, FilterChip, Pagination, Spinner, Stars } from '../../components/ui'
import { formatDateTime, humanize } from '../../lib/format'
import { AdminNav } from './AdminNav'

const FILTERS: (ReviewStatus | '')[] = ['', 'PUBLISHED', 'PENDING', 'HIDDEN', 'REMOVED']

export default function AdminReviewsPage() {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<ReviewStatus | ''>('')
  const [page, setPage] = useState(1)
  const reviews = useQuery({
    queryKey: ['admin', 'reviews', status, page],
    queryFn: () => api.admin.reviews({ review_status: status || undefined, page }),
    placeholderData: keepPreviousData,
  })
  const moderate = useMutation({
    mutationFn: ({ id, next }: { id: number; next: 'PUBLISHED' | 'HIDDEN' | 'REMOVED' }) => api.admin.moderateReview(id, next),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'reviews'] }),
  })

  return (
    <div>
      <h1 className="page-title mb-6">Administration</h1>
      <AdminNav />
      <div className="mb-6 flex flex-wrap gap-3">
        {FILTERS.map((f) => (
          <FilterChip
            key={f || 'all'}
            pressed={f === status}
            onClick={() => {
              setStatus(f)
              setPage(1)
            }}
          >
            {f ? humanize(f) : 'All'}
          </FilterChip>
        ))}
      </div>
      {reviews.isLoading && <Spinner />}
      <ErrorAlert error={reviews.error ?? moderate.error} />
      {reviews.data?.items.length === 0 && <EmptyState>No reviews.</EmptyState>}
      {!!reviews.data?.items.length && (
      <ul className="divide-y-3 divide-ink border-3 border-ink">
        {reviews.data.items.map((r) => (
          <li key={r.id} className="p-4 sm:p-5">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <div className="font-extrabold">{r.doctor_name}</div>
                <span className="font-extrabold">
                  <Stars value={r.rating} />
                </span>
                {r.comment && <p className="mt-1">{r.comment}</p>}
                <p className="caption mt-1">
                  Patient #{r.patient_id} · {formatDateTime(r.created_at)}
                </p>
              </div>
              <div className="flex flex-col items-end gap-2">
                <StatusBadge status={r.status} />
                <div className="flex flex-wrap gap-2">
                  {r.status !== 'PUBLISHED' && (
                    <button className="btn-secondary btn-sm" onClick={() => moderate.mutate({ id: r.id, next: 'PUBLISHED' })}>
                      Publish
                    </button>
                  )}
                  {r.status !== 'HIDDEN' && (
                    <button className="btn-secondary btn-sm" onClick={() => moderate.mutate({ id: r.id, next: 'HIDDEN' })}>
                      Hide
                    </button>
                  )}
                  {r.status !== 'REMOVED' && (
                    <button className="btn-danger btn-sm" onClick={() => moderate.mutate({ id: r.id, next: 'REMOVED' })}>
                      Remove
                    </button>
                  )}
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
      )}
      {reviews.data && <Pagination page={page} pageSize={reviews.data.page_size} total={reviews.data.total} onChange={setPage} />}
    </div>
  )
}
