import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api/endpoints'
import type { AdminDoctorDetail } from '../../api/types'
import { Card, ErrorAlert, Field, Notice, Spinner } from '../../components/ui'
import { CLINIC_TZ, formatDateTime, formatTime, upcomingDays } from '../../lib/format'
import { AdminNav } from './AdminNav'

export default function AdminSchedulesPage() {
  const [selected, setSelected] = useState('')
  const [day, setDay] = useState(() => upcomingDays(2)[1].value)
  const doctors = useQuery({ queryKey: ['admin', 'doctors'], queryFn: () => api.admin.list<AdminDoctorDetail>('doctors') })
  const doctorId = Number(selected || doctors.data?.[0]?.id || 0)
  const slots = useQuery({ queryKey: ['admin', 'slots', doctorId, day], queryFn: () => api.admin.slots(doctorId, day), enabled: !!doctorId && !!day, refetchInterval: 30_000 })
  return <div>
    <h1 className="page-title mb-6">Doctor schedules</h1><AdminNav />
    <Notice>Schedules and capacity are managed by the hospital ERP. This page is read-only.</Notice>
    <p className="caption my-4">All times use {slots.data?.timezone ?? CLINIC_TZ}.</p>
    <p className="caption mb-4">{slots.data?.synced_at ? `Last synced: ${formatDateTime(slots.data.synced_at)}` : 'Awaiting ERP synchronization.'}</p>
    <ErrorAlert error={doctors.error ?? slots.error} />
    <div className="mb-6 grid gap-5 sm:grid-cols-2">
      <Field label="Doctor"><select className="input" value={doctorId || ''} onChange={e => setSelected(e.target.value)}>
        {!doctorId && <option value="">Select a doctor</option>}
        {doctors.data?.map(d => <option key={d.id} value={d.id}>{d.full_name} · {d.specialty.name}</option>)}
      </select></Field>
      <Field label="Slot date"><input className="input" type="date" value={day} onChange={e => setDay(e.target.value)} /></Field>
    </div>
    {(doctors.isLoading || slots.isLoading) && <Spinner />}
    <Card><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="section-title">Slots on {day}</h2><button className="btn-secondary btn-sm" disabled={!doctorId || slots.isFetching} onClick={() => slots.refetch()}>Refresh slots</button></div>
      {slots.data?.slots.length === 0 && <p className="mt-4">No slots on this date.</p>}
      <ul className="divide-y divide-line">{slots.data?.slots.map(slot => <li className="space-y-2 py-4" key={slot.id}>
        <p className="font-semibold">{formatTime(slot.start_time)}–{formatTime(slot.end_time)} <span className="tag">{slot.is_open ? 'Open' : 'Closed'}</span></p>
        <p className="caption">{slot.booked_count} booked / {slot.capacity} places · {slot.remaining_places} remaining</p>
      </li>)}</ul>
    </Card>
  </div>
}
