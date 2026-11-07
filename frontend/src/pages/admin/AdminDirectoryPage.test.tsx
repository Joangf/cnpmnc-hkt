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

function renderDirectory() {
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter><AdminDirectoryPage /></MemoryRouter>
    </QueryClientProvider>,
  )
}

async function show(entity: 'Doctors' | 'Appointment types') {
  renderDirectory()
  fireEvent.click(screen.getByRole('button', { name: entity }))
  await screen.findByRole('button', { name: entity === 'Doctors' ? 'Edit Dr Ada' : 'Edit Standard' })
}

describe('admin directory pagination', () => {
  function seedDirectory() {
    records.doctors = Array.from({ length: 23 }, (_, i) => ({ ...doctor, id: i + 1, full_name: `Doctor ${i + 1}` }))
    records.departments = Array.from({ length: 23 }, (_, i) => ({
      ...(records.departments[0] as object), id: i + 1, name: `Department ${i + 1}`,
    }))
    records.specialties = Array.from({ length: 23 }, (_, i) => ({ id: i + 1, name: `Specialty ${i + 1}`, is_active: true }))
  }

  it.each([
    ['Doctors', 'Doctor'], ['Departments', 'Department'], ['Specialties', 'Specialty'],
  ])('shows ten %s at a time with page boundaries and item counts', async (tab, name) => {
    seedDirectory()
    renderDirectory()
    fireEvent.click(screen.getByRole('button', { name: tab }))
    await screen.findByRole('button', { name: `Edit ${name} 1` })
    expect(screen.getAllByRole('button', { name: /^Edit / })).toHaveLength(10)
    expect(screen.getByText(`Showing 1–10 of 23 ${tab.toLowerCase()}`)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: `Edit ${name} 11` })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('Page 2 of 3')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: `Edit ${name} 11` })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getAllByRole('button', { name: /^Edit / })).toHaveLength(3)
    expect(screen.getByText(`Showing 21–23 of 23 ${tab.toLowerCase()}`)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Previous' }))
    expect(screen.getByText('Page 2 of 3')).toBeInTheDocument()
  })

  it('returns to the first page when switching directory tabs', async () => {
    seedDirectory()
    renderDirectory()
    fireEvent.click(screen.getByRole('button', { name: 'Doctors' }))
    await screen.findByRole('button', { name: 'Edit Doctor 1' })
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    fireEvent.click(screen.getByRole('button', { name: 'Departments' }))
    expect(await screen.findByText('Showing 1–10 of 23 departments')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Doctors' }))
    expect(screen.getByText('Showing 1–10 of 23 doctors')).toBeInTheDocument()
  })

  it('edits a later-page doctor and keeps every department available in the form', async () => {
    seedDirectory()
    const update = vi.spyOn(api.admin, 'update').mockResolvedValue({})
    renderDirectory()
    fireEvent.click(screen.getByRole('button', { name: 'Doctors' }))
    await screen.findByRole('button', { name: 'Edit Doctor 1' })
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    fireEvent.click(screen.getByRole('button', { name: 'Edit Doctor 11' }))
    fireEvent.change(screen.getByLabelText(/Full name/), { target: { value: 'Updated Doctor 11' } })
    fireEvent.change(screen.getByRole('combobox', { name: /^Department/ }), { target: { value: '23' } })
    fireEvent.click(screen.getByRole('button', { name: 'Previous' }))
    expect(screen.getByLabelText(/Full name/)).toHaveValue('Updated Doctor 11')
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(update).toHaveBeenCalledWith('doctors', 11, {
      full_name: 'Updated Doctor 11', department_id: 23,
    }))
  })

  it('returns to a valid page when refreshed data removes the last page', async () => {
    seedDirectory()
    renderDirectory()
    fireEvent.click(screen.getByRole('button', { name: 'Doctors' }))
    await screen.findByRole('button', { name: 'Edit Doctor 1' })
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    records.doctors = records.doctors.slice(0, 12)
    await queryClient.invalidateQueries({ queryKey: ['admin', 'doctors'] })
    expect(await screen.findByText('Showing 11–12 of 12 doctors')).toBeInTheDocument()
    expect(screen.getByText('Page 2 of 2')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  })

  it('hides pagination for short and empty lists', async () => {
    await show('Doctors')
    expect(screen.getByText('Showing 1–1 of 1 doctors')).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Pagination' })).not.toBeInTheDocument()
    records.doctors = []
    await queryClient.invalidateQueries({ queryKey: ['admin', 'doctors'] })
    expect(await screen.findByText('No items to display.')).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Pagination' })).not.toBeInTheDocument()
  })
})

describe('SCRUM-21 scheduling controls', () => {
  it('omits ERP scheduling controls from the doctor form', async () => {
    await show('Doctors')
    expect(screen.queryByLabelText(/Capacity per work window/)).not.toBeInTheDocument()
    expect(screen.queryByLabelText('ERP doctor ID')).not.toBeInTheDocument()
  })

  it('offers a doctor selector and bounded duration and buffer fields', async () => {
    const update = vi.spyOn(api.admin, 'update').mockResolvedValue({})
    await show('Appointment types')
    fireEvent.change(screen.getByLabelText(/Duration \(min\)/), { target: { value: '30' } })
    fireEvent.change(screen.getByLabelText('Limit to doctor'), { target: { value: '2' } })
    expect(screen.getByLabelText(/Buffer \(min\)/)).toHaveValue(10)
    expect(screen.getByLabelText(/Duration \(min\)/)).toHaveAttribute('min', '5')
    expect(screen.getByLabelText(/Duration \(min\)/)).toHaveAttribute('max', '480')
    expect(screen.getByLabelText(/Buffer \(min\)/)).toHaveAttribute('max', '120')
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(update).toHaveBeenCalledWith('appointment-types', 5, {
      duration_minutes: 30, doctor_id: 2,
    }))
    expect(await screen.findByRole('status')).toHaveTextContent('Scheduling settings saved.')
  })

  it('retains attempted inputs and confirmed values when a save fails', async () => {
    vi.spyOn(api.admin, 'update').mockRejectedValue(
      new ApiError(409, 'SchedulingWriteFailed', 'Previous settings remain effective.'),
    )
    await show('Doctors')
    fireEvent.click(screen.getByRole('button', { name: 'Edit Dr Ada' }))
    fireEvent.change(screen.getByLabelText(/Full name/), { target: { value: 'Updated Ada' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Previous settings remain effective.')
    expect(screen.getByLabelText(/Full name/)).toHaveValue('Updated Ada')
    expect(screen.getByRole('button', { name: 'Edit Dr Ada' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled()
  })

  it('disables saving while pending and refreshes confirmed values and public caches on success', async () => {
    let finish!: (value: unknown) => void
    vi.spyOn(api.admin, 'update').mockImplementation(() => new Promise((resolve) => { finish = resolve }))
    queryClient.setQueryData(['availability', 2, 5, '2030-01-01'], { slots: [] })
    queryClient.setQueryData(['appointment-types', 2], [])
    await show('Doctors')
    fireEvent.click(screen.getByRole('button', { name: 'Edit Dr Ada' }))
    fireEvent.change(screen.getByLabelText(/Full name/), { target: { value: 'Updated Ada' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled())
    expect(screen.getByRole('button', { name: 'Edit Dr Ada' })).toBeInTheDocument()
    records.doctors = [{ ...doctor, full_name: 'Updated Ada' }]
    finish(records.doctors[0])
    expect(await screen.findByRole('button', { name: 'Edit Updated Ada' })).toBeInTheDocument()
    expect(await screen.findByRole('status')).toHaveTextContent('Scheduling settings saved.')
    expect(queryClient.getQueryState(['availability', 2, 5, '2030-01-01'])?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(['appointment-types', 2])?.isInvalidated).toBe(true)
  })
})
