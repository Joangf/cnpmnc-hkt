import { expect, test } from '@playwright/test'

test('admin cannot write ERP-owned directory or slots through the API', async ({ request }) => {
  const login = await request.post('/api/v1/auth/login', { data: {
    email: process.env.E2E_ADMIN_EMAIL ?? 'admin@example.com', password: process.env.E2E_ADMIN_PASSWORD ?? 'Admin12345!',
  } })
  expect(login.ok()).toBeTruthy()
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` }
  for (const entity of ['hospitals', 'specialties', 'departments', 'doctors', 'appointment-types']) {
    expect((await request.post(`/api/v1/admin/${entity}`, { headers, data: {} })).status()).toBe(403)
    expect((await request.patch(`/api/v1/admin/${entity}/1`, { headers, data: {} })).status()).toBe(403)
  }
  expect((await request.post('/api/v1/admin/doctors/1/slots', { headers, data: {} })).status()).toBe(403)
})
