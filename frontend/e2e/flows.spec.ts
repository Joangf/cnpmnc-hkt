import { expect, test, type Page } from '@playwright/test'

const DAY_CHIP = /^(Today|[A-Z][a-z]{2},? \d{2} [A-Z][a-z]{2})$/
const SLOT = /^\d{2}:\d{2}$/

async function signIn(page: Page, email: string, password: string) {
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
}

/** Click through the date chips until a day with free slots appears, then pick a slot. */
async function pickFirstAvailableSlot(page: Page) {
  const chips = page.getByRole('button', { name: DAY_CHIP })
  await expect(chips.first()).toBeVisible()
  for (let i = 2; i < 14; i++) {
    await chips.nth(i).click()
    const slots = page.getByRole('button', { name: SLOT })
    const empty = page.getByText('No available times on this day')
    await expect(slots.first().or(empty)).toBeVisible()
    if (await slots.count()) {
      await slots.nth(Math.floor((await slots.count()) / 2)).click()
      return
    }
  }
  throw new Error('No available slot in the next two weeks')
}

test('guest can browse departments, doctors and the symptom checker', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /Find the right care/ })).toBeVisible()

  await page.getByRole('link', { name: /Dermatology/ }).first().click()
  await expect(page.getByRole('heading', { name: 'Doctors', exact: true })).toBeVisible()
  await page.locator('a[href^="/doctors/"]').first().click()
  await expect(page.getByRole('heading', { name: 'Book an appointment' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Patient reviews' })).toBeVisible()

  await page.goto('/departments') // no header tab any more; also reachable from the department link on doctor cards
  await expect(page.getByRole('heading', { name: 'Departments & clinics' })).toBeVisible()
  await expect(page.getByRole('heading', { name: /Dermatology Department/ }).first()).toBeVisible()

  await page.getByRole('link', { name: 'Symptom checker' }).first().click()
  await expect(page.getByText(/does not diagnose conditions/)).toBeVisible()
  await page.getByRole('button', { name: 'Persistent cough' }).click()
  await page.getByRole('button', { name: 'Chest pain' }).click()
  await page.getByRole('button', { name: 'Suggest specialties' }).click()
  await expect(page.getByText('Seek urgent medical care')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Suggested specialties' })).toBeVisible()
  await expect(page.getByText(/1\. (Respiratory Medicine|Cardiology)/)).toBeVisible()
})

test('patient registers, books, pays by bank transfer, cancels and gets a refund', async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`

  // Registration with client-side validation (FR-ACC-01, FR-PRO-03)
  await page.goto('/register')
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByText('Please enter your full name.')).toBeVisible()
  await page.getByLabel('Full name').fill('E2E Patient')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Date of birth').fill('1992-04-15')
  await page.getByLabel('Phone number').fill('+84 912 000 111')
  await page.getByLabel('Password', { exact: true }).fill('Secret123')
  await page.getByLabel('Confirm password').fill('Secret123')
  await page.getByRole('button', { name: 'Create account' }).click()

  // Email OTP step. In dev with RESEND_API_KEY empty the API returns the code and the form prefills it.
  await expect(page.getByRole('heading', { name: 'Verify your email' })).toBeVisible()
  await expect(page.getByLabel('Verification code')).toHaveValue(/^\d{6}$/)
  await page.getByRole('button', { name: 'Verify and continue' }).click()
  await expect(page.getByRole('heading', { name: 'Doctors', exact: true })).toBeVisible()

  // Booking (FR-BOOK-01..07). The fee comes from the single admin-configured consultation type.
  await page.locator('a[href^="/doctors/"]').first().click()
  const doctorId = page.url().match(/\/doctors\/(\d+)/)![1]
  const types = await (await page.request.get(`/api/v1/doctors/${doctorId}/appointment-types`)).json()
  const fee = Number(types[0].fee)
  expect(fee).toBeGreaterThan(0)
  await pickFirstAvailableSlot(page)
  await page.getByLabel('Reason for visit (optional)').fill('Annual check-up')
  await page.getByRole('button', { name: 'Request booking' }).click()
  await expect(page).toHaveURL(/\/appointments\/\d+$/)
  await expect(page.getByText('Booking reference')).toBeVisible()
  await expect(page.getByText('Confirmed', { exact: true })).toBeVisible()
  await expect(page.getByText('Payment: Unpaid')).toBeVisible()
  const appointmentUrl = page.url()
  const bookingReference = (await page.getByText(/^HK[A-Z0-9]{8}$/).first().textContent())!.trim()

  // VietQR payment, settled by a fake SePay webhook (FR-PAY-01..05, plan D3-D5)
  await page.getByRole('button', { name: 'Pay by bank transfer' }).click()
  await expect(page).toHaveURL(/\/payments\/\d+$/)
  await expect(page.getByRole('heading', { name: 'Pay by bank transfer' })).toBeVisible()
  await expect(page.getByText('Payment: Pending').first()).toBeVisible()
  const paymentCode = (await page.getByText(/^CB[A-Z0-9]{8}$/).first().textContent())!.trim()
  const vietnamNow = new Date(Date.now() + 7 * 3600_000).toISOString().slice(0, 19).replace('T', ' ')
  const webhook = await page.request.post('/api/v1/payments/sepay-webhook', {
    headers: { Authorization: `Apikey ${process.env.SEPAY_WEBHOOK_API_KEY ?? 'dev-sepay-key'}` },
    data: {
      id: Date.now(),
      gateway: 'OCB',
      transactionDate: vietnamNow,
      accountNumber: 'SEPNK33418',
      content: `${paymentCode} E2E`,
      transferType: 'in',
      transferAmount: fee,
      referenceCode: 'E2E',
    },
  })
  expect(webhook.ok()).toBeTruthy()
  await expect(page.getByRole('heading', { name: 'Payment received' })).toBeVisible()
  await page.getByRole('link', { name: 'View appointment' }).click()
  await expect(page.getByText('Payment: Paid').first()).toBeVisible()

  // Notifications (FR-NOT-01..03)
  await page.getByRole('link', { name: /Notifications/ }).first().click()
  await expect(page.getByText('Booking request submitted')).toBeVisible()
  await expect(page.getByText('Payment received').first()).toBeVisible()

  // Cancelling never refunds automatically (plan D13)
  await page.goto(appointmentUrl)
  await page.getByRole('button', { name: 'Cancel appointment' }).click()
  await expect(page.getByText('Cancelling does not refund your payment automatically.', { exact: false })).toBeVisible()
  await page.getByPlaceholder('Reason (optional)').fill('Plans changed')
  await page.getByRole('button', { name: 'Confirm cancellation' }).click()
  await expect(page.getByText('Cancelled', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('Payment: Paid').first()).toBeVisible()

  // Refund request (SCRUM-31). The bank list is third-party: fall back to manual entry if it is down.
  await expect(page.getByRole('heading', { name: 'Refund' })).toBeVisible()
  const bankSelect = page.getByRole('combobox', { name: /^Bank\b/ })
  const bankName = page.getByLabel('Bank name')
  await expect(bankSelect.or(bankName)).toBeVisible()
  if (await bankSelect.isVisible()) {
    await bankSelect.selectOption('970448')
  } else {
    await bankName.fill('OCB')
    await page.getByLabel('Bank BIN').fill('970448')
  }
  await page.getByLabel('Account number').fill('0123456789')
  await page.getByLabel('Account holder name').fill('e2e patient')
  await expect(page.getByLabel('Account holder name')).toHaveValue('E2E PATIENT')
  await page.getByRole('button', { name: 'Request refund' }).click()
  await expect(page.getByText('Refund requested', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Sign out' }).first().click()

  // Admin pays it out by hand and marks it transferred (SCRUM-32)
  await page.goto('/login')
  await signIn(page, 'admin@example.com', 'Admin12345!')
  await expect(page).toHaveURL(/\/admin$/)
  await page.getByRole('link', { name: 'Refunds' }).click()
  const request = page.getByRole('listitem').filter({ hasText: bookingReference })
  await request.getByRole('button', { name: 'Process' }).click()
  await expect(request.getByRole('img', { name: /VietQR refund/ })).toBeVisible()
  await request.getByLabel('Bank transaction reference (optional)').fill('E2E-FT')
  await request.getByRole('button', { name: 'Mark as transferred' }).click()
  await expect(page.getByRole('listitem').filter({ hasText: bookingReference })).toHaveCount(0)
  await page.getByRole('button', { name: 'Completed' }).click()
  await expect(page.getByRole('listitem').filter({ hasText: bookingReference })).toBeVisible()
  await page.getByRole('button', { name: 'Sign out' }).first().click()

  // The patient sees the refund done
  await page.goto(`/login?next=${encodeURIComponent(new URL(appointmentUrl).pathname)}`)
  await signIn(page, email, 'Secret123')
  await expect(page).toHaveURL(appointmentUrl)
  await expect(page.getByText('Refund completed')).toBeVisible()
  await expect(page.getByText('Payment: Refunded').first()).toBeVisible()

  // Session survives a reload via the refresh cookie
  await page.reload()
  await expect(page.getByText('Booking reference')).toBeVisible()
})

test('protected pages redirect to sign-in and back', async ({ page }) => {
  await page.goto('/appointments')
  await expect(page).toHaveURL(/\/login\?next=%2Fappointments/)
  await signIn(page, 'patient@example.com', 'Patient12345!')
  await expect(page).toHaveURL(/\/appointments$/)
  await page.getByRole('button', { name: 'Past & cancelled' }).click()
  await expect(page.getByText('Demo appointment').or(page.getByText(/HK[A-Z2-9]{8}/).first())).toBeVisible()
})

test('admin sees the dashboard and manages the directory', async ({ page }) => {
  await page.goto('/login')
  await signIn(page, 'admin@example.com', 'Admin12345!')
  await expect(page).toHaveURL(/\/admin$/)
  await expect(page.getByRole('heading', { name: 'Appointments by status' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Audit log' })).toBeVisible()

  await page.getByRole('link', { name: 'Directory' }).click()
  await page.getByRole('button', { name: 'Specialties' }).click()
  const name = `E2E Specialty ${Date.now()}`
  await page.getByLabel('Name *').fill(name)
  await page.getByRole('button', { name: 'Create' }).click()
  await expect(page.getByText(name)).toBeVisible()

  await page.getByRole('link', { name: 'Reviews' }).click()
  await expect(page.getByRole('button', { name: 'All' })).toBeVisible()
  await page.getByRole('link', { name: 'Users' }).click()
  await page.getByPlaceholder('Search email or name').fill('patient@example.com')
  await page.getByRole('button', { name: 'Search' }).click()
  await expect(page.getByRole('cell', { name: 'patient@example.com' })).toBeVisible()
})
