import { expect, test } from '@playwright/test'

test.use({ channel: process.env.E2E_BROWSER_CHANNEL })

test('editing slot buffer and capacity updates the same slot and Find Doctor availability', async ({ page, request }) => {
  const email = process.env.E2E_ADMIN_EMAIL ?? 'admin@example.com'
  const password = process.env.E2E_ADMIN_PASSWORD ?? 'Admin12345!'
  const login = await request.post('/api/v1/auth/login', { data: { email, password } })
  expect(login.ok()).toBeTruthy()
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` }
  const published = await (await request.get('/api/v1/doctors')).json()
  const name = `Slot edit regression ${Date.now()}`
  const created = await request.post('/api/v1/admin/doctors', { headers, data: {
    department_id: published.items[0].department.id, full_name: name,
  } })
  expect(created.status()).toBe(201)
  const doctor = await created.json()
  expect(doctor.scheduling_mode).toBe('MANUAL')
  const date = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date(Date.now() + 3 * 86400000))
  try {
    await page.goto('/login')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()
    await expect(page).not.toHaveURL(/\/login/)
    await page.goto('/admin/schedules')
    await page.getByRole('combobox', { name: 'Doctor', exact: true }).selectOption(String(doctor.id))
    await page.getByLabel('Slot date').fill(date)
    await expect(page.getByText('No manual slots on this date.')).toBeVisible()
    await page.getByLabel('Start time', { exact: true }).fill('08:00')
    await page.getByLabel('End time', { exact: true }).fill('08:30')
    await page.getByLabel('Slot capacity').fill('5')
    await page.getByRole('button', { name: 'Create slot', exact: true }).click()
    await expect(page.getByText('0 booked / 5 places · 5 remaining · 0 min buffer')).toBeVisible()
    await expect(page.getByRole('combobox', { name: 'Scheduling mode', exact: true })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Save mode', exact: true })).toHaveCount(0)
    const original = await (await request.get(`/api/v1/doctors/${doctor.id}/availability`, { params: { date } })).json()
    expect(original.slots).toHaveLength(1)
    await page.getByRole('button', { name: 'Edit slot 08:00' }).click()
    await expect(page.getByRole('heading', { name: 'Edit slot', exact: true })).toBeVisible()
    await page.getByLabel('Buffer after slot (min)').fill('15')
    await page.getByLabel('Slot capacity').fill('7')
    const saved = page.waitForResponse(response => response.url().includes(`/admin/doctors/${doctor.id}/slots`) && response.request().method() === 'PATCH')
    await page.getByRole('button', { name: 'Save slot', exact: true }).click()
    const response = await saved
    expect(response.status(), await response.text()).toBe(200)
    await expect(page.getByText('0 booked / 7 places · 7 remaining · 15 min buffer')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Create slot', exact: true })).toBeVisible()
    await expect(page.getByLabel('Start time', { exact: true })).toHaveValue('')
    await expect(page.getByLabel('End time', { exact: true })).toHaveValue('')
    await expect(page.getByLabel('Buffer after slot (min)')).toHaveValue('0')
    await expect(page.getByLabel('Slot capacity')).toHaveValue('1')
    // Editing again must load the latest version and update the existing slot.
    await page.getByRole('button', { name: 'Edit slot 08:00' }).click()
    await page.getByLabel('Slot capacity').fill('8')
    const savedAgain = page.waitForResponse(response => response.url().includes(`/admin/doctors/${doctor.id}/slots`) && response.request().method() === 'PATCH')
    await page.getByRole('button', { name: 'Save slot', exact: true }).click()
    expect((await savedAgain).status()).toBe(200)
    await expect(page.getByText('0 booked / 8 places · 8 remaining · 15 min buffer')).toBeVisible()
    const offers = await (await request.get(`/api/v1/doctors/${doctor.id}/availability`, { params: { date } })).json()
    expect(offers.slots).toHaveLength(1)
    expect(offers.slots[0].slot_id).toBe(original.slots[0].slot_id)
    expect(offers.slots[0].capacity).toBe(8)
    expect(offers.slots[0].version).toBeGreaterThan(original.slots[0].version)
    await page.goto(`/doctors?q=${encodeURIComponent(name)}&available_from=${date}T08:00:00%2B07:00&available_to=${date}T08:30:00%2B07:00`)
    await expect(page.getByRole('link', { name: new RegExp(name) }).first()).toBeVisible()
    await page.goto(`/doctors/${doctor.id}`)
    await page.getByRole('group', { name: 'Date', exact: true }).getByRole('button').nth(3).click()
    await expect(page.getByRole('button', { name: /08:00–08:30.*8 places left/ })).toBeVisible()
  } finally {
    await request.delete(`/api/v1/admin/doctors/${doctor.id}`, { headers })
  }
})
