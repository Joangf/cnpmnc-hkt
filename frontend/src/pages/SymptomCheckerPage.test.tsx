import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { api } from '../api/endpoints'
import SymptomCheckerPage from './SymptomCheckerPage'
beforeEach(() => {
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false })))
  HTMLElement.prototype.scrollIntoView = vi.fn()
  HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) { this.open = true })
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) { this.open = false })
})
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })
it('filters by department, searches symptoms and retains selections across departments', async () => {
  vi.spyOn(api.directory, 'departments').mockResolvedValue({ items: [
    { id: 1, name: 'Cardiology', hospital: { name: 'Demo' } },
    { id: 2, name: 'Dermatology', hospital: { name: 'Demo' } },
  ], total: 2, page: 1, page_size: 100 } as Awaited<ReturnType<typeof api.directory.departments>>)
  const symptoms = vi.spyOn(api.symptoms, 'list').mockImplementation(async (id) =>
    (id === 1 ? [{ id: 1, name: 'Chest pain' }, { id: 3, name: 'Palpitations' }] : [{ id: 2, name: 'Itchy skin' }]) as Awaited<ReturnType<typeof api.symptoms.list>>)
  const query = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={query}><MemoryRouter><SymptomCheckerPage /></MemoryRouter></QueryClientProvider>)
  fireEvent.click(screen.getByRole('button', { name: 'Add from the symptom list' }))
  await screen.findByRole('option', { name: 'Dermatology · Demo' })
  expect(symptoms).toHaveBeenCalledWith(undefined)
  expect(screen.getByLabelText('Choose a department')).toHaveValue('all')
  fireEvent.change(screen.getByLabelText('Choose a department'), { target: { value: '1' } })
  fireEvent.click(await screen.findByRole('button', { name: 'Chest pain' }))
  fireEvent.change(screen.getByLabelText('Search symptoms'), { target: { value: 'palp' } })
  expect(within(screen.getByRole('group', { name: 'Available symptoms' })).queryByRole('button', { name: 'Chest pain' })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Palpitations' })).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Choose a department'), { target: { value: '2' } })
  expect(await screen.findByRole('button', { name: 'Itchy skin' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Remove Chest pain' })).toBeInTheDocument()
  expect(screen.getByLabelText('Search symptoms')).toHaveValue('')
  fireEvent.change(screen.getByLabelText('Search symptoms'), { target: { value: 'no match' } })
  expect(screen.getByText('No symptoms match your search.')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Choose a department'), { target: { value: '1' } })
  expect(await screen.findByRole('button', { name: 'Chest pain' })).toHaveAttribute('aria-pressed', 'true')
  query.clear()
})

const recommendation = (warning: string | null = null) => ({
  matched_symptoms: [], specialties: [{ specialty_id: 1, name: 'Cardiology', score: 1, matched_symptoms: ['Chest pain'] }],
  departments: [], doctors: [], urgent_warning: warning, disclaimer: 'Demo', mode: 'rules',
  explanation: null, specialty_explanations: [], trace: [],
}) as Awaited<ReturnType<typeof api.symptoms.recommend>>

async function openWithSymptom() {
  vi.spyOn(api.directory, 'departments').mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 })
  vi.spyOn(api.symptoms, 'list').mockResolvedValue([{ id: 1, name: 'Chest pain', description: null }])
  const query = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={query}><MemoryRouter><SymptomCheckerPage /></MemoryRouter></QueryClientProvider>)
  fireEvent.click(screen.getByRole('button', { name: 'Add from the symptom list' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Chest pain' }))
  return query
}

it('focuses and scrolls to suggestions after a successful recommendation', async () => {
  vi.spyOn(api.symptoms, 'recommend').mockResolvedValue(recommendation())
  const query = await openWithSymptom()
  fireEvent.click(screen.getByRole('button', { name: '3. Suggest specialties and doctors' }))
  const results = await screen.findByRole('region', { name: 'Suggested specialties and doctors' })
  expect(results).toHaveFocus()
  expect(results.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' })
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
  query.clear()
})

it('shows severe warning first, then scrolls to results when dismissed', async () => {
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })))
  vi.spyOn(api.symptoms, 'recommend').mockResolvedValue(recommendation('Urgent warning from the checker'))
  const query = await openWithSymptom()
  fireEvent.click(screen.getByRole('button', { name: '3. Suggest specialties and doctors' }))
  const modal = await screen.findByRole('alertdialog', { name: 'Seek urgent medical care' })
  expect(within(modal).getByText('Urgent warning from the checker')).toBeInTheDocument()
  expect(HTMLElement.prototype.scrollIntoView).not.toHaveBeenCalled()
  fireEvent.click(within(modal).getByRole('button', { name: 'I understand' }))
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
  expect(screen.getByRole('region', { name: 'Suggested specialties and doctors' })).toHaveFocus()
  expect(HTMLElement.prototype.scrollIntoView).toHaveBeenCalledWith({ behavior: 'instant', block: 'start' })
  query.clear()
})

it('opens an urgent modal from interpreted symptoms and supports Escape', async () => {
  vi.spyOn(api.symptoms, 'interpret').mockResolvedValue({
    symptoms: [], urgent_warning: 'Interpretation warning', mode: 'rules', trace: [],
  } as unknown as Awaited<ReturnType<typeof api.symptoms.interpret>>)
  const query = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={query}><MemoryRouter><SymptomCheckerPage /></MemoryRouter></QueryClientProvider>)
  fireEvent.change(screen.getByLabelText('1. Describe how you feel'), { target: { value: 'chest pain' } })
  fireEvent.click(screen.getByRole('button', { name: 'Find my symptoms' }))
  const modal = await screen.findByRole('alertdialog')
  fireEvent(modal, new Event('cancel', { bubbles: false, cancelable: true }))
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
  expect(document.body.style.overflow).toBe('')
  query.clear()
})
