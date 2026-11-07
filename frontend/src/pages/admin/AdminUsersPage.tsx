import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api/endpoints'
import { useAuth } from '../../auth/AuthContext'
import { Card, ErrorAlert, Pagination, Spinner } from '../../components/ui'
import { formatDateTime, humanize } from '../../lib/format'
import { AdminNav } from './AdminNav'

export default function AdminUsersPage() {
  const { user: me } = useAuth()
  const queryClient = useQueryClient()
  const [q, setQ] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const users = useQuery({
    queryKey: ['admin', 'users', search, page],
    queryFn: () => api.admin.users({ q: search || undefined, page }),
    placeholderData: keepPreviousData,
  })
  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => api.admin.setUserStatus(id, active ? 'INACTIVE' : 'ACTIVE'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })

  return (
    <div>
      <h1 className="page-title mb-6">Administration</h1>
      <AdminNav />
      <form
        className="mb-6 flex flex-wrap gap-3"
        onSubmit={(e) => {
          e.preventDefault()
          setSearch(q.trim())
          setPage(1)
        }}
      >
        <input className="input mt-0 min-w-0 flex-[1_1_260px]" type="search" aria-label="Search users" placeholder="Search email or name" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn-secondary">Search</button>
      </form>
      {users.isLoading && <Spinner />}
      <ErrorAlert error={users.error ?? toggle.error} />
      <Card className="overflow-x-auto p-0 sm:p-0">
        <table className="table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Name</th>
              <th>Role</th>
              <th>Last sign-in</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.data?.items.map((u) => (
              <tr key={u.id}>
                <td className="font-semibold">{u.email}</td>
                <td>{u.full_name ?? '-'}</td>
                <td>{humanize(u.role)}</td>
                <td>{u.last_login_at ? formatDateTime(u.last_login_at) : '-'}</td>
                <td>{humanize(u.account_status)}</td>
                <td className="text-right">
                  {u.id !== me?.id && (
                    <button className="btn-secondary btn-sm" onClick={() => toggle.mutate({ id: u.id, active: u.account_status === 'ACTIVE' })}>
                      {u.account_status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {users.data && <Pagination page={page} pageSize={users.data.page_size} total={users.data.total} onChange={setPage} />}
    </div>
  )
}
