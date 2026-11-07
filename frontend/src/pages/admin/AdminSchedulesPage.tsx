import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api } from '../../api/endpoints'
import type { AdminDoctorDetail, AdminSlot, SchedulingMode, SlotCreate } from '../../api/types'
import { Card, ErrorAlert, Field, Notice, Spinner } from '../../components/ui'
import { CLINIC_TZ, clinicDateTime, formatTime, upcomingDays } from '../../lib/format'
import { AdminNav } from './AdminNav'

function SlotForm({ day, editing, busy, onSave, onCancel }: {
  day: string
  editing: AdminSlot | null
  busy: boolean
  onSave: (body: SlotCreate) => Promise<unknown>
  onCancel: () => void
}) {
  const [error, setError] = useState<unknown>(null)
  const errorRef = useRef<HTMLDivElement>(null)
  const locked = (editing?.booked_count ?? 0) > 0

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    const form = event.currentTarget
    const data = new FormData(form)
    try {
      const body: SlotCreate = {
        start_time: clinicDateTime(day, String(data.get('start'))),
        end_time: clinicDateTime(day, String(data.get('end'))),
        buffer_minutes: Number(data.get('buffer')), capacity: Number(data.get('capacity')),
        is_open: data.get('open') === 'on',
      }
      const duration = (Date.parse(body.end_time) - Date.parse(body.start_time)) / 60000
      if (duration < 5 || duration > 480) throw new Error('End time must be 5–480 minutes after start time.')
      setError(null)
      await onSave(body)
      if (!editing) form.reset()
    } catch (err) {
      setError(err)
      requestAnimationFrame(() => errorRef.current?.focus())
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <div ref={errorRef} tabIndex={-1}><ErrorAlert error={error} /></div>
      {locked && <Notice>Times and buffer are locked while this slot has active bookings. Capacity and opening state can still change.</Notice>}
      <fieldset disabled={busy} className="grid gap-5 sm:grid-cols-2">
        <Field label="Start time">
          <input className="input" type="time" name="start" required readOnly={locked}
            defaultValue={editing ? formatTime(editing.start_time) : '08:00'} />
        </Field>
        <Field label="End time">
          <input className="input" type="time" name="end" required readOnly={locked}
            defaultValue={editing ? formatTime(editing.end_time) : '08:30'} />
        </Field>
        <Field label="Buffer after slot (min)" hint="Reserved after the shared slot, 0–120 whole minutes.">
          <input className="input" type="number" name="buffer" min={0} max={120} step={1}
            required readOnly={locked} defaultValue={editing?.buffer_minutes ?? 0} />
        </Field>
        <Field label="Slot capacity" hint="Total patients who may reserve this exact interval.">
          <input className="input" type="number" name="capacity" min={1} max={2147483647} step={1}
            required defaultValue={editing?.capacity ?? 1} />
        </Field>
        <label className="flex items-center gap-3 sm:col-span-2">
          <input className="h-5 w-5" type="checkbox" name="open" defaultChecked={editing?.is_open ?? true} />
          Open for new bookings
        </label>
        <div className="flex flex-wrap gap-3 sm:col-span-2">
          <button className="btn-primary" disabled={busy}>{busy ? 'Saving…' : editing ? 'Save slot' : 'Create slot'}</button>
          {editing && <button className="btn-secondary" type="button" onClick={onCancel}>Cancel edit</button>}
        </div>
      </fieldset>
    </form>
  )
}

export default function AdminSchedulesPage() {
  const queryClient = useQueryClient()
  const [selectedDoctor, setSelectedDoctor] = useState('')
  const [day, setDay] = useState(() => upcomingDays(2)[1].value)
  const [editing, setEditing] = useState<AdminSlot | null>(null)
  const [modeDraft, setModeDraft] = useState<SchedulingMode>('ERP')
  const [feedback, setFeedback] = useState('')
  const doctors = useQuery({ queryKey: ['admin', 'doctors'], queryFn: () => api.admin.list<AdminDoctorDetail>('doctors') })
  const doctorId = Number(selectedDoctor || doctors.data?.[0]?.id || 0)
  const doctor = doctors.data?.find((item) => item.id === doctorId)
  const slots = useQuery({
    queryKey: ['admin', 'slots', doctorId, day],
    queryFn: () => api.admin.slots(doctorId, day), enabled: !!doctorId && !!day,
  })
  useEffect(() => {
    setModeDraft(doctor?.scheduling_mode ?? 'ERP')
  }, [doctorId, doctor?.scheduling_mode])
  useEffect(() => {
    setEditing(null)
    setFeedback('')
  }, [doctorId, day])

  async function invalidate() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin', 'slots'] }),
      queryClient.invalidateQueries({ queryKey: ['admin', 'doctors'] }),
      queryClient.invalidateQueries({ queryKey: ['doctors'] }),
      queryClient.invalidateQueries({ queryKey: ['availability'] }),
    ])
  }
  const changeMode = useMutation({
    mutationFn: () => api.admin.update<AdminDoctorDetail>('doctors', doctorId, { scheduling_mode: modeDraft }),
    onSuccess: async () => { await invalidate(); setFeedback('Scheduling mode saved.') },
  })
  const save = useMutation({
    mutationFn: (body: SlotCreate) => editing
      ? api.admin.updateSlot(doctorId, editing.id, { ...body, version: editing.version })
      : api.admin.createSlot(doctorId, body),
    onSuccess: async () => { await invalidate(); setEditing(null); setFeedback('Slot saved.') },
  })
  const busy = changeMode.isPending || save.isPending

  return (
    <div>
      <h1 className="page-title mb-6">Doctor schedules</h1>
      <AdminNav />
      <p className="mb-6 text-muted">Create dated slots and set the number of patients who can book each one. All times use {slots.data?.timezone ?? CLINIC_TZ}.</p>
      {doctors.isLoading && <Spinner />}
      <ErrorAlert error={doctors.error} />
      {doctors.data?.length === 0 && <Notice>Add a doctor in Directory before creating slots.</Notice>}
      <div className="mb-6 grid gap-5 sm:grid-cols-2">
        <Field label="Doctor">
          <select className="input" value={doctorId || ''} disabled={busy} onChange={(event) => {
            setSelectedDoctor(event.target.value); changeMode.reset(); save.reset()
          }}>
            {!doctorId && <option value="">Select a doctor</option>}
            {doctors.data?.map((item) => <option value={item.id} key={item.id}>{item.full_name} · {item.specialty.name}</option>)}
          </select>
        </Field>
        <Field label="Slot date">
          <input className="input" type="date" required value={day} disabled={busy} onChange={(event) => {
            setDay(event.target.value); save.reset()
          }} />
        </Field>
      </div>
      {doctor && <>
        <Card className="mb-6 space-y-4">
          <h2 className="section-title">Scheduling source</h2>
          <div className="flex flex-wrap items-end gap-4">
            <Field label="Scheduling mode">
              <select className="input" value={modeDraft} disabled={busy} onChange={(event) => setModeDraft(event.target.value as SchedulingMode)}>
                <option value="ERP">ERP — hospital schedules</option>
                <option value="MANUAL">Manual — admin-managed slots</option>
              </select>
            </Field>
            <button className="btn-secondary" disabled={busy || modeDraft === doctor.scheduling_mode} onClick={() => changeMode.mutate()}>Save mode</button>
          </div>
          <p className="caption">Mode changes require no upcoming or ongoing active appointments. You can prepare manual slots while ERP mode is selected.</p>
          <ErrorAlert error={changeMode.error} />
          {doctor.scheduling_mode === 'ERP'
            ? <Notice>ERP schedules are currently offered to patients. Manual slots below will be available after switching this doctor to Manual.</Notice>
            : <Notice>CareBook confirms reservations immediately. Each slot has its own capacity; the ERP work-window limit does not apply.</Notice>}
        </Card>
        {feedback && <p role="status" className="mb-5 font-semibold text-success">{feedback}</p>}
        <div className="grid items-start gap-6 lg:grid-cols-2">
          <Card className="min-w-0 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="section-title">Slots on {day}</h2>
              <button className="btn-secondary btn-sm" disabled={busy || slots.isFetching} onClick={() => slots.refetch()}>Refresh slots</button>
            </div>
            <ErrorAlert error={slots.error} />
            {slots.isLoading && <Spinner />}
            {slots.data?.slots.length === 0 && <p className="text-muted">No manual slots on this date.</p>}
            <ul className="divide-y divide-line">
              {slots.data?.slots.map((slot) => <li key={slot.id} className="flex flex-wrap items-center justify-between gap-4 py-4">
                <div>
                  <p className="font-semibold">{formatTime(slot.start_time)}–{formatTime(slot.end_time)} <span className="tag">{slot.is_open ? 'Open' : 'Closed'}</span></p>
                  <p className="caption">{slot.booked_count} booked / {slot.capacity} places · {slot.remaining_places} remaining · {slot.buffer_minutes} min buffer</p>
                  {slot.booked_count > slot.capacity && <p className="caption">Existing bookings exceed the new capacity. No more reservations are offered.</p>}
                </div>
                <button className="btn-secondary btn-sm" disabled={busy} aria-label={`Edit slot ${formatTime(slot.start_time)}`} onClick={() => { setEditing(slot); save.reset(); setFeedback('') }}>Edit</button>
              </li>)}
            </ul>
          </Card>
          <Card className="min-w-0 space-y-4">
            <h2 className="section-title">{editing ? 'Edit slot' : 'Create slot'}</h2>
            <SlotForm key={`${doctorId}-${day}-${editing?.id ?? 'new'}`} day={day} editing={editing}
              busy={busy} onSave={(body) => save.mutateAsync(body)} onCancel={() => setEditing(null)} />
            <p className="caption">Slots, including their buffers, cannot overlap. Closed slots keep their interval; edit or reopen an existing slot instead of creating a replacement.</p>
          </Card>
        </div>
      </>}
    </div>
  )
}
