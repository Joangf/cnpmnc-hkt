import { useQuery } from '@tanstack/react-query'
import { useId } from 'react'
import { api } from '../api/endpoints'
import { FilterChip } from './ui'
import { IconStethoscope } from './icons'

/** Specialty chips: filter, don't paginate. Clicking the active chip clears it. */
export function SpecialtyFilter({ value, onChange }: { value?: number; onChange: (id?: number) => void }) {
  const specialties = useQuery({ queryKey: ['specialties'], queryFn: api.directory.specialties })
  const labelId = useId()
  return (
    <div className="mt-6 mb-8">
      <div className="flex items-center justify-between mb-3">
        <p id={labelId} className="text-sm font-semibold text-ink flex items-center gap-2">
          <IconStethoscope size={16} className="text-berry" />
          <span>Lọc theo chuyên khoa</span>
          {specialties.data && (
            <span className="text-xs font-normal text-muted bg-surface px-2 py-0.5 rounded-full border border-line">
              {specialties.data.length} chuyên khoa
            </span>
          )}
        </p>
        {value !== undefined && (
          <button
            type="button"
            onClick={() => onChange(undefined)}
            className="text-xs text-berry font-semibold hover:underline"
          >
            Xem tất cả
          </button>
        )}
      </div>
      <div role="group" aria-labelledby={labelId} className="flex flex-wrap gap-2.5">
        <FilterChip pressed={value === undefined} onClick={() => onChange(undefined)}>
          Tất cả chuyên khoa
        </FilterChip>
        {specialties.data?.map((s) => (
          <FilterChip key={s.id} pressed={value === s.id} onClick={() => onChange(value === s.id ? undefined : s.id)}>
            {s.name}
          </FilterChip>
        ))}
      </div>
    </div>
  )
}
