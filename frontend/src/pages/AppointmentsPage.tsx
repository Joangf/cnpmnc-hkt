import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/endpoints'
import { StatusBadge } from '../components/StatusBadge'
import { EmptyState, ErrorAlert, FilterChip, Pagination, Spinner } from '../components/ui'
import { dateParts } from '../lib/format'

const TABS = [
  { value: 'upcoming', label: 'Upcoming' },
  { value: 'past', label: 'Past & cancelled' },
] as const

export default function AppointmentsPage() {
  const [scope, setScope] = useState<'upcoming' | 'past'>('upcoming')
  const [page, setPage] = useState(1)
  const appointments = useQuery({
    queryKey: ['appointments', scope, page],
    queryFn: () => api.appointments.list(scope, page),
    placeholderData: keepPreviousData,
  })

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h1 className="page-title">My appointments</h1>
        <Link to="/doctors" className="btn-primary">
          Book new
        </Link>
      </div>
      <div className="mb-6 flex flex-wrap gap-3">
        {TABS.map((t) => (
          <FilterChip
            key={t.value}
            pressed={t.value === scope}
            onClick={() => {
              setScope(t.value)
              setPage(1)
            }}
          >
            {t.label}
          </FilterChip>
        ))}
      </div>

      {appointments.isLoading && <Spinner />}
      <ErrorAlert error={appointments.error} />
      {appointments.data?.items.length === 0 && <EmptyState>No appointments here yet.</EmptyState>}
      {!!appointments.data?.items.length && (
        <ul className="space-y-3">
          {appointments.data.items.map((a) => {
            const when = dateParts(a.start_time)
            return (
              <li key={a.id}>
                <Link to={`/appointments/${a.id}`} className="card flex items-center gap-4 p-4 text-ink no-underline transition-colors hover:border-berry hover:text-ink sm:gap-5 sm:p-5">
                  <div className="flex h-20 w-[72px] shrink-0 flex-col items-center justify-center rounded-md bg-blush text-center text-berry sm:w-20">
                    <span className="text-sm font-semibold">{when.weekday}</span>
                    <span className="text-[1.75rem] font-bold leading-none">{when.day}</span>
                    <span className="text-sm">{when.month}</span>
                  </div>
                  <div className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-h2 font-semibold">{when.time}</p>
                      <p>
                        {a.doctor.name} · {a.department.name}
                      </p>
                      <p className="caption">{a.hospital.name}</p>
                    </div>
                    <div className="flex flex-col items-start gap-2 sm:items-end">
                      <StatusBadge status={a.status} />
                      <StatusBadge status={a.payment_status} kind="payment" />
                      <span className="font-mono text-sm text-muted">{a.booking_reference}</span>
                    </div>
                  </div>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
      {appointments.data && (
        <Pagination page={page} pageSize={appointments.data.page_size} total={appointments.data.total} onChange={setPage} />
      )}
    </div>
  )
}
