import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { api } from '../../api/endpoints'
import type { AdminDoctorDetail } from '../../api/types'
import { Card, ErrorAlert, Field, Notice, Spinner } from '../../components/ui'
import { CLINIC_TZ, formatDateTime, formatTime, upcomingDays } from '../../lib/format'
import { AdminNav } from './AdminNav'

function DoctorCombobox({
  doctors,
  selectedId,
  onSelect,
}: {
  doctors: AdminDoctorDetail[]
  selectedId: number
  onSelect: (id: number) => void
}) {
  const [open, setOpen] = useState(false)
  const selectedDoctor = doctors.find((d) => d.id === selectedId)
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (selectedDoctor) {
      setQuery(`${selectedDoctor.full_name} · ${selectedDoctor.specialty.name}`)
    } else {
      setQuery('')
    }
  }, [selectedId, selectedDoctor])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
        if (selectedDoctor) {
          setQuery(`${selectedDoctor.full_name} · ${selectedDoctor.specialty.name}`)
        } else {
          setQuery('')
        }
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [selectedDoctor])

  const filtered = doctors.filter((d) => {
    const q = query.trim().toLowerCase()
    if (!q) return true
    if (selectedDoctor && `${selectedDoctor.full_name} · ${selectedDoctor.specialty.name}`.toLowerCase() === q) {
      return true
    }
    return (
      d.full_name.toLowerCase().includes(q) ||
      d.specialty.name.toLowerCase().includes(q)
    )
  })

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      setOpen(false)
      if (selectedDoctor) {
        setQuery(`${selectedDoctor.full_name} · ${selectedDoctor.specialty.name}`)
      } else {
        setQuery('')
      }
    } else if (e.key === 'Enter') {
      if (open && filtered.length > 0) {
        e.preventDefault()
        const first = filtered[0]
        onSelect(first.id)
        setQuery(`${first.full_name} · ${first.specialty.name}`)
        setOpen(false)
        inputRef.current?.blur()
      }
    } else if (e.key === 'ArrowDown') {
      if (!open) {
        setOpen(true)
      }
    }
  }

  return (
    <div className="relative" ref={containerRef}>
      <div className="relative flex items-center mt-2">
        <input
          ref={inputRef}
          type="text"
          className="input mt-0 pr-10"
          placeholder="Search doctor or specialty..."
          value={query}
          onFocus={(e) => {
            setOpen(true)
            e.target.select()
          }}
          onClick={() => {
            if (!open) setOpen(true)
          }}
          onChange={(e) => {
            setQuery(e.target.value)
            if (!open) setOpen(true)
          }}
          onKeyDown={handleKeyDown}
          autoComplete="off"
        />
        <button
          type="button"
          tabIndex={-1}
          aria-label={open ? 'Close list' : 'Open list'}
          className="absolute right-0 top-0 bottom-0 flex items-center px-3 text-muted hover:text-ink"
          onClick={() => {
            if (open) {
              setOpen(false)
            } else {
              setOpen(true)
              inputRef.current?.focus()
              inputRef.current?.select()
            }
          }}
        >
          <span
            className="text-xs transition-transform duration-fast inline-block"
            style={{ transform: open ? 'rotate(180deg)' : 'none' }}
          >
            ▼
          </span>
        </button>
      </div>

      {open && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-60 overflow-y-auto rounded-md border border-line bg-canvas shadow-card divide-y divide-line/40">
          {filtered.map((d) => (
            <button
              key={d.id}
              type="button"
              className={`flex w-full flex-col px-3.5 py-2.5 text-left text-sm transition-colors hover:bg-blush hover:text-berry ${
                d.id === selectedId ? 'bg-blush font-semibold text-berry' : 'text-ink'
              }`}
              onMouseDown={(e) => {
                e.preventDefault()
                onSelect(d.id)
                setQuery(`${d.full_name} · ${d.specialty.name}`)
                setOpen(false)
              }}
            >
              <span className="font-semibold">{d.full_name}</span>
              <span className="text-xs text-muted line-clamp-1 mt-0.5">{d.specialty.name}</span>
            </button>
          ))}
          {filtered.length === 0 && (
            <p className="p-3 text-center text-sm text-muted">No doctors match &ldquo;{query}&rdquo;.</p>
          )}
        </div>
      )}
    </div>
  )
}

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
      <Field label="Doctor">
        <DoctorCombobox
          doctors={doctors.data ?? []}
          selectedId={doctorId}
          onSelect={(id) => setSelected(String(id))}
        />
      </Field>
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
