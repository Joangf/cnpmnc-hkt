import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { IconArrowRight, IconHospital, IconLocation, IconSearch, IconStethoscope } from '../components/icons'
import { SpecialtyFilter } from '../components/SpecialtyFilter'
import { EmptyState, ErrorAlert, Pagination, Spinner, stagger } from '../components/ui'

export default function DepartmentsPage() {
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')
  const specialtyId = params.get('specialty_id') ? Number(params.get('specialty_id')) : undefined
  const hospitalId = params.get('hospital_id') ? Number(params.get('hospital_id')) : undefined
  const page = Number(params.get('page') ?? 1)

  const hospitals = useQuery({
    queryKey: ['hospitals', 'all'],
    queryFn: () => api.directory.hospitals({ page_size: 100 }),
  })
  const departments = useQuery({
    queryKey: ['departments', params.toString()],
    queryFn: () =>
      api.directory.departments({
        q: params.get('q') ?? undefined,
        hospital_id: hospitalId,
        specialty_id: specialtyId,
        page,
      }),
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
      <div className="mb-8">
        <div className="inline-flex items-center gap-2 rounded-full bg-blush px-3.5 py-1 text-xs font-semibold text-berry mb-3 border border-berry/20 uppercase tracking-wider">
          Khoa &amp; Phòng khám chuyên sâu
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-ink mb-3">
          Danh mục Khoa &amp; Phòng khám chuyên sâu
        </h1>
        <p className="max-w-2xl text-base text-muted leading-relaxed">
          Tra cứu vị trí phòng khám, thông tin khoa điều trị và các bác sĩ phụ trách tại HKT Hospital.
        </p>
      </div>

      <form
        className="rounded-2xl border border-line bg-canvas p-5 sm:p-6 shadow-card hover:shadow-card-hover transition-all duration-base mb-6"
        onSubmit={(e) => {
          e.preventDefault()
          update({ q: q.trim() || undefined })
        }}
      >
        <div className="flex flex-col md:flex-row items-stretch md:items-end gap-4">
          <label className="flex-[2_1_280px]">
            <span className="block text-sm font-semibold text-ink mb-1.5">Tên khoa, chuyên khoa hoặc tầng/vị trí</span>
            <div className="relative">
              <input
                className="input mt-0 pl-10"
                type="search"
                placeholder="Ví dụ: Tim mạch, Tầng 3, Nội tổng quát..."
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted flex items-center">
                <IconSearch size={18} />
              </span>
            </div>
          </label>
          <label className="flex-[1_1_220px]">
            <span className="block text-sm font-semibold text-ink mb-1.5">Cơ sở / Bệnh viện</span>
            <select
              className="input mt-0"
              value={hospitalId ?? ''}
              onChange={(e) => update({ hospital_id: e.target.value || undefined })}
            >
              <option value="">Tất cả cơ sở</option>
              {hospitals.data?.items.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.name}
                </option>
              ))}
            </select>
          </label>
          <button className="btn-primary min-w-[130px] font-semibold py-3 shadow-button hover:shadow-button-hover">
            Tìm kiếm
          </button>
        </div>
      </form>

      <SpecialtyFilter
        value={specialtyId}
        onChange={(id) => update({ specialty_id: id ? String(id) : undefined })}
      />

      <div className="mt-8">
        {departments.isLoading && (
          <div className="py-12 text-center">
            <Spinner />
          </div>
        )}
        <ErrorAlert error={departments.error} />
        {departments.data && (
          <p className="text-sm font-medium text-muted mb-4" aria-live="polite">
            Tìm thấy <span className="font-bold text-ink">{departments.data.total}</span> khoa và phòng khám
          </p>
        )}
        {departments.data?.items.length === 0 && (
          <EmptyState>Không tìm thấy khoa/phòng khám nào phù hợp với bộ lọc.</EmptyState>
        )}
        {!!departments.data?.items.length && (
          <div className="grid gap-6 md:grid-cols-2">
            {departments.data.items.map((d, i) => (
              <article
                key={d.id}
                className="card reveal group flex min-w-0 flex-col justify-between gap-4 rounded-2xl p-6 hover:-translate-y-1 hover:border-berry/60 hover:shadow-card-hover transition-all duration-base"
                style={stagger(i)}
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <h2 className="text-xl font-bold leading-tight text-ink group-hover:text-berry transition-colors">
                      <Link to={`/departments/${d.id}`} className="link-plain">
                        {d.name}
                      </Link>
                    </h2>
                    <span className="tag shrink-0 bg-mist text-info font-semibold text-xs px-2.5 py-1">
                      {d.specialty.name}
                    </span>
                  </div>
                  <p className="text-xs font-medium text-muted flex items-center gap-1.5 mb-3">
                    <IconHospital size={14} className="text-muted shrink-0" />
                    <span>{d.hospital.name}</span>
                  </p>
                  {d.description && <p className="line-clamp-2 text-sm text-muted leading-relaxed">{d.description}</p>}
                </div>

                <div className="border-t border-line/60 pt-3 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    {d.location && (
                      <span className="inline-flex items-center gap-1 rounded-md bg-surface px-2.5 py-1 text-xs font-semibold text-ink border border-line">
                        <IconLocation size={13} className="text-muted shrink-0" />
                        <span>{d.location}</span>
                      </span>
                    )}
                    <span className="inline-flex items-center gap-1.5 rounded-md bg-blush px-2.5 py-1 text-xs font-semibold text-berry border border-berry/20">
                      <IconStethoscope size={13} className="text-berry shrink-0" />
                      <span>{d.doctor_count} bác sĩ phụ trách</span>
                    </span>
                  </div>

                  <Link
                    to={`/departments/${d.id}`}
                    className="link inline-flex items-center gap-1.5 text-xs font-bold pt-1"
                    aria-label={`Xem chi tiết khoa ${d.name}`}
                  >
                    Xem chi tiết <IconArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
        {departments.data && (
          <div className="mt-8">
            <Pagination
              page={page}
              pageSize={departments.data.page_size}
              total={departments.data.total}
              onChange={(p) => update({ page: String(p) })}
            />
          </div>
        )}
      </div>
    </div>
  )
}
