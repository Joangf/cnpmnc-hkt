import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Fragment, useState, type ChangeEvent, type FormEvent } from 'react'
import { api } from '../../api/endpoints'
import type { AuditLog } from '../../api/types'
import { EmptyState, ErrorAlert, Field, Pagination, Spinner } from '../../components/ui'
import { formatDateTime, humanize } from '../../lib/format'
import { AdminNav } from './AdminNav'

const ENTITY_TYPES = [
  'appointment',
  'payment',
  'doctor_slot',
  'doctor_schedule',
  'review',
  'user',
  'patient_profile',
  'specialty',
  'hospital',
  'department',
  'doctor',
  'appointment_type',
  'integration',
]

const ACTOR_TYPES = [
  { value: 'USER', label: 'User' },
  { value: 'SYSTEM', label: 'System' },
  { value: 'ERP', label: 'ERP' },
  { value: 'PAYMENT_GATEWAY', label: 'Payment gateway' },
]

const ACTION_SUGGESTIONS = [
  'appointment.created',
  'appointment.status_changed',
  'appointment.rescheduled',
  'appointment.check_in_changed',
  'payment.initiated',
  'payment.status_changed',
  'payment.refund_requested',
  'payment.refunded',
  'payment.refund_rejected',
  'doctor_slot.created',
  'doctor_slot.updated',
  'review.created',
  'review.moderated',
  'user.registered',
  'user.status_changed',
  'profile.updated',
  'erp.catalog_synced',
  'erp.schedule_sync',
]

interface Filters {
  actor: string
  actor_type: string
  appointment: string
  entity_type: string
  action: string
  date_from: string
  date_to: string
}

const EMPTY_FILTERS: Filters = {
  actor: '',
  actor_type: '',
  appointment: '',
  entity_type: '',
  action: '',
  date_from: '',
  date_to: '',
}

const hasFilters = (filters: Filters) => Object.values(filters).some((value) => value.trim() !== '')

export default function AdminAuditLogsPage() {
  const [draft, setDraft] = useState<Filters>(EMPTY_FILTERS)
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [openId, setOpenId] = useState<number | null>(null)
  const audit = useQuery({
    queryKey: ['admin', 'audit', filters, page],
    queryFn: () =>
      api.admin.auditLogs({
        actor: filters.actor.trim() || undefined,
        actor_type: filters.actor_type || undefined,
        appointment: filters.appointment.trim() || undefined,
        entity_type: filters.entity_type || undefined,
        action: filters.action.trim() || undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
        page,
      }),
    placeholderData: keepPreviousData,
  })

  const bind = (key: keyof Filters) => (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setDraft((current) => ({ ...current, [key]: event.target.value }))

  const apply = (event: FormEvent) => {
    event.preventDefault()
    setPage(1)
    setOpenId(null)
    setFilters({ ...draft })
  }

  const clear = () => {
    setDraft(EMPTY_FILTERS)
    setFilters(EMPTY_FILTERS)
    setPage(1)
    setOpenId(null)
  }

  return (
    <div>
      <h1 className="page-title mb-6">Administration</h1>
      <AdminNav />

      <form className="card mb-6" onSubmit={apply}>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Field label="User" hint="Email or full name of the person who acted.">
            <input
              className="input"
              type="search"
              value={draft.actor}
              onChange={bind('actor')}
              placeholder="e.g. patient@example.com"
            />
          </Field>
          <Field label="Actor type">
            <select className="input" value={draft.actor_type} onChange={bind('actor_type')}>
              <option value="">All actors</option>
              {ACTOR_TYPES.map((actorType) => (
                <option key={actorType.value} value={actorType.value}>
                  {actorType.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Appointment" hint="Booking reference or numeric appointment id.">
            <input
              className="input"
              type="search"
              value={draft.appointment}
              onChange={bind('appointment')}
              placeholder="e.g. HKT-2026-00042"
            />
          </Field>
          <Field label="Entity type">
            <select className="input" value={draft.entity_type} onChange={bind('entity_type')}>
              <option value="">All types</option>
              {ENTITY_TYPES.map((type) => (
                <option key={type} value={type}>
                  {humanize(type)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Action">
            <input
              className="input"
              list="audit-actions"
              value={draft.action}
              onChange={bind('action')}
              placeholder="e.g. payment.status_changed"
            />
            <datalist id="audit-actions">
              {ACTION_SUGGESTIONS.map((action) => (
                <option key={action} value={action} />
              ))}
            </datalist>
          </Field>
          <Field label="From date">
            <input className="input" type="date" value={draft.date_from} onChange={bind('date_from')} />
          </Field>
          <Field label="To date">
            <input className="input" type="date" value={draft.date_to} onChange={bind('date_to')} />
          </Field>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button className="btn-primary" type="submit">
            Apply filters
          </button>
          <button
            className="btn-secondary"
            type="button"
            onClick={clear}
            disabled={!hasFilters(draft) && !hasFilters(filters)}
          >
            Clear
          </button>
          {hasFilters(filters) && <span className="caption">Filters are active.</span>}
        </div>
      </form>

      {audit.isLoading && <Spinner />}
      <ErrorAlert error={audit.error} />
      {audit.data?.items.length === 0 && (
        <EmptyState>{hasFilters(filters) ? 'No audit entries match these filters.' : 'No audit entries yet.'}</EmptyState>
      )}

      {!!audit.data?.items.length && (
        <div className="card overflow-x-auto p-0 sm:p-0">
          <table className="table">
            <thead>
              <tr>
                <th>Time</th>
                <th>User</th>
                <th>Action</th>
                <th>Entity</th>
                <th>
                  <span className="sr-only">Details</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {audit.data.items.map((log) => (
                <Fragment key={log.id}>
                  <tr>
                    <td className="whitespace-nowrap">{formatDateTime(log.created_at)}</td>
                    <td>
                      <div className="font-semibold">{actorLabel(log)}</div>
                      <div className="caption">{humanize(log.actor_type)}</div>
                    </td>
                    <td className="font-mono text-sm">{log.action}</td>
                    <td className="whitespace-nowrap">
                      {log.entity_type}
                      {log.entity_id ? ` #${log.entity_id}` : ''}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn-secondary btn-sm"
                        aria-expanded={openId === log.id}
                        onClick={() => setOpenId(openId === log.id ? null : log.id)}
                      >
                        {openId === log.id ? 'Hide' : 'Details'}
                      </button>
                    </td>
                  </tr>
                  {openId === log.id && (
                    <tr>
                      <td colSpan={5} className="bg-surface">
                        <ChangeDetails log={log} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {audit.data && (
        <>
          <p className="caption mt-4">
            Showing {audit.data.items.length} of {audit.data.total} entries.
          </p>
          <Pagination
            page={page}
            pageSize={audit.data.page_size}
            total={audit.data.total}
            onChange={(next) => {
              setOpenId(null)
              setPage(next)
            }}
          />
        </>
      )}
    </div>
  )
}

function actorLabel(log: AuditLog) {
  if (log.actor_name && log.actor_email) return `${log.actor_name} · ${log.actor_email}`
  if (log.actor_email) return log.actor_email
  if (log.actor_id) return `User #${log.actor_id}`
  return humanize(log.actor_type)
}

function ChangeDetails({ log }: { log: AuditLog }) {
  const details = log.details ?? {}
  const entries = Object.entries(details)
  const from = details.from
  const to = details.to
  const change = from !== undefined && to !== undefined ? `${detailValue(from)} → ${detailValue(to)}` : null
  const rest = change ? entries.filter(([key]) => key !== 'from' && key !== 'to') : entries

  return (
    <div className="rounded-lg border border-line bg-canvas p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-semibold">Change details</h3>
        <span className="caption font-mono">Log #{log.id}</span>
      </div>
      {change || rest.length ? (
        <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
          {change && (
            <>
              <dt className="caption">Change</dt>
              <dd className="font-semibold">{change}</dd>
            </>
          )}
          {rest.map(([key, value]) => (
            <Fragment key={key}>
              <dt className="caption">{humanize(key)}</dt>
              <dd className="break-words">{detailValue(value)}</dd>
            </Fragment>
          ))}
        </dl>
      ) : (
        <p className="caption mt-3">No extra change details were recorded for this entry.</p>
      )}
      {log.request_id && <p className="caption mt-3 font-mono">Request {log.request_id}</p>}
    </div>
  )
}

function detailValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (Array.isArray(value)) return value.length ? value.map((item) => String(item)).join(', ') : '—'
  if (typeof value === 'object') return JSON.stringify(value)
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}
