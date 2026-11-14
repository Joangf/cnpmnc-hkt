import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/endpoints'
import type { DoctorRecommendation, InterpretedSymptom, Recommendation } from '../api/types'
import { IconAlert, IconArrowRight, IconX } from '../components/icons'
import { EMERGENCY_NUMBER, ErrorAlert, Field, FilterChip, Notice, Spinner, Stars } from '../components/ui'

// Plain-language steps (design board 03: one task per step, progress shown).
const HOW_IT_WORKS = [
  { title: 'Describe how you feel', text: 'Optionally describe your symptoms in English or Vietnamese, then choose “Find my symptoms”. You can also go straight to the symptom list.' },
  { title: 'Review or select symptoms', text: 'Remove any incorrect matches or add symptoms from the list. It starts with all symptoms; filter by department or search to narrow it down. Your picks stay when you switch departments.' },
  { title: 'Get suggestions and choose a doctor', text: 'Choose “Suggest specialties and doctors” to see your results. If symptoms are flagged as severe, read the urgent alert first. Then explore the suggested specialties and doctors.' },
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

type Chip = { id: number; name: string; detail?: InterpretedSymptom }

export default function SymptomCheckerPage() {
  const [activeStep, setActiveStep] = useState<1 | 2 | 3>(1)
  const [text, setText] = useState('')
  const [chips, setChips] = useState<Chip[]>([])
  const [showCatalog, setShowCatalog] = useState(false)
  const [departmentId, setDepartmentId] = useState('all')
  const [symptomSearch, setSymptomSearch] = useState('')
  const departments = useQuery({
    queryKey: ['symptom-picker-departments'],
    enabled: showCatalog,
    queryFn: async () => {
      const first = await api.directory.departments({ page: 1, page_size: 100 })
      const items = [...first.items]
      for (let page = 2; items.length < first.total; page++) {
        const next = await api.directory.departments({ page, page_size: 100 })
        items.push(...next.items)
        if (next.items.length === 0) break
      }
      return items
    },
  })
  const symptoms = useQuery({
    queryKey: ['symptoms', departmentId],
    queryFn: () => api.symptoms.list(departmentId === 'all' ? undefined : Number(departmentId)),
    enabled: showCatalog && departmentId !== '',
  })
  const visibleSymptoms = symptoms.data?.filter((symptom) =>
    symptom.name.toLocaleLowerCase().includes(symptomSearch.trim().toLocaleLowerCase()),
  )

  const resultsRef = useRef<HTMLDivElement>(null)
  const [severeWarning, setSevereWarning] = useState<string | null>(null)
  const [interpretedText, setInterpretedText] = useState<string | null>(null)
  const interpret = useMutation({
    mutationFn: api.symptoms.interpret,
    onSuccess: (data, sentText) => {
      setActiveStep(2)
      setSevereWarning(data.urgent_warning)
      setInterpretedText(sentText)
      // Detected symptoms replace earlier detections; symptoms picked by hand stay.
      setChips((prev) => {
        const manual = prev.filter((c) => !c.detail)
        const found = data.symptoms.map((s) => ({ id: s.id, name: s.name, detail: s }))
        return [...found, ...manual.filter((m) => !found.some((f) => f.id === m.id))]
      })
      recommend.reset()
    },
  })
  const recommend = useMutation({
    mutationFn: api.symptoms.recommend,
    onMutate: () => setActiveStep(3),
    onError: () => setActiveStep(2),
    onSuccess: (data) => {
      setActiveStep(3)
      setSevereWarning(data.urgent_warning)
    },
  })
  const labelId = useId()

  const selectedIds = chips.map((c) => c.id)
  const remove = (id: number) => {
    setChips((c) => c.filter((x) => x.id !== id))
    recommend.reset()
  }
  const toggleCatalog = (id: number, name: string) => {
    setChips((c) => (c.some((x) => x.id === id) ? c.filter((x) => x.id !== id) : [...c, { id, name }]))
    recommend.reset()
  }
  const result = recommend.data
  const urgent = result?.urgent_warning ?? interpret.data?.urgent_warning ?? null

  useEffect(() => {
    // Let the urgent alert take priority; reveal suggestions once it is dismissed.
    if (!result || severeWarning) return
    const results = resultsRef.current
    results?.focus({ preventScroll: true })
    results?.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
      block: 'start',
    })
  }, [result, severeWarning])

  return (
    <div className="space-y-8">
      {severeWarning && <SevereSymptomAlert message={severeWarning} onDismiss={() => setSevereWarning(null)} />}
      <div className="space-y-5">
        <h1 className="page-title">Symptom checker</h1>
        {/* FR-REC-05 / BR-10 */}
        <Notice tone="info">{DISCLAIMER}</Notice>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="min-w-0 space-y-8 lg:col-span-2">
          <section className="card space-y-6">
            <Field label="1. Describe how you feel" hint="Optional — e.g. “dạo này tôi hay tức ngực, khó thở” or “itchy rash on my arms”. You can also select symptoms from the list below.">
              <textarea
                className="input"
                rows={3}
                maxLength={500}
                value={text}
                onFocus={() => setActiveStep(1)}
                onChange={(e) => { setActiveStep(1); setText(e.target.value) }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && text.trim().length >= 2) interpret.mutate(text.trim())
                }}
              />
            </Field>
            <ErrorAlert error={interpret.error} />
            <button
              className="btn-secondary w-full sm:w-auto"
              disabled={interpret.isPending || text.trim().length < 2}
              onClick={() => interpret.mutate(text.trim())}
            >
              {interpret.isPending ? 'Reading your description…' : 'Find my symptoms'}
            </button>

            {interpret.data && interpret.data.symptoms.length === 0 && (
              <Notice tone="warning" title="We couldn't recognise a symptom">
                <p>
                  Try other words, pick symptoms from the list below, or{' '}
                  <Link className="link" to="/doctors">
                    browse all doctors
                  </Link>{' '}
                  directly.
                </p>
              </Notice>
            )}
            {interpret.data?.mode === 'rule_fallback' && (
              <p className="caption">AI search is unavailable right now, so we matched your words exactly.</p>
            )}

            <div onFocusCapture={() => setActiveStep(2)} onClickCapture={() => setActiveStep(2)}>
              <div className="flex min-h-12 flex-wrap items-center justify-between gap-x-2">
                <p id={labelId} className="label">
                  2. Review or select symptoms
                </p>
                {chips.length > 0 && (
                  <p className="caption flex items-center" aria-live="polite">
                    {chips.length} selected ·{' '}
                    <button
                      type="button"
                      className="link inline-flex min-h-12 items-center px-1"
                      onClick={() => {
                        setChips([])
                        recommend.reset()
                      }}
                    >
                      Clear
                    </button>
                  </p>
                )}
              </div>
              {chips.length === 0 ? (
                <p className="caption">Nothing yet — describe how you feel above, or pick from the list.</p>
              ) : (
                <ul role="group" aria-labelledby={labelId} className="mt-2 flex flex-wrap gap-3">
                  {chips.map((c) => (
                    <li key={c.id} className="chip" aria-pressed="true">
                      <span>
                        {c.name}
                        {c.detail?.matched_phrase && (
                          <span className="caption ml-1">
                            (“{c.detail.matched_phrase}”{c.detail.via === 'rephrase' ? ', via AI rephrasing' : ''})
                          </span>
                        )}
                      </span>
                      <button type="button" className="ml-1 inline-flex" aria-label={`Remove ${c.name}`} onClick={() => remove(c.id)}>
                        <IconX size={16} />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <button type="button" className="link mt-3 inline-flex min-h-12 items-center" aria-expanded={showCatalog} aria-controls="symptom-catalog" onClick={() => setShowCatalog((v) => !v)}>
                {showCatalog ? 'Hide the symptom list' : 'Add from the symptom list'}
              </button>
              {showCatalog && (
                <div id="symptom-catalog" className="mt-2 space-y-4">
                  <Field label="Choose a department" hint="Pick symptoms from one or more departments. Your selections stay when you switch.">
                    <select
                      className="input"
                      value={departmentId}
                      onChange={(event) => {
                        setDepartmentId(event.target.value)
                        setSymptomSearch('')
                      }}
                    >
                      <option value="all">All symptoms</option>
                      {departments.data?.map((department) => (
                        <option key={department.id} value={department.id}>
                          {department.name} · {department.hospital.name}
                        </option>
                      ))}
                    </select>
                  </Field>
                  {departments.isLoading && <Spinner />}
                  <ErrorAlert error={departments.error} />
                  {departments.isError && (
                    <button type="button" className="link" onClick={() => departments.refetch()}>Retry loading departments</button>
                  )}
                  {departmentId && (
                    <>
                      <Field label="Search symptoms">
                        <input className="input" type="search" value={symptomSearch} onChange={(event) => setSymptomSearch(event.target.value)} />
                      </Field>
                      {symptoms.isLoading && <Spinner />}
                      <ErrorAlert error={symptoms.error} />
                      {symptoms.isError && (
                        <button type="button" className="link" onClick={() => symptoms.refetch()}>Retry loading symptoms</button>
                      )}
                      {symptoms.isSuccess && (
                        <>
                          <p className="caption" role="status">
                            {visibleSymptoms?.length === 0
                              ? (symptomSearch.trim() ? 'No symptoms match your search.' : 'No symptoms are listed for this department yet. Try another department or browse all symptoms.')
                              : `${visibleSymptoms?.length} symptoms available`}
                          </p>
                          <div className="flex max-h-72 flex-wrap gap-3 overflow-y-auto p-1" role="group" aria-label="Available symptoms">
                            {visibleSymptoms?.map((symptom) => (
                              <FilterChip key={symptom.id} pressed={selectedIds.includes(symptom.id)} onClick={() => toggleCatalog(symptom.id, symptom.name)}>
                                {symptom.name}
                              </FilterChip>
                            ))}
                          </div>
                        </>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
            <ErrorAlert error={recommend.error} />
            {/* SCRUM-39: a description alone, selected symptoms alone, or both. */}
            <button
              className="btn-primary w-full sm:w-auto"
              disabled={recommend.isPending || interpret.isPending || (chips.length === 0 && !text.trim())}
              onClick={async () => {
                const description = text.trim()
                let ids = selectedIds
                if (description && description !== interpretedText) {
                  // Not read yet: find its symptoms first, then suggest from them and the picks.
                  let found: number[]
                  try {
                    found = (await interpret.mutateAsync(description)).symptoms.map((s) => s.id)
                  } catch {
                    return // shown by the error alert above
                  }
                  const picked = chips.filter((c) => !c.detail).map((c) => c.id)
                  ids = [...new Set([...found, ...picked])]
                }
                if (ids.length === 0) return // the "couldn't recognise" notice is showing
                recommend.mutate({ symptom_ids: ids, context_text: description || undefined, explain: true })
              }}
            >
              {recommend.isPending ? 'Finding specialties and doctors…' : '3. Suggest specialties and doctors'}
            </button>
          </section>

          {/* FR-REC-06: shown as soon as a warning sign is found, before any suggestion. */}
          {urgent && (
            <Notice tone="danger" title="Seek urgent medical care">
              <p>{urgent}</p>
              <a href={`tel:${EMERGENCY_NUMBER}`} className="btn-danger btn-sm mt-3">
                Call {EMERGENCY_NUMBER}
              </a>
            </Notice>
          )}

          {result && (
            <div ref={resultsRef} tabIndex={-1} role="region" aria-label="Suggested specialties and doctors" className="scroll-mt-40 rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-berry">
              <Results result={result} />
            </div>
          )}

        </div>

        <aside className="space-y-5 lg:sticky lg:top-6 lg:self-start" aria-label="About the symptom checker">
          <section className="card">
            <h2 className="section-title mb-5">How it works</h2>
            <ol className="space-y-5">
              {HOW_IT_WORKS.map((step, i) => (
                <li
                  key={step.title}
                  aria-current={activeStep === i + 1 ? 'step' : undefined}
                  className={`flex gap-4 rounded-lg p-3 ${activeStep === i + 1 ? 'bg-blush' : ''}`}
                >
                  <span
                    aria-hidden="true"
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full font-bold ${
                      activeStep === i + 1 ? 'bg-berry text-on-accent' : 'bg-blush text-berry'
                    }`}
                  >
                    {i + 1}
                  </span>
                  <div>
                    <p className={`font-semibold ${activeStep === i + 1 ? 'text-berry' : ''}`}>{step.title}</p>
                    {activeStep === i + 1 && <span className="caption font-semibold text-berry">Current step</span>}
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
              <Link to="/departments" className="link inline-flex min-h-12 items-center gap-2">
                Departments <IconArrowRight size={18} />
              </Link>
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}

function SevereSymptomAlert({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const dismissRef = useRef<HTMLButtonElement>(null)
  const titleId = useId()
  const messageId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    const previousOverflow = document.body.style.overflow
    dialog?.showModal()
    dismissRef.current?.focus()
    document.body.style.overflow = 'hidden'
    return () => {
      dialog?.close()
      document.body.style.overflow = previousOverflow
    }
  }, [])

  return (
    <dialog
      ref={dialogRef}
      role="alertdialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={messageId}
      onCancel={(event) => { event.preventDefault(); onDismiss() }}
      className="m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-lg overflow-y-auto rounded-lg border border-alert-line bg-surface p-6 text-ink shadow-card backdrop:bg-ink/50"
    >
      <h2 id={titleId} className="section-title flex items-center gap-2 text-alert-strong">
        <IconAlert size={24} /> Seek urgent medical care
      </h2>
      <p id={messageId} className="mt-4">{message}</p>
      <div className="mt-6 flex flex-wrap gap-3">
        <a href={`tel:${EMERGENCY_NUMBER}`} className="btn-danger">Call {EMERGENCY_NUMBER}</a>
        <button type="button" ref={dismissRef} className="btn-secondary" onClick={onDismiss}>I understand</button>
      </div>
    </dialog>
  )
}

function Results({ result }: { result: Recommendation }) {
  const reasons = new Map(result.specialty_explanations.map((e) => [e.specialty_id, e.reason]))
  const doctorsBySpecialty = new Map<number, DoctorRecommendation[]>()
  for (const d of result.doctors) doctorsBySpecialty.set(d.specialty_id, [...(doctorsBySpecialty.get(d.specialty_id) ?? []), d])

  return (
    <div className="reveal space-y-8">
      <section>
        <h2 className="section-title mb-2">Suggested specialties</h2>
        {result.explanation && <p className="mb-4">{result.explanation}</p>}
        {result.specialties.length === 0 ? (
          <p className="card">
            We couldn't match these symptoms to a specialty. A{' '}
            <Link className="link" to="/doctors">
              General Internal Medicine
            </Link>{' '}
            doctor is a good place to start, or{' '}
            <Link className="link" to="/doctors">
              browse all doctors
            </Link>
            .
          </p>
        ) : (
          <ol className="space-y-4">
            {result.specialties.map((s, i) => (
              <li key={s.specialty_id} className={`card space-y-4 ${i === 0 ? 'border-berry bg-blush' : ''}`}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <span className="text-h2 font-semibold">
                      {i + 1}. {s.name}
                    </span>
                    <span className="caption mt-1 block">Based on: {s.matched_symptoms.join(', ')}</span>
                    {reasons.get(s.specialty_id) && <p className="mt-2">{reasons.get(s.specialty_id)}</p>}
                  </div>
                  <Link className="btn-secondary btn-sm" to={`/doctors?specialty_id=${s.specialty_id}`}>
                    All doctors
                  </Link>
                </div>
                {(doctorsBySpecialty.get(s.specialty_id) ?? []).length > 0 ? (
                  <ul className="divide-y divide-line rounded-lg border border-line bg-surface">
                    {doctorsBySpecialty.get(s.specialty_id)!.map((d) => (
                      <DoctorRow key={d.doctor_id} doctor={d} />
                    ))}
                  </ul>
                ) : (
                  <p className="caption">
                    No doctor of this specialty is taking bookings online right now.{' '}
                    <Link className="link" to="/hospitals">
                      Browse other facilities
                    </Link>
                    .
                  </p>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>

      <p className="caption">{result.disclaimer}</p>
    </div>
  )
}

function DoctorRow({ doctor: d }: { doctor: DoctorRecommendation }) {
  const next = d.next_available
    ? new Date(d.next_available).toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
    : null
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 p-4">
      <div className="min-w-0">
        <div className="font-semibold">
          {d.full_name}
          {d.title && <span className="caption ml-2">{d.title}</span>}
        </div>
        <div className="caption">
          {/* SCRUM-42: the suggested department leads to its doctors */}
          <Link className="link" to={`/doctors?department_id=${d.department_id}`}>
            {d.department_name}
          </Link>{' '}
          · {d.hospital_name}
        </div>
        <div className="caption mt-1 flex flex-wrap items-center gap-x-3">
          {d.rating_count > 0 ? (
            <span className="inline-flex items-center gap-1">
              <Stars value={d.rating_avg} /> {d.rating_avg.toFixed(1)} ({d.rating_count})
            </span>
          ) : (
            <span>No reviews yet</span>
          )}
          <span>{next ? `Next free: ${next}` : 'No free slot in the next 2 weeks'}</span>
        </div>
      </div>
      <Link className="btn-primary btn-sm" to={`/doctors/${d.doctor_id}`} aria-label={`Book ${d.full_name}`}>
        Book
      </Link>
    </li>
  )
}
