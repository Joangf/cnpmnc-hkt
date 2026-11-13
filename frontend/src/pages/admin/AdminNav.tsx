import { useQuery } from '@tanstack/react-query'
import { NavLink } from 'react-router-dom'
import { api } from '../../api/endpoints'

const items = [
  { to: '/admin', label: 'Overview', end: true },
  { to: '/admin/directory', label: 'Directory' },
  { to: '/admin/schedules', label: 'Schedules' },
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/reviews', label: 'Reviews' },
  { to: '/admin/refunds', label: 'Refunds' },
  { to: '/admin/audit-logs', label: 'Audit logs' },
]

export function AdminNav() {
  const pendingRefunds = useQuery({
    queryKey: ['admin', 'refunds', 'REQUESTED', 1],
    queryFn: () => api.admin.refunds({ refund_status: 'REQUESTED', page: 1 }),
    refetchInterval: 30_000,
  })
  const requestedCount = pendingRefunds.data?.total ?? 0

  return (
    <nav aria-label="Administration" className="mb-8 flex flex-wrap gap-2">
      {items.map((i) => (
        <NavLink
          key={i.to}
          to={i.to}
          end={i.end}
          className={({ isActive }) =>
            `chip no-underline ${isActive ? 'border-berry bg-blush font-semibold text-berry' : 'hover:text-berry'}`
          }
        >
          {i.label}
          {i.to === '/admin/refunds' && requestedCount > 0 && (
            <span className="ml-1.5 inline-flex min-w-5 items-center justify-center rounded-full bg-berry px-1.5 text-[11px] font-bold text-white">
              {requestedCount}
            </span>
          )}
        </NavLink>
      ))}
    </nav>
  )
}
