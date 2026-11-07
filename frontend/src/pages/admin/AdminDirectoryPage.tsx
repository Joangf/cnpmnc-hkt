import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { api, type AdminEntity } from '../../api/endpoints'
import type { AppointmentTypeAdmin, Department, DepartmentVisibility, DoctorDetail, HospitalDetail, Specialty } from '../../api/types'
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

type Row = { id: number; is_active: boolean; title: string; subtitle: string; visibility?: DepartmentVisibility }

function EntityForm({ fields, onSubmit, busy }: { fields: FieldDef[]; onSubmit: (body: Record<string, unknown>) => void; busy: boolean }) {
  const handle = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const data = new FormData(e.currentTarget)
    const body: Record<string, unknown> = {}
    for (const f of fields) {
      const raw = String(data.get(f.name) ?? '').trim()
      if (raw === '') continue
      body[f.name] = f.type === 'number' || (f.type === 'select' && /^\d+$/.test(raw)) ? Number(raw) : raw
    }
    onSubmit(body)
    e.currentTarget.reset()
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
            <textarea name={f.name} className="input" rows={2} required={f.required} />
          ) : f.type === 'select' ? (
            <select name={f.name} className="input" required={f.required} defaultValue="">
              <option value="">—</option>
              {f.options?.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          ) : (
            <input name={f.name} className="input" type={f.type ?? 'text'} required={f.required} min={f.type === 'number' ? 0 : undefined} />
          )}
        </label>
      ))}
      <div className="sm:col-span-2">
        <button className="btn-primary" disabled={busy}>
          Create
        </button>
      </div>
    </form>
  )
}

export default function AdminDirectoryPage() {
  const queryClient = useQueryClient()
  const [entity, setEntity] = useState<AdminEntity>('hospitals')

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
  const toggle = useMutation({
    mutationFn: (row: Row) => api.admin.update(entity, row.id, { is_active: !row.is_active }),
    onSuccess: invalidate,
  })
  const setVisibility = useMutation({
    mutationFn: ({ id, visibility }: { id: number; visibility: DepartmentVisibility }) =>
      api.admin.update('departments', id, { visibility }),
    onSuccess: invalidate,
  })

  const hospitalName = new Map(hospitals.data?.map((h) => [h.id, h.name] as const))
  const specialtyOptions = specialties.data?.map((s) => ({ value: s.id, label: s.name })) ?? []

  const config: Record<AdminEntity, { label: string; rows: Row[] | undefined; fields: FieldDef[] }> = {
    hospitals: {
      label: 'Hospitals & clinics',
      rows: hospitals.data?.map((h) => ({ id: h.id, is_active: h.is_active, title: h.name, subtitle: `${h.address}, ${h.city}` })),
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
      rows: specialties.data?.map((s) => ({ id: s.id, is_active: s.is_active, title: s.name, subtitle: s.description ?? '' })),
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
        subtitle: `${hospitalName.get(d.hospital_id) ?? `Hospital #${d.hospital_id}`} · ${d.specialty.name} · ${d.location ?? 'No location'}`,
        visibility: d.visibility ?? 'PUBLIC',
      })),
      fields: [
        { name: 'hospital_id', label: 'Hospital', type: 'select', required: true, options: hospitals.data?.map((h) => ({ value: h.id, label: h.name })) },
        { name: 'specialty_id', label: 'Specialty', type: 'select', required: true, options: specialtyOptions },
        { name: 'name', label: 'Name', required: true },
        { name: 'location', label: 'Location / floor' },
        {
          name: 'visibility',
          label: 'Visibility',
          type: 'select',
          options: [
            { value: 'PUBLIC', label: 'Public (published)' },
            { value: 'UNPUBLISHED', label: 'Unpublished' },
            { value: 'HIDDEN', label: 'Hidden' },
          ],
        },
        { name: 'description', label: 'Description', type: 'textarea' },
      ],
    },
    doctors: {
      label: 'Doctors',
      rows: doctors.data?.map((d) => ({
        id: d.id,
        is_active: d.is_active,
        title: d.full_name,
        subtitle: `${d.hospital.name} · ${d.department.name} · ${formatMoney(d.consultation_fee)} · ERP ${d.erp_doctor_id ?? 'not linked'}`,
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
        { name: 'consultation_fee', label: 'Consultation fee', type: 'number' },
        { name: 'erp_doctor_id', label: 'ERP doctor ID' },
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
          <FilterChip key={key} pressed={key === entity} onClick={() => setEntity(key)}>
            {config[key].label}
          </FilterChip>
        ))}
      </div>

      <div className="grid gap-8 lg:grid-cols-5">
        <Card className="min-w-0 lg:col-span-3">
          <h2 className="section-title mb-3">{current.label}</h2>
          {!current.rows && <Spinner />}
          <ErrorAlert error={toggle.error} />
          <ErrorAlert error={setVisibility.error} />
          <ul className="divide-y divide-line">
            {current.rows?.map((row) => (
              <li key={row.id} className="flex items-center justify-between gap-3 py-3">
                <div className={`min-w-0 ${row.is_active ? '' : 'text-muted'}`}>
                  <div className="flex flex-wrap items-center gap-2 font-semibold">
                    {row.title}
                    {!row.is_active && <span className="tag">Inactive</span>}
                  </div>
                  <div className="caption">{row.subtitle}</div>
                  {row.visibility && (
                    <label className="mt-2 flex max-w-[220px] items-center gap-2">
                      <span className="caption shrink-0">Visibility</span>
                      <select
                        className="input py-1"
                        value={row.visibility}
                        onChange={(e) =>
                          setVisibility.mutate({
                            id: row.id,
                            visibility: e.target.value as DepartmentVisibility,
                          })
                        }
                      >
                        <option value="PUBLIC">Public</option>
                        <option value="UNPUBLISHED">Unpublished</option>
                        <option value="HIDDEN">Hidden</option>
                      </select>
                    </label>
                  )}
                </div>
                <button className="btn-secondary btn-sm shrink-0" onClick={() => toggle.mutate(row)}>
                  {row.is_active ? 'Deactivate' : 'Activate'}
                </button>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="min-w-0 lg:col-span-2">
          <h2 className="section-title mb-4">Add new</h2>
          <EntityForm key={entity} fields={current.fields} onSubmit={(body) => create.mutate(body)} busy={create.isPending} />
          <div className="mt-3">
            <ErrorAlert error={create.error} />
          </div>
        </Card>
      </div>
    </div>
  )
}
