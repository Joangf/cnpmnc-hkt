import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { api } from '../api/endpoints'
import { ApiError } from '../api/http'
import type { DoctorDetail } from '../api/types'
import { clinicDateTime, upcomingDays } from '../lib/format'
import { BookingPanel } from './BookingPanel'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: { role: 'PATIENT' } }) }))
const doctor = { id: 2 } as DoctorDetail
const day = upcomingDays(2)[1].value
const offer = {
  start_time: clinicDateTime(day, '08:00'), end_time: clinicDateTime(day, '08:50'),
  slot_id: 11, version: 2, capacity: 5, remaining_places: 3,
}
let queryClient: QueryClient

beforeEach(() => {
  queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  vi.spyOn(api.directory, 'appointmentTypes').mockResolvedValue([{
    id: 5, name: 'Standard', description: null, duration_minutes: 20, buffer_minutes: 10,
    fee: '100000', currency: 'VND', is_active: true,
  }])
  vi.spyOn(api.directory, 'availability').mockResolvedValue({
    doctor_id: 2, date: day, appointment_type_id: 5, timezone: 'Asia/Ho_Chi_Minh',
    source: 'erp-slots', generated_at: new Date().toISOString(), slots: [offer],
  })
  vi.spyOn(api.appointments, 'list').mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
})
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks() })

function show() {
  render(<QueryClientProvider client={queryClient}><MemoryRouter><Routes>
    <Route path="/" element={<BookingPanel doctor={doctor} />} />
    <Route path="/appointments/:id" element={<p>Booking created</p>} />
  </Routes></MemoryRouter></QueryClientProvider>)
}

it('shows held payment message and submits slot details when requesting appointment', async () => {
  const create = vi.spyOn(api.appointments, 'create').mockResolvedValue({ id: 99, status: 'PENDING' } as never)
  show()
  fireEvent.click(await screen.findByRole('button', { name: /08:00–08:50.*3 slots left/ }))
  expect(screen.getByText(/This appointment will be held for 15 minutes/i)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Request appointment' }))
  await waitFor(() => expect(create).toHaveBeenCalledWith({
    doctor_id: 2, appointment_type_id: 5, start_time: offer.start_time,
    slot_id: 11, slot_version: 2, reason_for_visit: undefined,
  }, expect.any(String)))
  expect(await screen.findByText('Booking created')).toBeInTheDocument()
})

it('clears a stale selection and refreshes availability on conflict', async () => {
  vi.spyOn(api.appointments, 'create').mockRejectedValue(new ApiError(409, 'SlotFull', 'This slot is full.'))
  show()
  fireEvent.click(await screen.findByRole('button', { name: /08:00–08:50/ }))
  vi.mocked(api.directory.availability).mockResolvedValue({
    doctor_id: 2, date: day, appointment_type_id: 5, timezone: 'Asia/Ho_Chi_Minh',
    source: 'erp-slots', generated_at: new Date().toISOString(), slots: [],
  })
  fireEvent.click(screen.getByRole('button', { name: 'Request appointment' }))
  expect(await screen.findByText(/No available times on this day/)).toBeInTheDocument()
  expect(screen.getByRole('alert')).toHaveTextContent('This slot is full.')
  expect(screen.queryByRole('button', { name: 'Request appointment' })).not.toBeInTheDocument()
})

it('shows hourly ERP windows with remaining slot counts and disables 0-slot full windows', async () => {
  vi.mocked(api.directory.availability).mockResolvedValue({
    doctor_id: 2,
    date: day,
    appointment_type_id: 5,
    timezone: 'Asia/Ho_Chi_Minh',
    source: 'erp-schedule-cache',
    generated_at: new Date().toISOString(),
    slots: [
      {
        start_time: clinicDateTime(day, '08:00'),
        end_time: clinicDateTime(day, '09:00'),
        capacity: 3,
        remaining_places: 0,
      },
      {
        start_time: clinicDateTime(day, '09:00'),
        end_time: clinicDateTime(day, '10:00'),
        capacity: 3,
        remaining_places: 2,
      },
    ],
  })
  show()
  const fullBtn = await screen.findByRole('button', { name: /08:00–09:00/ })
  expect(fullBtn).toBeDisabled()
  expect(fullBtn).toHaveTextContent('0 slots')

  const openBtn = screen.getByRole('button', { name: /09:00–10:00/ })
  expect(openBtn).toBeEnabled()
  expect(openBtn).toHaveTextContent('2 slots left')
})

it('shows past slots as disabled with Passed label', async () => {
  vi.mocked(api.directory.availability).mockResolvedValue({
    doctor_id: 2,
    date: day,
    appointment_type_id: 5,
    timezone: 'Asia/Ho_Chi_Minh',
    source: 'erp-schedule-cache',
    generated_at: new Date().toISOString(),
    slots: [
      {
        start_time: clinicDateTime(day, '08:00'),
        end_time: clinicDateTime(day, '09:00'),
        capacity: 3,
        remaining_places: 3,
        is_past: true,
      },
      {
        start_time: clinicDateTime(day, '09:00'),
        end_time: clinicDateTime(day, '10:00'),
        capacity: 3,
        remaining_places: 2,
        is_past: false,
      },
    ],
  })
  show()
  const passedBtn = await screen.findByRole('button', { name: /08:00–09:00/ })
  expect(passedBtn).toBeDisabled()
  expect(passedBtn).toHaveTextContent('Passed')
  expect(screen.getByText('1 time window available on this day')).toBeInTheDocument()
})

it('warns and disables booking when patient already has an appointment with this doctor on that day', async () => {
  vi.mocked(api.appointments.list).mockResolvedValue({
    items: [
      {
        id: 77,
        booking_reference: 'REF77',
        doctor: { id: 2, name: 'Dr. Test' },
        hospital: { id: 1, name: 'HKT Hospital' },
        department: { id: 1, name: 'Cardiology' },
        appointment_type: { id: 5, name: 'Standard' },
        start_time: clinicDateTime(day, '08:00'),
        end_time: clinicDateTime(day, '09:00'),
        status: 'PENDING',
        status_reason: null,
        check_in_status: 'NOT_CHECKED_IN',
        payment_status: 'UNPAID',
        payment_due_at: null,
        fee_amount: '100000',
        currency: 'VND',
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
  })
  show()
  expect(await screen.findByText(/Existing appointment on this day/i)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /View or cancel existing appointment/i })).toHaveAttribute('href', '/appointments/77')
  fireEvent.click(screen.getByRole('button', { name: /08:00–08:50/ }))
  expect(screen.getByRole('button', { name: 'Request appointment' })).toBeDisabled()
})
