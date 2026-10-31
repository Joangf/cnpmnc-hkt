import { useMutation, useQuery } from '@tanstack/react-query'
import { useId, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/endpoints'
import { EMERGENCY_NUMBER, ErrorAlert, Field, FilterChip, Notice, Spinner } from '../components/ui'

const DISCLAIMER =
  'This tool helps you choose which kind of doctor to see. It does not diagnose conditions and is not a substitute for professional medical advice.'

export default function SymptomCheckerPage() {
  const symptoms = useQuery({ queryKey: ['symptoms'], queryFn: api.symptoms.list })
  const [selected, setSelected] = useState<number[]>([])
  const [freeText, setFreeText] = useState('')
  const recommend = useMutation({ mutationFn: api.symptoms.recommend })
  const labelId = useId()

  const toggle = (id: number) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))
  const result = recommend.data

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div className="space-y-5">
        <h1 className="page-title">Symptom checker</h1>
        {/* FR-REC-05 / BR-10 */}
        <Notice tone="info">{DISCLAIMER}</Notice>
      </div>

      <section className="card space-y-6">
        <div>
          <p id={labelId} className="label">
            Select your symptoms
          </p>
          {symptoms.isLoading && <Spinner />}
          <div role="group" aria-labelledby={labelId} className="mt-3 flex flex-wrap gap-3">
            {symptoms.data?.map((s) => (
              <FilterChip key={s.id} pressed={selected.includes(s.id)} onClick={() => toggle(s.id)}>
                {s.name}
              </FilterChip>
            ))}
          </div>
        </div>
        <Field label="Or describe them in your own words (optional)">
          <textarea className="input" rows={2} maxLength={500} value={freeText} onChange={(e) => setFreeText(e.target.value)} placeholder="e.g. itchy rash on my arms" />
        </Field>
        <ErrorAlert error={recommend.error} />
        <button
          className="btn-primary w-full sm:w-auto"
          disabled={recommend.isPending || (!selected.length && !freeText.trim())}
          onClick={() => recommend.mutate({ symptom_ids: selected, free_text: freeText.trim() || undefined })}
        >
          {recommend.isPending ? 'Checking…' : 'Suggest specialties'}
        </button>
      </section>

      {result && (
        <div className="space-y-8">
          {/* FR-REC-06 */}
          {result.urgent_warning && (
            <Notice tone="danger" title="Seek urgent medical care">
              <p>{result.urgent_warning}</p>
              <a href={`tel:${EMERGENCY_NUMBER}`} className="btn-danger btn-sm mt-3">
                Call {EMERGENCY_NUMBER}
              </a>
            </Notice>
          )}

          <section>
            <h2 className="section-title mb-4">Suggested specialties</h2>
            {result.specialties.length === 0 ? (
              <p className="card">
                We couldn't match these symptoms. A{' '}
                <Link className="link" to="/doctors">
                  General Internal Medicine
                </Link>{' '}
                doctor is a good place to start.
              </p>
            ) : (
              <ol className="space-y-3">
                {result.specialties.map((s, i) => (
                  <li key={s.specialty_id} className={`card flex flex-wrap items-center justify-between gap-4 ${i === 0 ? 'border-berry bg-blush' : ''}`}>
                    <div>
                      <span className="text-h2 font-semibold">
                        {i + 1}. {s.name}
                      </span>
                      <span className="caption mt-1 block">Based on: {s.matched_symptoms.join(', ')}</span>
                    </div>
                    <Link className={`${i === 0 ? 'btn-primary' : 'btn-secondary'} btn-sm`} to={`/doctors?specialty_id=${s.specialty_id}`}>
                      See doctors
                    </Link>
                  </li>
                ))}
              </ol>
            )}
          </section>

          {result.departments.length > 0 && (
            <section>
              <h2 className="section-title mb-4">Where you can go</h2>
              <ul className="card divide-y divide-line p-0 sm:p-0">
                {result.departments.map((d) => (
                  <li key={d.department_id} className="flex flex-wrap items-center justify-between gap-3 p-4 sm:px-6">
                    <div>
                      <div className="font-semibold">{d.department_name}</div>
                      <div className="caption">
                        {d.hospital_name} · {d.city}
                      </div>
                    </div>
                    <Link className="btn-secondary btn-sm" to={`/doctors?department_id=${d.department_id}`} aria-label={`Book: ${d.department_name}, ${d.hospital_name}`}>
                      Book
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}
          <p className="caption">{result.disclaimer}</p>
        </div>
      )}
    </div>
  )
}
