import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type AdminEntity } from '../../api/endpoints'
import { Card, ErrorAlert, FilterChip, Notice, Pagination, Spinner } from '../../components/ui'
import { AdminNav } from './AdminNav'
import { formatDateTime } from '../../lib/format'

const entities: { key: AdminEntity; label: string }[] = [
  { key: 'specialties', label: 'Specialties' }, { key: 'doctors', label: 'Doctors' },
  { key: 'appointment-types', label: 'Appointment types' },
]
type RecordRow = { id: number; name?: string; full_name?: string; description?: string; introduction?: string; is_active: boolean; department?: { name: string }; specialty?: { name: string }; address?: string; fee_override?: string | null }
export default function AdminDirectoryPage() {
  const [entity, setEntity] = useState<AdminEntity>('specialties')
  const [page, setPage] = useState(1)
  const records = useQuery({ queryKey: ['admin', entity], queryFn: () => api.admin.list<RecordRow>(entity) })
  const sync = useQuery({ queryKey: ['admin', 'erp-status'], queryFn: api.admin.erpStatus })
  const items = records.data ?? []
  const currentPage = Math.min(page, Math.max(1, Math.ceil(items.length / 10)))
  return <div>
    <h1 className="page-title mb-6">Hospital directory</h1><AdminNav />
    <Notice>Directory information is managed by the hospital ERP. Contact the hospital to request changes.</Notice>
    <p className="caption my-4">{sync.data?.synced_at ? `Last synced: ${formatDateTime(sync.data.synced_at)}` : 'Awaiting ERP synchronization.'}</p>
    <ErrorAlert error={sync.error} />
    <div className="mb-6 flex flex-wrap gap-3">{entities.map(item => <FilterChip key={item.key} pressed={entity === item.key} onClick={() => { setEntity(item.key); setPage(1) }}>{item.label}</FilterChip>)}</div>
    <ErrorAlert error={records.error} />{records.isLoading && <Spinner />}
    <Card><ul className="divide-y divide-line">{items.slice((currentPage - 1) * 10, currentPage * 10).map(row => <li className="space-y-2 py-4" key={row.id}>
      <div className="flex flex-wrap items-center gap-3"><h2 className="font-semibold">{row.full_name ?? row.name}</h2><span className="tag">{row.is_active ? 'Active' : 'Inactive'}</span></div>
      <p className="caption">{[row.department?.name, row.specialty?.name, row.address].filter(Boolean).join(' · ')}</p>
      {(row.description || row.introduction) && <p>{row.description ?? row.introduction}</p>}
      {row.fee_override != null && <p>Consultation fee: {Number(row.fee_override).toLocaleString()} VND</p>}
    </li>)}</ul>{records.data && !items.length && <p>No records synchronized yet.</p>}
    <Pagination page={currentPage} pageSize={10} total={items.length} onChange={setPage} /></Card>
  </div>
}
