import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api/endpoints'
import type { AdminSymptom } from '../../api/types'
import { EmptyState, ErrorAlert, Field, Notice, Spinner } from '../../components/ui'
import { AdminNav } from './AdminNav'

/** SCRUM-43: symptom catalog, synonyms (used by the AI search), warning signs and rules. */
export default function AdminSymptomsPage() {
  const queryClient = useQueryClient()
  const symptoms = useQuery({ queryKey: ['admin', 'symptoms'], queryFn: api.admin.symptoms })
  const specialties = useQuery({ queryKey: ['specialties'], queryFn: api.directory.specialties })
  const [filter, setFilter] = useState('')
  const [newName, setNewName] = useState('')
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['admin', 'symptoms'] })
  const create = useMutation({
    mutationFn: (name: string) => api.admin.createSymptom({ name }),
    onSuccess: () => {
      setNewName('')
      refresh()
    },
  })

  const shown = (symptoms.data ?? []).filter((s) =>
    `${s.name} ${s.keywords ?? ''}`.toLowerCase().includes(filter.trim().toLowerCase()),
  )

  return (
    <div>
      <h1 className="page-title mb-6">Administration</h1>
      <AdminNav />
      <Notice tone="info" className="mb-6">
        Rules decide which specialties are suggested; synonyms (any language, comma-separated) help the AI search
        recognise how patients describe a symptom. Changes apply to the next search within a minute. Rules and warning
        signs must be reviewed by a clinician.
      </Notice>
      <div className="mb-6 flex flex-wrap items-end gap-4">
        <Field label="Filter">
          <input className="input" value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="name or synonym" />
        </Field>
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault()
            if (newName.trim().length >= 2) create.mutate(newName.trim())
          }}
        >
          <Field label="New symptom">
            <input className="input" value={newName} onChange={(e) => setNewName(e.target.value)} maxLength={100} />
          </Field>
          <button className="btn-primary" disabled={create.isPending || newName.trim().length < 2}>
            Add
          </button>
        </form>
      </div>
      <ErrorAlert error={symptoms.error ?? create.error} />
      {symptoms.isLoading && <Spinner />}
      {symptoms.data && shown.length === 0 && <EmptyState>No symptoms match.</EmptyState>}
      <ul className="space-y-4">
        {shown.map((s) => (
          <SymptomCard key={s.id} symptom={s} specialties={specialties.data ?? []} onSaved={refresh} />
        ))}
      </ul>
    </div>
  )
}

function SymptomCard({
  symptom: s,
  specialties,
  onSaved,
}: {
  symptom: AdminSymptom
  specialties: { id: number; name: string }[]
  onSaved: () => void
}) {
  const [keywords, setKeywords] = useState(s.keywords ?? '')
  const [redFlag, setRedFlag] = useState(s.is_red_flag)
  const [message, setMessage] = useState(s.red_flag_message ?? '')
  const [specialtyId, setSpecialtyId] = useState<number | ''>('')
  const [weight, setWeight] = useState('1')
  const dirty = keywords !== (s.keywords ?? '') || redFlag !== s.is_red_flag || message !== (s.red_flag_message ?? '')

  const save = useMutation({
    mutationFn: (body: Parameters<typeof api.admin.updateSymptom>[1]) => api.admin.updateSymptom(s.id, body),
    onSuccess: onSaved,
  })
  const addRule = useMutation({
    mutationFn: () => api.admin.createSymptomRule(s.id, { specialty_id: Number(specialtyId), weight: Number(weight) }),
    onSuccess: () => {
      setSpecialtyId('')
      onSaved()
    },
  })
  const updateRule = useMutation({
    mutationFn: ({ id, body }: { id: number; body: { weight?: number; is_active?: boolean } }) =>
      api.admin.updateSymptomRule(id, body),
    onSuccess: onSaved,
  })
  const mapped = new Set(s.rules.map((r) => r.specialty_id))

  return (
    <li className={`card space-y-4 ${s.is_active ? '' : 'opacity-70'}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-h2 font-semibold">
          {s.name}
          {s.is_red_flag && <span className="ml-2 text-sm font-bold text-alert">warning sign</span>}
          {!s.is_active && <span className="caption ml-2">(inactive)</span>}
        </h2>
        <button className="btn-secondary btn-sm" disabled={save.isPending} onClick={() => save.mutate({ is_active: !s.is_active })}>
          {s.is_active ? 'Deactivate' : 'Activate'}
        </button>
      </div>
      <Field label="Synonyms (comma-separated, any language)">
        <textarea className="input" rows={2} maxLength={500} value={keywords} onChange={(e) => setKeywords(e.target.value)} />
      </Field>
      <div className="flex flex-wrap items-end gap-4">
        <label className="flex min-h-12 items-center gap-2">
          <input type="checkbox" checked={redFlag} onChange={(e) => setRedFlag(e.target.checked)} />
          Warning sign (urgent care)
        </label>
        {redFlag && (
          <div className="min-w-64 flex-1">
            <Field label="Warning message">
              <input className="input" maxLength={500} value={message} onChange={(e) => setMessage(e.target.value)} />
            </Field>
          </div>
        )}
        <button
          className="btn-primary btn-sm"
          disabled={!dirty || save.isPending}
          onClick={() => save.mutate({ keywords: keywords.trim() || null, is_red_flag: redFlag, red_flag_message: redFlag ? message.trim() : null })}
        >
          Save
        </button>
      </div>
      <ErrorAlert error={save.error ?? addRule.error ?? updateRule.error} />

      <div>
        <p className="label mb-2">Specialty rules</p>
        {s.rules.length === 0 && <p className="caption">No rules — this symptom suggests no specialty.</p>}
        <ul className="divide-y divide-line rounded-lg border border-line">
          {s.rules.map((r) => (
            <li key={r.id} className={`flex flex-wrap items-center justify-between gap-3 p-3 ${r.is_active ? '' : 'text-muted line-through'}`}>
              <span>{r.specialty_name}</span>
              <span className="flex items-center gap-3">
                <label className="caption flex items-center gap-1">
                  weight
                  <input
                    className="input w-20"
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="5"
                    defaultValue={r.weight}
                    onBlur={(e) => {
                      const w = Number(e.target.value)
                      if (w > 0 && w <= 5 && w !== r.weight) updateRule.mutate({ id: r.id, body: { weight: w } })
                    }}
                  />
                </label>
                <button className="btn-secondary btn-sm" onClick={() => updateRule.mutate({ id: r.id, body: { is_active: !r.is_active } })}>
                  {r.is_active ? 'Disable' : 'Enable'}
                </button>
              </span>
            </li>
          ))}
        </ul>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <select className="input w-auto" value={specialtyId} onChange={(e) => setSpecialtyId(e.target.value ? Number(e.target.value) : '')} aria-label="Specialty">
            <option value="">Add a specialty…</option>
            {specialties
              .filter((sp) => !mapped.has(sp.id))
              .map((sp) => (
                <option key={sp.id} value={sp.id}>
                  {sp.name}
                </option>
              ))}
          </select>
          <input className="input w-20" type="number" step="0.1" min="0.1" max="5" value={weight} onChange={(e) => setWeight(e.target.value)} aria-label="Weight" />
          <button className="btn-secondary btn-sm" disabled={!specialtyId || addRule.isPending} onClick={() => addRule.mutate()}>
            Add rule
          </button>
        </div>
      </div>
    </li>
  )
}
