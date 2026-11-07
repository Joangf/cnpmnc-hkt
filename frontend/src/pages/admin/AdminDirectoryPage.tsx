import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect, type FormEvent } from 'react'
import { api, type AdminEntity } from '../../api/endpoints'
import type { AppointmentTypeAdmin, Department, DoctorDetail, HospitalDetail, Specialty } from '../../api/types'
import { Card, ErrorAlert, FilterChip, Spinner } from '../../components/ui'
import { formatMoney } from '../../lib/format'
import { AdminNav } from './AdminNav'

// FR-ADM-02: manage directory data. Deletion is a soft deactivate to preserve history.

interface FieldDef {
  name: string
  label: string
  type?: 'text' | 'number' | 'textarea' | 'select'
  required?: boolean
  options?: { value: string | number; label: string }[]
}

type Row = {
  id: number
  is_active: boolean
  title: string
  subtitle: string
  raw: Record<string, unknown>
}

function EntityForm({
  fields,
  initialValues,
  onSubmit,
  onCancel,
  busy,
  submitLabel = 'Create',
}: {
  fields: FieldDef[]
  initialValues?: Record<string, unknown> | null
  onSubmit: (body: Record<string, unknown>) => void
  onCancel?: () => void
  busy: boolean
  submitLabel?: string
}) {
  const [formState, setFormState] = useState<Record<string, unknown>>(initialValues ?? {})

  useEffect(() => {
    setFormState(initialValues ?? {})
  }, [initialValues])

  const handle = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const body: Record<string, unknown> = {}
    for (const f of fields) {
      const val = formState[f.name]
      if (val === undefined || val === null || val === '') {
        if (!initialValues) continue
        body[f.name] = null
        continue
      }
      body[f.name] = f.type === 'number' || (f.type === 'select' && /^\d+$/.test(String(val))) ? Number(val) : val
    }
    onSubmit(body)
    if (!initialValues) {
      setFormState({})
      e.currentTarget.reset()
    }
  }

  return (
    <form className="grid gap-5 sm:grid-cols-2" onSubmit={handle}>
      {fields.map((f) => (
        <label key={f.name} className={f.type === 'textarea' ? 'sm:col-span-2' : ''}>
          <span className="label">
            {f.label}
            {f.required && ' *'}
          </span>
          {f.type === 'textarea' ? (
            <textarea
              name={f.name}
              className="input"
              rows={2}
              required={f.required}
              value={String(formState[f.name] ?? '')}
              onChange={(e) => setFormState({ ...formState, [f.name]: e.target.value })}
            />
          ) : f.type === 'select' ? (
            <select
              name={f.name}
              className="input"
              required={f.required}
              value={String(formState[f.name] ?? '')}
              onChange={(e) => setFormState({ ...formState, [f.name]: e.target.value })}
            >
              <option value="">—</option>
              {f.options?.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          ) : (
            <input
              name={f.name}
              className="input"
              type={f.type ?? 'text'}
              required={f.required}
              min={f.type === 'number' ? 0 : undefined}
              value={String(formState[f.name] ?? '')}
              onChange={(e) => setFormState({ ...formState, [f.name]: e.target.value })}
            />
          )}
        </label>
      ))}
      <div className="flex flex-wrap gap-3 sm:col-span-2">
        <button className="btn-primary" disabled={busy}>
          {busy ? 'Saving…' : submitLabel}
        </button>
        {onCancel && (
          <button type="button" className="btn-secondary" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}

export default function AdminDirectoryPage() {
  const queryClient = useQueryClient()
  const [entity, setEntity] = useState<AdminEntity>('appointment-types')
  const [editing, setEditing] = useState<Row | null>(null)

  const specialties = useQuery({ queryKey: ['admin', 'specialties'], queryFn: () => api.admin.list<Specialty>('specialties') })
  const hospitals = useQuery({ queryKey: ['admin', 'hospitals'], queryFn: () => api.admin.list<HospitalDetail>('hospitals') })
  const departments = useQuery({ queryKey: ['admin', 'departments'], queryFn: () => api.admin.list<Department>('departments') })
  const doctors = useQuery({ queryKey: ['admin', 'doctors'], queryFn: () => api.admin.list<DoctorDetail>('doctors') })
  const types = useQuery({ queryKey: ['admin', 'appointment-types'], queryFn: () => api.admin.list<AppointmentTypeAdmin>('appointment-types') })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['admin'] })
    queryClient.invalidateQueries({ queryKey: ['hospitals'] })
    queryClient.invalidateQueries({ queryKey: ['doctors'] })
    queryClient.invalidateQueries({ queryKey: ['specialties'] })
  }
  const create = useMutation({ mutationFn: (body: Record<string, unknown>) => api.admin.create(entity, body), onSuccess: invalidate })
  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Record<string, unknown> }) => api.admin.update(entity, id, body),
    onSuccess: () => {
      invalidate()
      setEditing(null)
    },
  })
  const toggle = useMutation({
    mutationFn: (row: Row) => api.admin.update(entity, row.id, { is_active: !row.is_active }),
    onSuccess: invalidate,
  })

  const hospitalName = new Map(hospitals.data?.map((h) => [h.id, h.name] as const))
  const specialtyOptions = specialties.data?.map((s) => ({ value: s.id, label: s.name })) ?? []

  const config: Record<AdminEntity, { label: string; rows: Row[] | undefined; fields: FieldDef[] }> = {
    hospitals: {
      label: 'Hospitals & clinics',
      rows: hospitals.data?.map((h) => ({
        id: h.id,
        is_active: h.is_active,
        title: h.name,
        subtitle: `${h.address}, ${h.city}`,
        raw: {
          name: h.name,
          facility_type: h.facility_type,
          address: h.address,
          city: h.city,
          phone: h.phone ?? '',
          email: h.email ?? '',
          description: h.description ?? '',
        },
      })),
      fields: [
        { name: 'name', label: 'Name', required: true },
        { name: 'facility_type', label: 'Type', type: 'select', options: [{ value: 'HOSPITAL', label: 'Hospital' }, { value: 'CLINIC', label: 'Clinic' }] },
        { name: 'address', label: 'Address', required: true },
        { name: 'city', label: 'City', required: true },
        { name: 'phone', label: 'Phone' },
        { name: 'email', label: 'Email' },
        { name: 'description', label: 'Description', type: 'textarea' },
      ],
    },
    specialties: {
      label: 'Specialties',
      rows: specialties.data?.map((s) => ({
        id: s.id,
        is_active: s.is_active,
        title: s.name,
        subtitle: s.description ?? '',
        raw: { name: s.name, description: s.description ?? '' },
      })),
      fields: [
        { name: 'name', label: 'Name', required: true },
        { name: 'description', label: 'Description', type: 'textarea' },
      ],
    },
    departments: {
      label: 'Departments',
      rows: departments.data?.map((d) => ({
        id: d.id,
        is_active: d.is_active,
        title: d.name,
        subtitle: `${hospitalName.get(d.hospital_id) ?? `Hospital #${d.hospital_id}`} · ${d.specialty.name}`,
        raw: { name: d.name, hospital_id: d.hospital_id, specialty_id: d.specialty.id, description: d.description ?? '' },
      })),
      fields: [
        { name: 'hospital_id', label: 'Hospital', type: 'select', required: true, options: hospitals.data?.map((h) => ({ value: h.id, label: h.name })) },
        { name: 'specialty_id', label: 'Specialty', type: 'select', required: true, options: specialtyOptions },
        { name: 'name', label: 'Name', required: true },
        { name: 'description', label: 'Description', type: 'textarea' },
      ],
    },
    doctors: {
      label: 'Doctors',
      rows: doctors.data?.map((d) => ({
        id: d.id,
        is_active: d.is_active,
        title: d.full_name,
        subtitle: `${d.hospital.name} · ${d.department.name} · ERP ${d.erp_doctor_id ?? 'not linked'}`,
        raw: {
          full_name: d.full_name,
          department_id: d.department.id,
          title: d.title ?? '',
          experience_years: d.experience_years,
          erp_doctor_id: d.erp_doctor_id ?? '',
          qualifications: d.qualifications ?? '',
          introduction: d.introduction ?? '',
        },
      })),
      fields: [
        {
          name: 'department_id',
          label: 'Department',
          type: 'select',
          required: true,
          options: departments.data?.map((d) => ({ value: d.id, label: `${d.name} (${hospitalName.get(d.hospital_id) ?? d.hospital_id})` })),
        },
        { name: 'full_name', label: 'Full name', required: true },
        { name: 'title', label: 'Title' },
        { name: 'experience_years', label: 'Years of experience', type: 'number' },
        { name: 'erp_doctor_id', label: 'ERP doctor ID' },
        { name: 'qualifications', label: 'Qualifications', type: 'textarea' },
        { name: 'introduction', label: 'Introduction', type: 'textarea' },
      ],
    },
    'appointment-types': {
      label: 'Consultation fee',
      rows: types.data?.map((t) => ({
        id: t.id,
        is_active: t.is_active,
        title: t.name,
        subtitle: `${t.fee_override ? formatMoney(t.fee_override) : 'No fee'} · ${t.duration_minutes} min duration`,
        raw: {
          name: t.name,
          fee_override: t.fee_override ?? '',
          duration_minutes: t.duration_minutes,
          buffer_minutes: t.buffer_minutes,
          description: t.description ?? '',
        },
      })),
      fields: [
        { name: 'name', label: 'Name', required: true },
        { name: 'fee_override', label: 'Consultation fee (VND)', type: 'number', required: true },
        { name: 'duration_minutes', label: 'Slot duration (min)', type: 'number', required: true },
        { name: 'description', label: 'Description', type: 'textarea' },
      ],
    },
  }
  const current = config[entity]

  return (
    <div>
      <h1 className="page-title mb-6">Administration</h1>
      <AdminNav />
      <div className="mb-6 flex flex-wrap gap-3">
        {(Object.keys(config) as AdminEntity[]).map((key) => (
          <FilterChip
            key={key}
            pressed={key === entity}
            onClick={() => {
              setEntity(key)
              setEditing(null)
            }}
          >
            {config[key].label}
          </FilterChip>
        ))}
      </div>

      <div className="grid gap-8 lg:grid-cols-5">
        <Card className="min-w-0 lg:col-span-3">
          <h2 className="section-title mb-3">{current.label}</h2>
          {!current.rows && <Spinner />}
          <ErrorAlert error={toggle.error} />
          <ul className="divide-y divide-line">
            {current.rows?.map((row) => (
              <li key={row.id} className="flex items-center justify-between gap-3 py-3">
                <div className={`min-w-0 ${row.is_active ? '' : 'text-muted'}`}>
                  <div className="flex flex-wrap items-center gap-2 font-semibold">
                    {row.title}
                    {!row.is_active && <span className="tag">Inactive</span>}
                  </div>
                  <div className="caption">{row.subtitle}</div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <button className="btn-secondary btn-sm" type="button" onClick={() => setEditing(row)}>
                    Edit
                  </button>
                  <button className="btn-secondary btn-sm" type="button" onClick={() => toggle.mutate(row)}>
                    {row.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="min-w-0 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="section-title">{editing ? `Edit: ${editing.title}` : 'Add new'}</h2>
            {editing && (
              <button className="btn-secondary btn-sm" type="button" onClick={() => setEditing(null)}>
                Cancel
              </button>
            )}
          </div>
          <EntityForm
            key={`${entity}-${editing?.id ?? 'new'}`}
            fields={current.fields}
            initialValues={editing?.raw}
            onSubmit={(body) => (editing ? update.mutate({ id: editing.id, body }) : create.mutate(body))}
            onCancel={editing ? () => setEditing(null) : undefined}
            busy={create.isPending || update.isPending}
            submitLabel={editing ? 'Save changes' : 'Create'}
          />
          <div className="mt-3">
            <ErrorAlert error={create.error ?? update.error} />
          </div>
        </Card>
      </div>
    </div>
  )
}
