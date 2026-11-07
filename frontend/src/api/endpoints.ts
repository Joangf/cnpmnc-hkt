import { request } from './http'
import type * as T from './types'

type Scope = 'upcoming' | 'past' | 'all'

export const api = {
  auth: {
    register: (body: T.RegisterPayload) => request<T.RegistrationPending>('POST', '/auth/register', { body, auth: false }),
    resendRegistrationOtp: (email: string) =>
      request<T.RegistrationPending>('POST', '/auth/register/resend', { body: { email }, auth: false }),
    verifyRegistration: (email: string, otp: string) =>
      request<T.TokenResponse>('POST', '/auth/register/verify', { body: { email, otp }, auth: false }),
    login: (body: { email: string; password: string }) =>
      request<T.TokenResponse>('POST', '/auth/login', { body, auth: false }),
    logout: () => request<void>('POST', '/auth/logout', { auth: false }),
    requestPasswordReset: (email: string) =>
      request<T.PasswordResetRequested>('POST', '/auth/password-reset/request', { body: { email }, auth: false }),
    confirmPasswordReset: (token: string, new_password: string) =>
      request<T.Message>('POST', '/auth/password-reset/confirm', { body: { token, new_password }, auth: false }),
  },

  profile: {
    get: () => request<T.Profile>('GET', '/profile'),
    update: (body: T.ProfileUpdate) => request<T.Profile>('PATCH', '/profile', { body }),
  },

  directory: {
    specialties: () => request<T.Specialty[]>('GET', '/specialties'),
    hospitals: (query: {
      q?: string
      city?: string
      specialty_id?: number
      facility_type?: T.FacilityType
      page?: number
      page_size?: number
    }) => request<T.Page<T.HospitalSummary>>('GET', '/hospitals', { query }),
    hospital: (id: number) => request<T.HospitalDetail>('GET', `/hospitals/${id}`),
    departments: (query: {
      q?: string
      hospital_id?: number
      specialty_id?: number
      page?: number
      page_size?: number
    }) => request<T.Page<T.DepartmentSummary>>('GET', '/departments', { query }),
    department: (id: number) => request<T.DepartmentPublicDetail>('GET', `/departments/${id}`),
    doctors: (query: {
      q?: string
      hospital_id?: number
      department_id?: number
      specialty_id?: number
      /** Clinic-local `YYYY-MM-DDTHH:mm`; keeps doctors with an open schedule window in range. */
      available_from?: string
      available_to?: string
      page?: number
      page_size?: number
    }) => request<T.Page<T.DoctorSummary>>('GET', '/doctors', { query }),
    doctor: (id: number) => request<T.DoctorDetail>('GET', `/doctors/${id}`),
    appointmentTypes: (doctorId: number) => request<T.AppointmentType[]>('GET', `/doctors/${doctorId}/appointment-types`),
    availability: (doctorId: number, date: string, appointmentTypeId?: number) =>
      request<T.Availability>('GET', `/doctors/${doctorId}/availability`, {
        query: { date, appointment_type_id: appointmentTypeId },
      }),
    doctorReviews: (doctorId: number, page = 1) =>
      request<T.Page<T.ReviewPublic>>('GET', `/doctors/${doctorId}/reviews`, { query: { page, page_size: 10 } }),
  },

  symptoms: {
    list: () => request<T.Symptom[]>('GET', '/symptoms'),
    recommend: (body: { symptom_ids: number[]; free_text?: string }) =>
      request<T.Recommendation>('POST', '/symptoms/recommendations', { body }),
  },

  appointments: {
    list: (scope: Scope, page = 1) =>
      request<T.Page<T.AppointmentSummary>>('GET', '/appointments', { query: { scope, page, page_size: 20 } }),
    get: (id: number) => request<T.AppointmentDetail>('GET', `/appointments/${id}`),
    create: (body: T.AppointmentCreate, idempotencyKey: string) =>
      request<T.AppointmentDetail>('POST', '/appointments', { body, headers: { 'Idempotency-Key': idempotencyKey } }),
    cancel: (id: number, reason?: string) =>
      request<T.AppointmentDetail>('POST', `/appointments/${id}/cancel`, { body: { reason } }),
    pay: (id: number, idempotencyKey: string) =>
      request<T.PaymentInit>('POST', `/appointments/${id}/payments`, { headers: { 'Idempotency-Key': idempotencyKey } }),
    review: (id: number, body: T.ReviewCreate) => request<T.Review>('POST', `/appointments/${id}/review`, { body }),
  },

  payments: {
    get: (id: number) => request<T.Payment>('GET', `/payments/${id}`),
  },

  notifications: {
    list: () => request<T.NotificationList>('GET', '/notifications'),
    markRead: (id: number) => request<T.Notification>('POST', `/notifications/${id}/read`),
    markAllRead: () => request<void>('POST', '/notifications/read-all'),
  },

  admin: {
    slots: (doctorId: number, date: string) =>
      request<T.AdminSlotList>('GET', `/admin/doctors/${doctorId}/slots`, { query: { date } }),
    createSlot: (doctorId: number, body: T.SlotCreate) =>
      request<T.AdminSlot>('POST', `/admin/doctors/${doctorId}/slots`, { body }),
    updateSlot: (doctorId: number, slotId: number, body: T.SlotUpdate) =>
      request<T.AdminSlot>('PATCH', `/admin/doctors/${doctorId}/slots/${slotId}`, { body }),
    summary: () => request<T.ReportSummary>('GET', '/admin/reports/summary'),
    users: (query: { q?: string; page?: number }) => request<T.Page<T.AdminUser>>('GET', '/admin/users', { query }),
    setUserStatus: (id: number, account_status: T.AccountStatus) =>
      request<T.AdminUser>('PATCH', `/admin/users/${id}`, { body: { account_status } }),
    reviews: (query: { review_status?: string; page?: number }) =>
      request<T.Page<T.AdminReview>>('GET', '/admin/reviews', { query }),
    moderateReview: (id: number, status: 'PUBLISHED' | 'HIDDEN' | 'REMOVED', note?: string) =>
      request<T.AdminReview>('PATCH', `/admin/reviews/${id}`, { body: { status, note } }),
    appointments: (query: { appointment_status?: string; page?: number }) =>
      request<T.Page<T.AdminAppointment>>('GET', '/admin/appointments', { query }),
    auditLogs: (page = 1) => request<T.Page<T.AuditLog>>('GET', '/admin/audit-logs', { query: { page } }),
    syncSchedules: () =>
      request<{ doctors_synced: number; success: boolean }>('POST', '/admin/integrations/erp/sync-schedules'),

    // Directory management: list / create / update for each entity.
    list: <R>(entity: AdminEntity) => request<R[]>('GET', `/admin/${entity}`),
    create: <R>(entity: AdminEntity, body: Record<string, unknown>) => request<R>('POST', `/admin/${entity}`, { body }),
    update: <R>(entity: AdminEntity, id: number, body: Record<string, unknown>) =>
      request<R>('PATCH', `/admin/${entity}/${id}`, { body }),
  },
}

export type AdminEntity = 'hospitals' | 'specialties' | 'departments' | 'doctors' | 'appointment-types'
