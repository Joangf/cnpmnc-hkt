import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { api, type AdminEntity } from '../../api/endpoints'
import type { AppointmentTypeAdmin, Department, DoctorDetail, HospitalDetail, Specialty } from '../../api/types'
import { Card, ErrorAlert, FilterChip, Spinner } from '../../components/ui'
import { formatMoney } from '../../lib/format'
import { AdminNav } from './AdminNav'

// FR-ADM-02: manage directory data. Deletion is a soft deactivate to preserve history.

type AnyRecord = Record<string, unknown>

interface FieldDef {
  name: string
  label: string
  type?: 'text' | 'number' | 'textarea' | 'select'
  required?: boolean
  /** Not editable once created (the API's update schema does not accept it). */
  createOnly?: boolean
  options?: { value: string | number; label: string }[]
  /** Current value from a listed record, when it is not simply `record[name]`. */
  get?: (record: AnyRecord) => unknown
}

type Row = { id: number; is_active: boolean; title: string; subtitle: string; record: AnyRecord }

const currentValue = (f: FieldDef, record: AnyRecord): string => {
  const value = f.get ? f.get(record) : record[f.name]
  return value === null || value === undefined ? '' : String(value)
}

/**
 * Create form, or edit form when `editing` is set. On edit only changed fields are sent, and a
 * cleared optional field is sent as null. The form keeps its input when the server rejects it.
 */
function EntityForm({
  fields,
  editing,
  onSubmit,
  onCancel,
  busy,
}: {
  fields: FieldDef[]
  editing?: AnyRecord
  onSubmit: (body: AnyRecord) => Promise<unknown>
  onCancel?: () => void
  busy: boolean
}) {
  const visible = editing ? fields.filter((f) => !f.createOnly) : fields
  const handle = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = e.currentTarget
    const data = new FormData(form)
    const body: AnyRecord = {}
    for (const f of visible) {
      const raw = String(data.get(f.name) ?? '').trim()
      if (editing && raw === currentValue(f, editing)) continue
      if (raw === '') {
        if (editing) body[f.name] = null
        continue
      }
      body[f.name] = f.type === 'number' || (f.type === 'select' && /^\d+$/.test(raw)) ? Number(raw) : raw
    }
    if (editing && Object.keys(body).length === 0) return onCancel?.()
    try {
      await onSubmit(body)
      if (!editing) form.reset()
    } catch {
      // Shown by the caller's <ErrorAlert>; keep the input so the admin can correct it.
    }
  }
  return (
    <form className="grid gap-5 sm:grid-cols-2" onSubmit={handle}>
      {visible.map((f) => {
        const initial = editing ? currentValue(f, editing) : ''
        return (
          <label key={f.name} className={f.type === 'textarea' ? 'sm:col-span-2' : ''}>
            <span className="label">
              {f.label}
              {f.required && ' *'}
            </span>
            {f.type === 'textarea' ? (
              <textarea name={f.name} className="input" rows={2} required={f.required} defaultValue={initial} />
            ) : f.type === 'select' ? (
              <select name={f.name} className="input" required={f.required} defaultValue={initial}>
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
                step={f.type === 'number' ? 'any' : undefined}
                defaultValue={initial}
              />
            )}
          </label>
        )
      })}
      <div className="flex gap-3 sm:col-span-2">
        <button className="btn-primary" disabled={busy}>
          {editing ? 'Save changes' : 'Create'}
        </button>
        {editing && (
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
  const [entity, setEntity] = useState<AdminEntity>('hospitals')
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
  const create = useMutation({ mutationFn: (body: AnyRecord) => api.admin.create(entity, body), onSuccess: invalidate })
  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: AnyRecord }) => api.admin.update(entity, id, body),
    onSuccess: () => {
      invalidate()
      setEditing(null)
    },
  })
  const selectEntity = (key: AdminEntity) => {
    setEntity(key)
    setEditing(null)
    create.reset()
    update.reset()
  }
  const toggle = useMutation({
    mutationFn: (row: Row) => api.admin.update(entity, row.id, { is_active: !row.is_active }),
    onSuccess: invalidate,
  })

  const hospitalName = new Map(hospitals.data?.map((h) => [h.id, h.name] as const))
  const specialtyOptions = specialties.data?.map((s) => ({ value: s.id, label: s.name })) ?? []

  const config: Record<AdminEntity, { label: string; rows: Row[] | undefined; fields: FieldDef[] }> = {
    hospitals: {
      label: 'Hospitals & clinics',
      rows: hospitals.data?.map((h) => ({ id: h.id, is_active: h.is_active, title: h.name, subtitle: `${h.address}, ${h.city}`, record: { ...h } })),
      fields: [
        { name: 'name', label: 'Name', required: true },
        { name: 'facility_type', label: 'Type', type: 'select', options: [{ value: 'HOSPITAL', label: 'Hospital' }, { value: 'CLINIC', label: 'Clinic' }] },
        { name: 'address', label: 'Address', required: true },
        { name: 'city', label: 'City', required: true },
        { name: 'phone', label: 'Phone' },
        { name: 'email', label: 'Email' },
        { name: 'website', label: 'Website' },
        { name: 'description', label: 'Description', type: 'textarea' },
      ],
    },
    specialties: {
      label: 'Specialties',
      rows: specialties.data?.map((s) => ({ id: s.id, is_active: s.is_active, title: s.name, subtitle: s.description ?? '', record: { ...s } })),
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
        record: { ...d },
      })),
      fields: [
        {
          name: 'hospital_id',
          label: 'Hospital',
          type: 'select',
          required: true,
          createOnly: true,
          options: hospitals.data?.map((h) => ({ value: h.id, label: h.name })),
        },
        { name: 'specialty_id', label: 'Specialty', type: 'select', required: true, options: specialtyOptions, get: (r) => (r.specialty as Specialty).id },
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
        subtitle: `${d.hospital.name} · ${d.department.name} · ${d.specialty.name} · ${formatMoney(d.consultation_fee)} · ERP ${d.erp_doctor_id ?? 'not linked'}`,
        record: { ...d },
      })),
      fields: [
        {
          name: 'department_id',
          label: 'Department',
          type: 'select',
          required: true,
          options: departments.data?.map((d) => ({
            value: d.id,
            label: `${d.name} · ${d.specialty.name} (${hospitalName.get(d.hospital_id) ?? d.hospital_id})${d.is_active ? '' : ' — inactive'}`,
          })),
          get: (r) => (r.department as DoctorDetail['department']).id,
        },
        { name: 'full_name', label: 'Full name', required: true },
        { name: 'title', label: 'Title' },
        { name: 'experience_years', label: 'Years of experience', type: 'number' },
        { name: 'consultation_fee', label: 'Consultation fee', type: 'number' },
        { name: 'erp_doctor_id', label: 'ERP doctor ID' },
        { name: 'avatar_url', label: 'Photo URL' },
        { name: 'qualifications', label: 'Qualifications', type: 'textarea' },
        { name: 'introduction', label: 'Introduction', type: 'textarea' },
      ],
    },
    'appointment-types': {
      label: 'Appointment types',
      rows: types.data?.map((t) => ({
        id: t.id,
        is_active: t.is_active,
        title: t.name,
        subtitle: `${t.duration_minutes} min + ${t.buffer_minutes} min buffer · ${
          t.doctor_id ? `doctor #${t.doctor_id}` : t.specialty_id ? `specialty #${t.specialty_id}` : 'all doctors'
        }${t.fee_override ? ` · ${formatMoney(t.fee_override)}` : ''}`,
        record: { ...t },
      })),
      fields: [
        { name: 'name', label: 'Name', required: true },
        { name: 'duration_minutes', label: 'Duration (min)', type: 'number', required: true },
        { name: 'buffer_minutes', label: 'Buffer (min)', type: 'number' },
        { name: 'fee_override', label: 'Fee override', type: 'number' },
        { name: 'specialty_id', label: 'Limit to specialty', type: 'select', options: specialtyOptions },
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
          <FilterChip key={key} pressed={key === entity} onClick={() => selectEntity(key)}>
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
                <div className="flex shrink-0 gap-2">
                  <button
                    className="btn-secondary btn-sm"
                    aria-label={`Edit ${row.title}`}
                    onClick={() => {
                      update.reset()
                      setEditing(row)
                    }}
                  >
                    Edit
                  </button>
                  <button className="btn-secondary btn-sm" onClick={() => toggle.mutate(row)}>
                    {row.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="min-w-0 lg:col-span-2">
          <h2 className="section-title mb-4">{editing ? `Edit ${editing.title}` : 'Add new'}</h2>
          {editing ? (
            <EntityForm
              key={`${entity}-${editing.id}`}
              fields={current.fields}
              editing={editing.record}
              onSubmit={(body) => update.mutateAsync({ id: editing.id, body })}
              onCancel={() => setEditing(null)}
              busy={update.isPending}
            />
          ) : (
            <EntityForm key={entity} fields={current.fields} onSubmit={(body) => create.mutateAsync(body)} busy={create.isPending} />
          )}
          <div className="mt-3">
            <ErrorAlert error={editing ? update.error : create.error} />
          </div>
        </Card>
      </div>
    </div>
  )
}
