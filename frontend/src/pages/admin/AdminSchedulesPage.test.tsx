import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { api } from '../../api/endpoints'
import AdminSchedulesPage from './AdminSchedulesPage'
afterEach(() => { cleanup(); vi.restoreAllMocks() })
it('shows ERP slots without controls that mutate hospital data', async () => {
  vi.spyOn(api.admin, 'list').mockResolvedValue([{ id: 2, full_name: 'Dr Ada', specialty: { name: 'Cardiology' } }])
  vi.spyOn(api.admin, 'slots').mockResolvedValue({ doctor_id: 2, timezone: 'Asia/Ho_Chi_Minh', slots: [{ id: 1, doctor_id: 2, start_time: '2030-01-01T01:00:00Z', end_time: '2030-01-01T01:30:00Z', capacity: 5, booked_count: 2, remaining_places: 3, is_open: true, version: 1 }] })
  const query = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={query}><MemoryRouter><AdminSchedulesPage /></MemoryRouter></QueryClientProvider>)
  expect(await screen.findByText('2 booked / 5 places · 3 remaining')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /create|edit|save/i })).not.toBeInTheDocument()
  expect(screen.getByText(/read-only/)).toBeInTheDocument()
  query.clear()
})
