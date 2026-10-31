import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../../api/endpoints'
import { StatusBadge } from '../../components/StatusBadge'
import { Card, ErrorAlert, Notice, Spinner } from '../../components/ui'
import { formatDateTime, formatMoney, humanize } from '../../lib/format'
import { AdminNav } from './AdminNav'

export default function AdminDashboardPage() {
  const summary = useQuery({ queryKey: ['admin', 'summary'], queryFn: api.admin.summary, refetchInterval: 30_000 })
  const appointments = useQuery({ queryKey: ['admin', 'appointments'], queryFn: () => api.admin.appointments({}) })
  const audit = useQuery({ queryKey: ['admin', 'audit'], queryFn: () => api.admin.auditLogs() })
  const sync = useMutation({ mutationFn: api.admin.syncSchedules })

  return (
    <div>
      <h1 className="page-title mb-6">Administration</h1>
      <AdminNav />
      {summary.isLoading && <Spinner />}
      <ErrorAlert error={summary.error} />

      {summary.data && (
        <div className="tile-grid md:grid-cols-3">
          <section className="bg-white p-6">
            <h2 className="section-title mb-4">Appointments by status</h2>
            <ul className="space-y-2">
              {Object.entries(summary.data.appointments_by_status).map(([status, count]) => (
                <li key={status} className="flex items-center justify-between gap-3">
                  <StatusBadge status={status} />
                  <span className="text-h2 font-extrabold">{count}</span>
                </li>
              ))}
            </ul>
            <p className="caption mt-4">{summary.data.total_patients} registered patients</p>
          </section>
          <section className="bg-white p-6">
            <h2 className="section-title mb-4">Payments</h2>
            <ul className="divide-y divide-ink">
              {summary.data.payments_by_status.map((p) => (
                <li key={p.status} className="flex justify-between gap-3 py-2">
                  <span>
                    {humanize(p.status)} ({p.count})
                  </span>
                  <span className="font-extrabold">{formatMoney(p.total_amount)}</span>
                </li>
              ))}
            </ul>
          </section>
          <section className="bg-white p-6">
            <h2 className="section-title mb-4">Top recommended specialties</h2>
            <ol className="divide-y divide-ink">
              {summary.data.top_specialties.map((s) => (
                <li key={s.specialty_id} className="flex justify-between gap-3 py-2">
                  <span>{s.name}</span>
                  <span className="font-extrabold">{s.count}</span>
                </li>
              ))}
            </ol>
          </section>
        </div>
      )}

      <Card className="mt-8 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="section-title">ERP schedule sync</h2>
          <button className="btn-secondary btn-sm" disabled={sync.isPending} onClick={() => sync.mutate()}>
            {sync.isPending ? 'Syncing…' : 'Sync schedules now'}
          </button>
        </div>
        <ErrorAlert error={sync.error} />
        {sync.data && (
          <Notice tone={sync.data.success ? 'success' : 'warning'}>
            Synced {sync.data.doctors_synced} doctors{sync.data.success ? '.' : ' (some failed - see logs).'}
          </Notice>
        )}
      </Card>

      <Card className="mt-8 overflow-x-auto">
        <h2 className="section-title mb-3">Recent appointments</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Reference</th>
              <th>When</th>
              <th>Doctor</th>
              <th>Status</th>
              <th>Payment</th>
            </tr>
          </thead>
          <tbody>
            {appointments.data?.items.map((a) => (
              <tr key={a.id}>
                <td className="font-mono font-semibold">{a.booking_reference}</td>
                <td>{formatDateTime(a.start_time)}</td>
                <td>{a.doctor.name}</td>
                <td>
                  <StatusBadge status={a.status} />
                </td>
                <td>
                  <StatusBadge status={a.payment_status} kind="payment" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card className="mt-8 overflow-x-auto">
        <h2 className="section-title mb-3">Audit log</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>Entity</th>
              <th>Actor</th>
            </tr>
          </thead>
          <tbody>
            {audit.data?.items.map((log) => (
              <tr key={log.id}>
                <td>{formatDateTime(log.created_at)}</td>
                <td className="font-mono text-sm">{log.action}</td>
                <td>
                  {log.entity_type} {log.entity_id}
                </td>
                <td>
                  {humanize(log.actor_type)}
                  {log.actor_id ? ` #${log.actor_id}` : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
