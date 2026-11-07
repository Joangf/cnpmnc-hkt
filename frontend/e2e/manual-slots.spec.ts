import { expect, test, type Page } from '@playwright/test'

// Use an installed Chrome when requested; CI can use the default Playwright Chromium.
test.use({ channel: process.env.E2E_BROWSER_CHANNEL })

async function signIn(page: Page, baseURL: string, email: string, password: string) {
  await page.goto(`${baseURL}/login`)
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).not.toHaveURL(/\/login/)
}

test('admin creates/edits a shared slot, patient books, closure preserves the reservation', async ({ page, browser, request, baseURL }) => {
  const base = baseURL ?? 'http://localhost:8080'
  const adminEmail = process.env.E2E_ADMIN_EMAIL ?? 'admin@example.com'
  const adminPassword = process.env.E2E_ADMIN_PASSWORD ?? 'Admin12345!'
  const patientEmail = process.env.E2E_PATIENT_EMAIL ?? 'patient@example.com'
  const patientPassword = process.env.E2E_PATIENT_PASSWORD ?? 'Patient12345!'
  const adminLogin = await request.post('/api/v1/auth/login', { data: { email: adminEmail, password: adminPassword } })
  expect(adminLogin.ok()).toBeTruthy()
  const adminHeaders = { Authorization: `Bearer ${(await adminLogin.json()).access_token}` }
  const patientLogin = await request.post('/api/v1/auth/login', { data: { email: patientEmail, password: patientPassword } })
  expect(patientLogin.ok()).toBeTruthy()
  const patientHeaders = { Authorization: `Bearer ${(await patientLogin.json()).access_token}` }
  const published = await (await request.get('/api/v1/doctors')).json()
  expect(published.items.length).toBeGreaterThan(0)
  const created = await request.post('/api/v1/admin/doctors', { headers: adminHeaders, data: {
    department_id: published.items[0].department.id, full_name: `E2E Manual Slots ${Date.now()}`,
    scheduling_mode: 'MANUAL', max_appointments_per_window: 1,
  } })
  expect(created.status()).toBe(201)
  const doctor = await created.json()
  const date = new Intl.DateTimeFormat('en-CA', {
    timeZone: process.env.E2E_CLINIC_TIMEZONE ?? 'Asia/Ho_Chi_Minh',
    year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date(Date.now() + 3 * 86400000))
  let appointmentId: number | undefined
  const patientContext = await browser.newContext({ viewport: { width: 1280, height: 900 } })
  try {
    await signIn(page, base, adminEmail, adminPassword)
    await page.goto(`${base}/admin/schedules`)
    await page.getByRole('combobox', { name: 'Doctor', exact: true }).selectOption(String(doctor.id))
    await page.getByLabel('Slot date').fill(date)
    await expect(page.getByText('No manual slots on this date.')).toBeVisible()
    await page.getByLabel('Start time', { exact: true }).fill('09:00')
    await page.getByLabel('End time', { exact: true }).fill('09:40')
    await page.getByLabel('Buffer after slot (min)').fill('10')
    await page.getByLabel('Slot capacity').fill('4')
    await page.getByRole('button', { name: 'Create slot', exact: true }).click()
    await expect(page.getByText('0 booked / 4 places · 4 remaining · 10 min buffer')).toBeVisible()
    await page.getByRole('button', { name: 'Edit slot 09:00' }).click()
    await page.getByLabel('End time', { exact: true }).fill('09:50')
    await page.getByLabel('Slot capacity').fill('5')
    await page.getByRole('button', { name: 'Save slot', exact: true }).click()
    await expect(page.getByText('0 booked / 5 places · 5 remaining · 10 min buffer')).toBeVisible()
    await page.screenshot({ path: test.info().outputPath('admin-desktop.png'), fullPage: true })
    await page.setViewportSize({ width: 375, height: 812 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
    await page.getByRole('heading', { name: 'Create slot', exact: true }).scrollIntoViewIfNeeded()
    await page.screenshot({ path: test.info().outputPath('admin-mobile.png') })
    await page.setViewportSize({ width: 1280, height: 900 })

    const patientPage = await patientContext.newPage()
    await signIn(patientPage, base, patientEmail, patientPassword)
    await patientPage.goto(`${base}/doctors/${doctor.id}`)
    await patientPage.getByRole('group', { name: 'Date', exact: true }).getByRole('button').nth(3).click()
    const slotButton = patientPage.getByRole('button', { name: /09:00–09:50.*5 places left/ })
    await slotButton.click()
    expect(await slotButton.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBeTruthy()
    await expect(patientPage.getByText('50 min', { exact: true })).toBeVisible()
    await expect(patientPage.getByText(/CareBook confirms this reservation immediately/)).toBeVisible()
    await patientPage.screenshot({ path: test.info().outputPath('patient-slot.png'), fullPage: true })
    const bookingResponse = patientPage.waitForResponse((response) =>
      response.url().endsWith('/api/v1/appointments') && response.request().method() === 'POST')
    await patientPage.getByRole('button', { name: 'Book appointment', exact: true }).click()
    const booked = await bookingResponse
    expect(booked.status()).toBe(201)
    const appointment = await booked.json()
    appointmentId = appointment.id
    expect(appointment.status).toBe('CONFIRMED')
    await expect(patientPage.getByText('Confirmed', { exact: true })).toBeVisible()

    await page.getByRole('button', { name: 'Refresh slots' }).click()
    await expect(page.getByText('1 booked / 5 places · 4 remaining · 10 min buffer')).toBeVisible()
    await page.getByRole('button', { name: 'Edit slot 09:00' }).click()
    await expect(page.getByLabel('Start time', { exact: true })).toHaveAttribute('readonly', '')
    await page.getByLabel('Open for new bookings').uncheck()
    await page.getByRole('button', { name: 'Save slot', exact: true }).click()
    await expect(page.getByText('Closed', { exact: true })).toBeVisible()
    const current = await request.get(`/api/v1/appointments/${appointmentId}`, { headers: patientHeaders })
    expect((await current.json()).status).toBe('CONFIRMED')
    const offers = await request.get(`/api/v1/doctors/${doctor.id}/availability`, { params: { date } })
    expect((await offers.json()).slots).toEqual([])
  } finally {
    if (appointmentId) {
      const cancelled = await request.post(`/api/v1/appointments/${appointmentId}/cancel`, {
        headers: patientHeaders, data: { reason: 'End-to-end test cleanup' },
      })
      expect(cancelled.ok()).toBeTruthy()
    }
    await request.patch(`/api/v1/admin/doctors/${doctor.id}`, {
      headers: adminHeaders, data: { is_active: false },
    })
    await patientContext.close()
  }
})
