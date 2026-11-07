import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, type AdminEntity } from '../../api/endpoints'
import { ApiError } from '../../api/http'
import AdminDirectoryPage from './AdminDirectoryPage'

const doctor = {
  id: 2, full_name: 'Dr Ada', is_active: true, max_appointments_per_window: 3,
  hospital: { id: 1, name: 'Hospital' }, department: { id: 1, name: 'Department' },
  specialty: { id: 1, name: 'Cardiology' }, consultation_fee: '0', erp_doctor_id: null,
}
let records: Record<AdminEntity, unknown[]>
let queryClient: QueryClient

beforeEach(() => {
  records = {
    hospitals: [],
    specialties: [{ id: 1, name: 'Cardiology', is_active: true }],
    departments: [{ id: 1, hospital_id: 1, name: 'Department', is_active: true,
      specialty: { id: 1, name: 'Cardiology' } }],
    doctors: [{ ...doctor }],
    'appointment-types': [{
      id: 5, name: 'Standard', is_active: true, duration_minutes: 20, buffer_minutes: 10,
      doctor_id: null, specialty_id: null, fee_override: null,
    }],
  }
  vi.spyOn(api.admin, 'list').mockImplementation((entity) => Promise.resolve(records[entity] as never))
  queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
})

afterEach(() => {
  cleanup()
  queryClient.clear()
  vi.restoreAllMocks()
})

async function show(entity: 'Doctors' | 'Appointment types') {
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter><AdminDirectoryPage /></MemoryRouter>
    </QueryClientProvider>,
  )
  fireEvent.click(screen.getByRole('button', { name: entity }))
  await screen.findByRole('button', { name: entity === 'Doctors' ? 'Edit Dr Ada' : 'Edit Standard' })
}

describe('SCRUM-21 scheduling controls', () => {
  it('defaults doctor capacity to one and enforces positive whole integers', async () => {
    await show('Doctors')
    const capacity = screen.getByLabelText(/Capacity per work window/) as HTMLInputElement
    expect(capacity).toHaveValue(1)
    expect(capacity).toHaveAttribute('min', '1')
    expect(capacity).toHaveAttribute('step', '1')
    for (const value of ['0', '-1', '1.5', '']) {
      fireEvent.change(capacity, { target: { value } })
      expect(capacity.checkValidity()).toBe(false)
    }
    fireEvent.change(capacity, { target: { value: '4' } })
    expect(capacity.checkValidity()).toBe(true)
    expect(screen.getByText(/A stricter hospital schedule limit still applies/)).toBeInTheDocument()
  })

  it('offers a doctor selector and bounded duration and buffer fields', async () => {
    const create = vi.spyOn(api.admin, 'create').mockResolvedValue({})
    await show('Appointment types')
    fireEvent.change(screen.getByLabelText('Name *'), { target: { value: 'Doctor consultation' } })
    fireEvent.change(screen.getByLabelText(/Duration \(min\)/), { target: { value: '30' } })
    fireEvent.change(screen.getByLabelText('Limit to doctor'), { target: { value: '2' } })
    expect(screen.getByLabelText(/Buffer \(min\)/)).toHaveValue(0)
    expect(screen.getByLabelText(/Duration \(min\)/)).toHaveAttribute('min', '5')
    expect(screen.getByLabelText(/Duration \(min\)/)).toHaveAttribute('max', '480')
    expect(screen.getByLabelText(/Buffer \(min\)/)).toHaveAttribute('max', '120')
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    await waitFor(() => expect(create).toHaveBeenCalledWith('appointment-types', {
      name: 'Doctor consultation', duration_minutes: 30, buffer_minutes: 0, doctor_id: 2,
    }))
    expect(await screen.findByRole('status')).toHaveTextContent('Scheduling settings saved.')
  })

  it('retains attempted inputs and confirmed values when a save fails', async () => {
    vi.spyOn(api.admin, 'update').mockRejectedValue(
      new ApiError(409, 'SchedulingWriteFailed', 'Previous settings remain effective.'),
    )
    await show('Doctors')
    fireEvent.click(screen.getByRole('button', { name: 'Edit Dr Ada' }))
    fireEvent.change(screen.getByLabelText(/Capacity per work window/), { target: { value: '7' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Previous settings remain effective.')
    expect(screen.getByLabelText(/Capacity per work window/)).toHaveValue(7)
    expect(screen.getByText(/Capacity 3 per work window/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled()
  })

  it('disables saving while pending and refreshes confirmed values and public caches on success', async () => {
    let finish!: (value: unknown) => void
    vi.spyOn(api.admin, 'update').mockImplementation(() => new Promise((resolve) => { finish = resolve }))
    queryClient.setQueryData(['availability', 2, 5, '2030-01-01'], { slots: [] })
    queryClient.setQueryData(['appointment-types', 2], [])
    await show('Doctors')
    fireEvent.click(screen.getByRole('button', { name: 'Edit Dr Ada' }))
    fireEvent.change(screen.getByLabelText(/Capacity per work window/), { target: { value: '5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled())
    expect(screen.getByText(/Capacity 3 per work window/)).toBeInTheDocument()
    records.doctors = [{ ...doctor, max_appointments_per_window: 5 }]
    finish(records.doctors[0])
    expect(await screen.findByText(/Capacity 5 per work window/)).toBeInTheDocument()
    expect(await screen.findByRole('status')).toHaveTextContent('Scheduling settings saved.')
    expect(queryClient.getQueryState(['availability', 2, 5, '2030-01-01'])?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(['appointment-types', 2])?.isInvalidated).toBe(true)
  })
})
