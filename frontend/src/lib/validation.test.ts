import { safeNext } from '../pages/LoginPage'
import { upcomingDays } from './format'
import { passwordSchema, phoneSchema, registerSchema } from './validation'

describe('validation (mirrors backend rules)', () => {
  it('normalises and validates phone numbers', () => {
    expect(phoneSchema.parse('+84 901-234-567')).toBe('+84901234567')
    expect(phoneSchema.safeParse('12345').success).toBe(false)
  })

  it('requires letters and digits in passwords', () => {
    expect(passwordSchema.safeParse('abcdefgh').success).toBe(false)
    expect(passwordSchema.safeParse('abcdefg1').success).toBe(true)
  })

  it('rejects mismatched password confirmation', () => {
    const result = registerSchema.safeParse({
      email: 'a@example.com',
      password: 'Secret123',
      confirm_password: 'Secret124',
      full_name: 'Test User',
      date_of_birth: '1990-01-01',
      phone_number: '+84901234567',
    })
    expect(result.success).toBe(false)
  })

  it('allows date of birth and phone number to be left empty at registration', () => {
    const base = { email: 'a@example.com', password: 'Secret123', confirm_password: 'Secret123', full_name: 'Test User' }
    expect(registerSchema.safeParse({ ...base, date_of_birth: '', phone_number: '' }).success).toBe(true)
    expect(registerSchema.safeParse({ ...base, date_of_birth: '', phone_number: '12' }).success).toBe(false)
  })
})

describe('helpers', () => {
  it('only allows relative redirects after login', () => {
    expect(safeNext('/appointments/1', '/')).toBe('/appointments/1')
    expect(safeNext('//evil.example', '/')).toBe('/')
    expect(safeNext('https://evil.example', '/')).toBe('/')
    expect(safeNext('/\\evil.example', '/')).toBe('/')
  })

  it('produces clinic-local ISO dates', () => {
    const days = upcomingDays(3, new Date('2026-11-01T18:00:00Z')) // 01:00 on Nov 2 in UTC+7
    expect(days.map((d) => d.value)).toEqual(['2026-11-02', '2026-11-03', '2026-11-04'])
    expect(days[0].label).toBe('Today')
  })
})
