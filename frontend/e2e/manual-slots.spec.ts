import { expect, test } from '@playwright/test'

test.use({ channel: process.env.E2E_BROWSER_CHANNEL })

test('ERP creates a shared slot; admins can only view it and patients see its capacity', async ({ page, request }) => {
  const erp = process.env.E2E_ERP_URL ?? 'http://localhost:8100'
  const login = await request.post('/api/v1/auth/login', { data: {
    email: process.env.E2E_ADMIN_EMAIL ?? 'admin@example.com', password: process.env.E2E_ADMIN_PASSWORD ?? 'Admin12345!',
  } })
  expect(login.ok()).toBeTruthy()
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` }
  const catalog = await (await request.get(`${erp}/catalog`)).json()
  expect(catalog.departments.length).toBeGreaterThan(0)
  const id = `E2E-${Date.now()}`
  const doctorData = { full_name: id, department_id: catalog.departments[0].id, is_active: true }
  expect((await request.put(`${erp}/directory/doctors/${id}`, { data: { id, data: doctorData } })).ok()).toBeTruthy()
  expect((await request.put(`${erp}/directory/appointment_types/${id}-type`, { data: {
    id: `${id}-type`, data: { name: 'Standard', duration_minutes: 30, doctor_id: id, fee_override: '0' },
  } })).ok()).toBeTruthy()
  const day = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(Date.now() + 3 * 86400000))
  const slotResponse = await request.put(`${erp}/slots/${id}-slot`, { data: {
    id: `${id}-slot`, doctor_id: id, start_time: `${day}T08:00:00+07:00`, end_time: `${day}T08:30:00+07:00`, capacity: 5,
  } })
  expect(slotResponse.ok()).toBeTruthy()
  const slot = await slotResponse.json()
  try {
    expect((await request.post('/api/v1/admin/integrations/erp/sync-schedules', { headers })).ok()).toBeTruthy()
    const doctors = await (await request.get('/api/v1/doctors', { params: { q: id } })).json()
    const doctor = doctors.items[0]
    expect(doctor).toBeTruthy()
    await page.goto('/login')
    await page.getByLabel('Email').fill(process.env.E2E_ADMIN_EMAIL ?? 'admin@example.com')
    await page.getByLabel('Password').fill(process.env.E2E_ADMIN_PASSWORD ?? 'Admin12345!')
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()
    await expect(page).not.toHaveURL(/\/login/)
    await page.goto('/admin/schedules')
    await page.getByRole('combobox', { name: 'Doctor', exact: true }).selectOption(String(doctor.id))
    await page.getByLabel('Slot date').fill(day)
    await expect(page.getByText('0 booked / 5 places · 5 remaining')).toBeVisible()
    await expect(page.getByRole('button', { name: /create slot|edit slot|save slot/i })).toHaveCount(0)
    await page.goto(`/doctors/${doctor.id}`)
    await page.getByRole('group', { name: 'Date', exact: true }).getByRole('button').nth(3).click()
    await expect(page.getByRole('button', { name: /08:00–08:30.*5 places left/ })).toBeVisible()
  } finally {
    await request.put(`${erp}/slots/${id}-slot`, { data: { ...slot, is_open: false } })
    await request.put(`${erp}/directory/doctors/${id}`, { data: { id, data: { ...doctorData, is_active: false } } })
    await request.post('/api/v1/admin/integrations/erp/sync-schedules', { headers })
  }
})
