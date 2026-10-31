import { useQuery } from '@tanstack/react-query'
import { useId } from 'react'
import { api } from '../api/endpoints'
import { FilterChip } from './ui'

/** Specialty chips: filter, don't paginate. Clicking the active chip clears it. */
export function SpecialtyFilter({ value, onChange }: { value?: number; onChange: (id?: number) => void }) {
  const specialties = useQuery({ queryKey: ['specialties'], queryFn: api.directory.specialties })
  const labelId = useId()
  return (
    <div className="mt-6">
      <p id={labelId} className="label">
        Specialty
      </p>
      <div role="group" aria-labelledby={labelId} className="mt-3 flex flex-wrap gap-3">
        <FilterChip pressed={value === undefined} onClick={() => onChange(undefined)}>
          All specialties
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
