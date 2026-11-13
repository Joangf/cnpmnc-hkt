import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { api } from '../../api/endpoints'
import AdminDirectoryPage from './AdminDirectoryPage'
afterEach(() => { cleanup(); vi.restoreAllMocks() })
it('shows ERP records without create/edit/deactivation controls', async () => {
  vi.spyOn(api.admin, 'list').mockResolvedValue([{ id: 1, name: 'Hospital A', is_active: true }])
  vi.spyOn(api.admin, 'erpStatus').mockResolvedValue({ ready: true, synced_at: '2030-01-01T00:00:00Z' })
  const query = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={query}><MemoryRouter><AdminDirectoryPage /></MemoryRouter></QueryClientProvider>)
  expect(await screen.findByText('Hospital A')).toBeInTheDocument()
  expect(screen.getByText(/Last synced/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /create|edit|deactivate|save/i })).not.toBeInTheDocument()
  query.clear()
})
