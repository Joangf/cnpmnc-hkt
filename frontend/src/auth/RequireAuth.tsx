import { Navigate, Outlet, useLocation } from 'react-router-dom'
import type { UserRole } from '../api/types'
import { Card, Spinner } from '../components/ui'
import { useAuth } from './AuthContext'

/** Route guard for patient-only (BR-01) and admin-only (BR-13) areas. */
export function RequireAuth({ role }: { role: UserRole }) {
  const { user, ready } = useAuth()
  const location = useLocation()

  if (!ready) return <Spinner />
  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  if (user.role !== role) {
    return (
      <Card>
        <h1 className="page-title">Not available</h1>
        <p className="mt-3">This page is not available for your account type.</p>
      </Card>
    )
  }
  return <Outlet />
}
