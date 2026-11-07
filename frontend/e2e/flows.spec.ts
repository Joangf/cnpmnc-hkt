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

test('guest can browse facilities, doctors and the symptom checker', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /Find the right care/ })).toBeVisible()

  await page.getByRole('link', { name: /Dermatology/ }).first().click()
  await expect(page.getByRole('heading', { name: 'Find a doctor' })).toBeVisible()
  await page.locator('a[href^="/doctors/"]').first().click()
  await expect(page.getByRole('heading', { name: 'Book an appointment' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Patient reviews' })).toBeVisible()

  await page.getByRole('link', { name: 'Hospitals & clinics' }).first().click()
  await expect(page.getByRole('heading', { name: 'Hospitals & clinics' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Lotus Skin & Eye Clinic' })).toBeVisible()

  await page.getByRole('link', { name: 'Symptom checker' }).first().click()
  await expect(page.getByText(/does not diagnose conditions/)).toBeVisible()
  await page.getByRole('button', { name: 'Persistent cough' }).click()
  await page.getByRole('button', { name: 'Chest pain' }).click()
  await page.getByRole('button', { name: 'Suggest specialties' }).click()
  await expect(page.getByText('Seek urgent medical care')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Suggested specialties' })).toBeVisible()
  await expect(page.getByText(/1\. (Respiratory Medicine|Cardiology)/)).toBeVisible()
})

test('patient registers, books, pays and cancels with a refund', async ({ page }) => {
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
  await expect(page.getByRole('heading', { name: 'Find a doctor' })).toBeVisible()

  // Booking (FR-BOOK-01..07)
  await page.locator('a[href^="/doctors/"]').first().click()
  await pickFirstAvailableSlot(page)
  await page.getByLabel('Reason for visit (optional)').fill('Annual check-up')
  await page.getByRole('button', { name: 'Request booking' }).click()
  await expect(page).toHaveURL(/\/appointments\/\d+$/)
  await expect(page.getByText('Booking reference')).toBeVisible()
  await expect(page.getByText('Confirmed', { exact: true })).toBeVisible()
  await expect(page.getByText('Payment: Unpaid')).toBeVisible()
  const appointmentUrl = page.url()

  // Payment through the sandbox gateway (FR-PAY-01..05)
  await page.getByRole('button', { name: 'Pay online' }).click()
  await expect(page.getByText('SANDBOX - no real payment')).toBeVisible()
  await page.getByRole('button', { name: 'Pay now' }).click()
  await expect(page).toHaveURL(/\/payments\/result\?payment_id=\d+/)
  await expect(page.getByText(/Payment of .* received/)).toBeVisible()
  await page.getByRole('link', { name: 'View appointment' }).click()
  await expect(page.getByText('Payment: Paid').first()).toBeVisible()

  // Notifications (FR-NOT-01..03)
  await page.getByRole('link', { name: /Notifications/ }).first().click()
  await expect(page.getByText('Booking request submitted')).toBeVisible()
  await expect(page.getByText('Payment successful')).toBeVisible()

  // Cancellation with refund (FR-APT-03, FR-PAY-07)
  await page.goto(appointmentUrl)
  await page.getByRole('button', { name: 'Cancel appointment' }).click()
  await page.getByPlaceholder('Reason (optional)').fill('Plans changed')
  await page.getByRole('button', { name: 'Confirm cancellation' }).click()
  await expect(page.getByText('Cancelled', { exact: true }).first()).toBeVisible()
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
