import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { api } from '../../api/endpoints'
import { ApiError } from '../../api/http'
import type { AdminSlot } from '../../api/types'
import { clinicDateTime, upcomingDays } from '../../lib/format'
import AdminSchedulesPage from './AdminSchedulesPage'

const day = upcomingDays(2)[1].value
let queryClient: QueryClient
let slots: AdminSlot[]

beforeEach(() => {
  slots = []
  queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  vi.spyOn(api.admin, 'list').mockResolvedValue([{
    id: 2, full_name: 'Dr Ada', specialty: { id: 1, name: 'Cardiology' },
    scheduling_mode: 'MANUAL', max_appointments_per_window: 1,
  }])
  vi.spyOn(api.admin, 'slots').mockImplementation(async () => ({ doctor_id: 2, timezone: 'Asia/Ho_Chi_Minh', slots }))
})

afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks() })

async function show() {
  render(<QueryClientProvider client={queryClient}><MemoryRouter><AdminSchedulesPage /></MemoryRouter></QueryClientProvider>)
  await screen.findByText('No manual slots on this date.')
}

function existing(booked = 0): AdminSlot {
  return {
    id: 11, doctor_id: 2, start_time: clinicDateTime(day, '08:00'),
    end_time: clinicDateTime(day, '08:30'), buffer_minutes: 10, capacity: 5,
    booked_count: booked, remaining_places: 5 - booked, is_open: true, version: 2,
  }
}

it('creates a dated shared slot with its own capacity and clinic-local times', async () => {
  const create = vi.spyOn(api.admin, 'createSlot').mockImplementation(async (_doctor, body) => {
    const result = { ...body, id: 11, doctor_id: 2, booked_count: 0, remaining_places: body.capacity, version: 1 }
    slots = [result]
    return result
  })
  await show()
  expect(screen.getByLabelText('Slot capacity')).toHaveValue(1)
  fireEvent.change(screen.getByLabelText('Slot capacity'), { target: { value: '5' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create slot' }))
  await waitFor(() => expect(create).toHaveBeenCalledWith(2, {
    start_time: clinicDateTime(day, '08:00'), end_time: clinicDateTime(day, '08:30'),
    buffer_minutes: 0, capacity: 5, is_open: true,
  }))
  expect(await screen.findByRole('status')).toHaveTextContent('Slot saved.')
  expect(await screen.findByText('0 booked / 5 places · 5 remaining · 0 min buffer')).toBeInTheDocument()
})

it('keeps inputs on failed save and announces the error', async () => {
  vi.spyOn(api.admin, 'createSlot').mockRejectedValue(new ApiError(409, 'SlotConflict', 'This slot overlaps an existing slot.'))
  await show()
  fireEvent.change(screen.getByLabelText('Start time'), { target: { value: '09:00' } })
  fireEvent.change(screen.getByLabelText('End time'), { target: { value: '09:30' } })
  fireEvent.change(screen.getByLabelText('Slot capacity'), { target: { value: '5' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create slot' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('This slot overlaps an existing slot.')
  expect(screen.getByLabelText('Start time')).toHaveValue('09:00')
  expect(screen.getByLabelText('Slot capacity')).toHaveValue(5)
})

it('locks booked times and submits versioned capacity/closure edits', async () => {
  slots = [existing(3)]
  const update = vi.spyOn(api.admin, 'updateSlot').mockImplementation(async (_doctor, _slot, body) => {
    slots = [{ ...slots[0], ...body, version: 3, remaining_places: 0 }]
    return slots[0]
  })
  render(<QueryClientProvider client={queryClient}><MemoryRouter><AdminSchedulesPage /></MemoryRouter></QueryClientProvider>)
  fireEvent.click(await screen.findByRole('button', { name: 'Edit slot 08:00' }))
  expect(screen.getByLabelText('Start time')).toHaveAttribute('readonly')
  expect(screen.getByLabelText('End time')).toHaveAttribute('readonly')
  expect(screen.getByLabelText('Buffer after slot (min)')).toHaveAttribute('readonly')
  fireEvent.change(screen.getByLabelText('Slot capacity'), { target: { value: '1' } })
  fireEvent.click(screen.getByLabelText('Open for new bookings'))
  fireEvent.click(screen.getByRole('button', { name: 'Save slot' }))
  await waitFor(() => expect(update).toHaveBeenCalledWith(2, 11, {
    start_time: clinicDateTime(day, '08:00'), end_time: clinicDateTime(day, '08:30'),
    capacity: 1, buffer_minutes: 10, is_open: false, version: 2,
  }))
  expect(await screen.findByText(/Existing bookings exceed the new capacity/)).toBeInTheDocument()
})

it('reports a blocked scheduling-mode switch without changing persisted mode', async () => {
  vi.mocked(api.admin.list).mockResolvedValue([{
    id: 2, full_name: 'Dr Ada', specialty: { id: 1, name: 'Cardiology' }, scheduling_mode: 'ERP',
  }])
  const update = vi.spyOn(api.admin, 'update').mockRejectedValue(new ApiError(409, 'SchedulingModeInUse', 'Resolve upcoming appointments before changing scheduling mode.'))
  await show()
  fireEvent.change(screen.getByLabelText('Scheduling mode'), { target: { value: 'MANUAL' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save mode' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Resolve upcoming appointments')
  expect(update).toHaveBeenCalledWith('doctors', 2, { scheduling_mode: 'MANUAL' })
  expect(screen.getByText(/ERP schedules are currently offered/)).toBeInTheDocument()
})

it('converts clinic wall times independently of the browser timezone', () => {
  expect(clinicDateTime('2030-01-01', '08:00')).toBe('2030-01-01T01:00:00.000Z')
  expect(clinicDateTime('2030-01-01', '00:00')).toBe('2029-12-31T17:00:00.000Z')
})
