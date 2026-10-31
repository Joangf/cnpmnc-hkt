import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/endpoints'
import { EmptyState, ErrorAlert, Spinner } from '../components/ui'
import { formatDateTime } from '../lib/format'

export default function NotificationsPage() {
  const queryClient = useQueryClient()
  const notifications = useQuery({ queryKey: ['notifications'], queryFn: api.notifications.list })
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['notifications'] })
  const markRead = useMutation({ mutationFn: api.notifications.markRead, onSuccess: invalidate })
  const markAll = useMutation({ mutationFn: api.notifications.markAllRead, onSuccess: invalidate })

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h1 className="page-title">Notifications</h1>
        {!!notifications.data?.unread_count && (
          <button className="btn-secondary btn-sm" onClick={() => markAll.mutate()}>
            Mark all as read
          </button>
        )}
      </div>
      {notifications.isLoading && <Spinner />}
      <ErrorAlert error={notifications.error} />
      {notifications.data?.items.length === 0 && <EmptyState>You have no notifications.</EmptyState>}
      {!!notifications.data?.items.length && (
        <ul className="card divide-y divide-line p-0 sm:p-0">
          {notifications.data.items.map((n) => (
            <li key={n.id} className="flex flex-wrap items-start justify-between gap-4 p-4 sm:p-5">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  {!n.read_at && <span className="badge bg-blush text-berry">New</span>}
                  <span className="font-semibold">{n.title}</span>
                </div>
                <p className="mt-1">{n.content}</p>
                <span className="caption">{formatDateTime(n.created_at)}</span>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                {n.link && (
                  <Link className="link inline-flex min-h-12 items-center" to={n.link} onClick={() => !n.read_at && markRead.mutate(n.id)}>
                    View
                  </Link>
                )}
                {!n.read_at && (
                  <button className="btn-secondary btn-sm" onClick={() => markRead.mutate(n.id)}>
                    Mark read
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
