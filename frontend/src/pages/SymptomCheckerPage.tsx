import { useMutation, useQuery } from '@tanstack/react-query'
import { useId, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/endpoints'
import { IconAlert, IconArrowRight } from '../components/icons'
import { EMERGENCY_NUMBER, ErrorAlert, Field, FilterChip, Notice, Spinner } from '../components/ui'

// Plain-language steps (design board 03: one task per step, progress shown).
const HOW_IT_WORKS = [
  { title: 'Tell us how you feel', text: 'Pick the symptoms that fit, or describe them in your own words.' },
  { title: 'See which specialty fits', text: 'We suggest the kinds of doctor who usually help, most likely first.' },
  { title: 'Book a doctor', text: 'Choose a doctor and a time that suits you. You can browse without an account.' },
]

// Mirrors the warning signs the checker flags as urgent (FR-REC-06), shown before anyone types.
const WARNING_SIGNS = [
  'Chest pain or pressure',
  'Trouble breathing',
  'Sudden weakness or numbness on one side',
  'Sudden loss of vision',
]

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
    <div className="space-y-8">
      <div className="space-y-5">
        <h1 className="page-title">Symptom checker</h1>
        {/* FR-REC-05 / BR-10 */}
        <Notice tone="info">{DISCLAIMER}</Notice>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="min-w-0 space-y-8 lg:col-span-2">
          <section className="card space-y-6">
            <div>
              <div className="flex min-h-12 flex-wrap items-center justify-between gap-x-2">
                <p id={labelId} className="label">
                  Select your symptoms
                </p>
                {selected.length > 0 && (
                  <p className="caption flex items-center" aria-live="polite">
                    {selected.length} selected ·{' '}
                    <button type="button" className="link inline-flex min-h-12 items-center px-1" onClick={() => setSelected([])}>
                      Clear
                    </button>
                  </p>
                )}
              </div>
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
            <div className="reveal space-y-8">
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

        <aside className="space-y-5 lg:sticky lg:top-6 lg:self-start" aria-label="About the symptom checker">
          <section className="card">
            <h2 className="section-title mb-5">How it works</h2>
            <ol className="space-y-5">
              {HOW_IT_WORKS.map((step, i) => (
                <li key={step.title} className="flex gap-4">
                  <span
                    aria-hidden="true"
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full font-bold ${
                      i === 0 ? 'bg-berry text-on-accent' : 'bg-blush text-berry'
                    }`}
                  >
                    {i + 1}
                  </span>
                  <div>
                    <p className="font-semibold">{step.title}</p>
                    <p className="caption mt-1">{step.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <section className="rounded-lg border border-alert-line bg-alert-soft p-5 text-alert-strong shadow-card sm:p-6">
            <h2 className="flex items-center gap-2 text-h2 font-semibold">
              <IconAlert size={22} className="text-alert" />
              Don't wait if you have
            </h2>
            <ul className="mt-3 list-disc space-y-1.5 pl-5 text-base">
              {WARNING_SIGNS.map((sign) => (
                <li key={sign}>{sign}</li>
              ))}
            </ul>
            <a href={`tel:${EMERGENCY_NUMBER}`} className="btn-danger btn-sm mt-5 w-full">
              Call {EMERGENCY_NUMBER} now
            </a>
          </section>

          <section className="card">
            <h2 className="section-title">Know what you need?</h2>
            <p className="caption mt-1">Skip the checker and look directly.</p>
            <div className="mt-4 flex flex-col gap-1">
              <Link to="/doctors" className="link inline-flex min-h-12 items-center gap-2">
                Doctors <IconArrowRight size={18} />
              </Link>
              <Link to="/hospitals" className="link inline-flex min-h-12 items-center gap-2">
                Hospitals &amp; clinics <IconArrowRight size={18} />
              </Link>
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}
