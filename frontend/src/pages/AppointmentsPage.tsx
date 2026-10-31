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
        <ul className="divide-y-3 divide-ink border-3 border-ink">
          {appointments.data.items.map((a) => {
            const when = dateParts(a.start_time)
            return (
              <li key={a.id}>
                <Link to={`/appointments/${a.id}`} className="flex items-stretch hover:bg-grey-100 hover:text-ink">
                  <div className="flex w-20 shrink-0 flex-col items-center justify-center border-r-3 border-ink py-4 text-center sm:w-28">
                    <span className="eyebrow text-sm">{when.weekday}</span>
                    <span className="text-[2rem] font-extrabold leading-none sm:text-[2.5rem]">{when.day}</span>
                    <span className="text-caption font-semibold">{when.month}</span>
                  </div>
                  <div className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-4 p-4 sm:p-5">
                    <div className="min-w-0">
                      <p className="text-h2 font-extrabold">{when.time}</p>
                      <p>
                        {a.doctor.name} · {a.department.name}
                      </p>
                      <p className="caption">{a.hospital.name}</p>
                    </div>
                    <div className="flex flex-col items-start gap-2 sm:items-end">
                      <StatusBadge status={a.status} />
                      <StatusBadge status={a.payment_status} kind="payment" />
                      <span className="font-mono text-sm font-semibold">{a.booking_reference}</span>
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
