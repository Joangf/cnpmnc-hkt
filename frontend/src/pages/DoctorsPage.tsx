import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { DoctorCard } from '../components/DoctorCard'
import { SpecialtyFilter } from '../components/SpecialtyFilter'
import { EmptyState, ErrorAlert, stagger, Pagination, Spinner } from '../components/ui'
import { IconSearch } from '../components/icons'

export default function DoctorsPage() {
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')
  const num = (key: string) => (params.get(key) ? Number(params.get(key)) : undefined)
  const page = num('page') ?? 1

  const hospitals = useQuery({ queryKey: ['hospitals', 'all'], queryFn: () => api.directory.hospitals({ page_size: 100 }) })
  const doctors = useQuery({
    queryKey: ['doctors', params.toString()],
    queryFn: () =>
      api.directory.doctors({
        q: params.get('q') ?? undefined,
        hospital_id: num('hospital_id'),
        department_id: num('department_id'),
        specialty_id: num('specialty_id'),
        page,
      }),
    placeholderData: keepPreviousData,
  })

  const update = (changes: Record<string, string | undefined>) => {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(changes)) {
      if (v) next.set(k, v)
      else next.delete(k)
    }
    if (!('page' in changes)) next.delete('page')
    setParams(next)
  }

  return (
    <div className="pb-12">
      {/* Page Header */}
      <div className="mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blush text-berry text-xs font-semibold tracking-wider uppercase mb-3 border border-berry/20">
          Danh mục bác sĩ chuyên khoa
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-ink mb-3">
          Tìm kiếm &amp; Đặt lịch bác sĩ chuyên khoa
        </h1>
        <p className="text-muted text-base sm:text-lg max-w-2xl leading-relaxed">
          Khám phá danh sách các bác sĩ chuyên khoa hàng đầu tại HKT Hospital. Đặt lịch khám nhanh chóng, minh bạch chi phí và an tâm điều trị.
        </p>
      </div>

      {/* Search Form */}
      <form
        className="rounded-2xl border border-line/80 bg-canvas p-5 shadow-card hover:shadow-card-hover transition-all duration-base sm:p-6 mb-6"
        onSubmit={(e) => {
          e.preventDefault()
          update({ q: q.trim() || undefined })
        }}
      >
        <div className="flex flex-col md:flex-row items-stretch md:items-end gap-4">
          <label className="flex-[2_1_280px]">
            <span className="block text-sm font-semibold text-ink mb-1.5">Tên bác sĩ</span>
            <div className="relative">
              <input
                className="input mt-0 pl-10"
                type="search"
                placeholder="Ví dụ: Nguyen, Le, Ha..."
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted pointer-events-none flex items-center">
                <IconSearch size={18} />
              </span>
            </div>
          </label>

          <label className="flex-[1_1_240px]">
            <span className="block text-sm font-semibold text-ink mb-1.5">Cơ sở / Phòng khám</span>
            <select
              className="input mt-0"
              value={num('hospital_id') ?? ''}
              onChange={(e) => update({ hospital_id: e.target.value || undefined, department_id: undefined })}
            >
              <option value="">Tất cả cơ sở</option>
              {hospitals.data?.items.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.name}
                </option>
              ))}
            </select>
          </label>

          <div className="flex gap-2">
            <button className="btn-primary min-w-[130px] flex-1 md:flex-initial">
              Tìm kiếm
            </button>
            {(q || num('hospital_id') || num('specialty_id')) && (
              <button
                type="button"
                onClick={() => {
                  setQ('')
                  setParams(new URLSearchParams())
                }}
                className="btn-secondary px-4 text-sm"
                title="Xóa bộ lọc"
              >
                Đặt lại
              </button>
            )}
          </div>
        </div>
      </form>

      {/* Specialty Filter */}
      <SpecialtyFilter
        value={num('specialty_id')}
        onChange={(id) => update({ specialty_id: id ? String(id) : undefined, department_id: undefined })}
      />

      <div className="mt-8">
        {doctors.isLoading && (
          <div className="py-12 text-center">
            <Spinner />
          </div>
        )}
        <ErrorAlert error={doctors.error} />
        {doctors.data && (
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-medium text-muted" aria-live="polite">
              Tìm thấy <span className="font-bold text-ink">{doctors.data.total}</span> bác sĩ phù hợp
            </p>
          </div>
        )}
        {doctors.data?.items.length === 0 && (
          <EmptyState>Không tìm thấy bác sĩ nào phù hợp với bộ lọc. Vui lòng thử tìm kiếm theo chuyên khoa hoặc cơ sở khác.</EmptyState>
        )}
        {!!doctors.data?.items.length && (
          <div className="grid gap-6 md:grid-cols-2">
            {doctors.data.items.map((d, i) => (
              <DoctorCard key={d.id} doctor={d} style={stagger(i)} />
            ))}
          </div>
        )}
        {doctors.data && (
          <div className="mt-8">
            <Pagination page={page} pageSize={doctors.data.page_size} total={doctors.data.total} onChange={(p) => update({ page: String(p) })} />
          </div>
        )}
      </div>
    </div>
  )
}
