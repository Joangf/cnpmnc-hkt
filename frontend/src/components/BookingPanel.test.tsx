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
    source: 'manual-slots', generated_at: new Date().toISOString(), slots: [offer],
  })
})
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks() })

function show() {
  render(<QueryClientProvider client={queryClient}><MemoryRouter><Routes>
    <Route path="/" element={<BookingPanel doctor={doctor} />} />
    <Route path="/appointments/:id" element={<p>Confirmed reservation</p>} />
  </Routes></MemoryRouter></QueryClientProvider>)
}

it('shows shared slot places and duration, and submits its identifier and version', async () => {
  const create = vi.spyOn(api.appointments, 'create').mockResolvedValue({ id: 99, status: 'CONFIRMED' } as never)
  show()
  fireEvent.click(await screen.findByRole('button', { name: /08:00–08:50.*3 places left/ }))
  expect(screen.getByText('50 min')).toBeInTheDocument()
  expect(screen.getByText(/CareBook confirms this reservation immediately/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Book appointment' }))
  await waitFor(() => expect(create).toHaveBeenCalledWith({
    doctor_id: 2, appointment_type_id: 5, start_time: offer.start_time,
    slot_id: 11, slot_version: 2, reason_for_visit: undefined,
  }, expect.any(String)))
  expect(await screen.findByText('Confirmed reservation')).toBeInTheDocument()
})

it('clears a stale selection and refreshes remaining places on conflict', async () => {
  vi.spyOn(api.appointments, 'create').mockRejectedValue(new ApiError(409, 'SlotFull', 'This slot is full.'))
  show()
  fireEvent.click(await screen.findByRole('button', { name: /08:00–08:50.*3 places left/ }))
  vi.mocked(api.directory.availability).mockResolvedValue({
    doctor_id: 2, date: day, appointment_type_id: 5, timezone: 'Asia/Ho_Chi_Minh',
    source: 'manual-slots', generated_at: new Date().toISOString(), slots: [],
  })
  fireEvent.click(screen.getByRole('button', { name: 'Book appointment' }))
  expect(await screen.findByText(/No available times on this day/)).toBeInTheDocument()
  expect(screen.getByRole('alert')).toHaveTextContent('This slot is full.')
  expect(screen.queryByRole('button', { name: 'Book appointment' })).not.toBeInTheDocument()
})
