// Hand-written client types. They are checked against the generated OpenAPI types
// (schema.d.ts, `make gen-client`) at compile time in ./contract.ts.

export type UserRole = 'PATIENT' | 'ADMIN'
export type AccountStatus = 'PENDING' | 'ACTIVE' | 'INACTIVE'
export type FacilityType = 'HOSPITAL' | 'CLINIC'
export type AppointmentStatus = 'PENDING' | 'CONFIRMED' | 'REJECTED' | 'CANCELLED' | 'COMPLETED' | 'NO_SHOW'
export type CheckInStatus = 'NOT_CHECKED_IN' | 'CHECKED_IN' | 'UNKNOWN'
export type PaymentStatus = 'UNPAID' | 'PENDING' | 'PAID' | 'FAILED' | 'REFUNDED'
export type ReviewStatus = 'PENDING' | 'PUBLISHED' | 'HIDDEN' | 'REMOVED'
export type Decimal = string // Pydantic serialises Decimal as a string

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Ref {
  id: number
  name: string
}

export interface Message {
  message: string
}

// --- auth / profile --------------------------------------------------------------------------

export interface UserMe {
  id: number
  email: string
  role: UserRole
  account_status: AccountStatus
  full_name: string | null
  patient_id: number | null
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: UserMe
}

export interface RegisterPayload {
  email: string
  password: string
  full_name: string
  date_of_birth?: string | null
  phone_number?: string | null
}

export interface RegistrationPending {
  email: string
  message: string
  expires_in: number
  dev_otp?: string | null
}

export interface PasswordResetRequested {
  message: string
  dev_reset_token?: string | null
}

export interface Profile {
  id: number
  email: string
  full_name: string
  date_of_birth: string | null
  phone_number: string | null
  address: string | null
}

export type ProfileUpdate = Partial<Omit<Profile, 'id' | 'email'>>

// --- directory -------------------------------------------------------------------------------

export interface Specialty {
  id: number
  name: string
  description: string | null
  is_active: boolean
}

export interface Department {
  id: number
  hospital_id: number
  name: string
  description: string | null
  specialty: Specialty
  is_active: boolean
}

export interface HospitalSummary {
  id: number
  name: string
  facility_type: FacilityType
  address: string
  city: string
  phone: string | null
  email: string | null
  is_active: boolean
  specialties: Specialty[]
}

export interface HospitalDetail extends HospitalSummary {
  description: string | null
  website: string | null
  departments: Department[]
}

export interface DoctorSummary {
  id: number
  full_name: string
  title: string | null
  experience_years: number
  consultation_fee: Decimal | null
  currency: string
  rating_avg: Decimal
  rating_count: number
  avatar_url: string | null
  hospital: Ref
  department: Ref
  specialty: Ref
  is_active: boolean
}

export interface DoctorDetail extends DoctorSummary {
  qualifications: string | null
  introduction: string | null
  erp_doctor_id: string | null
}

export interface AppointmentType {
  id: number
  name: string
  description: string | null
  duration_minutes: number
  buffer_minutes: number
  fee: Decimal | null
  currency: string
  is_active: boolean
}

export interface Slot {
  start_time: string
  end_time: string
}

export interface Availability {
  doctor_id: number
  date: string
  appointment_type_id: number
  timezone: string
  slots: Slot[]
  generated_at: string
  source: string
}

// --- appointments / payments -----------------------------------------------------------------

export interface AppointmentCreate {
  doctor_id: number
  appointment_type_id: number
  start_time: string
  reason_for_visit?: string
}

export interface StatusHistory {
  field: string
  from_value: string | null
  to_value: string
  reason: string | null
  source: string
  created_at: string
}

export interface PaymentSummary {
  id: number
  status: PaymentStatus
  amount: Decimal
  currency: string
  provider_reference: string | null
  failure_reason: string | null
  paid_at: string | null
  created_at: string
}

export interface AppointmentSummary {
  id: number
  booking_reference: string
  status: AppointmentStatus
  status_reason: string | null
  check_in_status: CheckInStatus
  payment_status: PaymentStatus
  start_time: string
  end_time: string
  doctor: Ref
  hospital: Ref
  department: Ref
  appointment_type: Ref
  fee_amount: Decimal
  currency: string
}

export interface AppointmentDetail extends AppointmentSummary {
  reason_for_visit: string | null
  history: StatusHistory[]
  payments: PaymentSummary[]
  can_cancel: boolean
  can_pay: boolean
  can_review: boolean
  has_review: boolean
  cancellation_deadline: string
}

export interface PaymentInit {
  payment_id: number
  status: PaymentStatus
  amount: Decimal
  currency: string
  checkout_url: string
}

export interface Payment {
  id: number
  appointment_id: number
  booking_reference: string
  status: PaymentStatus
  amount: Decimal
  currency: string
  provider_reference: string | null
  failure_reason: string | null
  paid_at: string | null
  created_at: string
}

// --- reviews / symptoms / notifications ------------------------------------------------------

export interface ReviewCreate {
  rating: number
  comment?: string
}

export interface Review {
  id: number
  appointment_id: number
  doctor_id: number
  rating: number
  comment: string | null
  status: ReviewStatus
  created_at: string
}

export interface ReviewPublic {
  id: number
  rating: number
  comment: string | null
  author: string
  created_at: string
}

export interface Symptom {
  id: number
  name: string
  description: string | null
}

export interface Recommendation {
  matched_symptoms: Symptom[]
  specialties: { specialty_id: number; name: string; score: number; matched_symptoms: string[] }[]
  departments: {
    department_id: number
    department_name: string
    hospital_id: number
    hospital_name: string
    city: string
    specialty_id: number
  }[]
  urgent_warning: string | null
  disclaimer: string
}

export interface Notification {
  id: number
  type: string
  title: string
  content: string
  link: string | null
  created_at: string
  read_at: string | null
}

export interface NotificationList {
  items: Notification[]
  unread_count: number
}

// --- admin -----------------------------------------------------------------------------------

export interface AdminUser {
  id: number
  email: string
  role: UserRole
  account_status: AccountStatus
  full_name: string | null
  created_at: string
  last_login_at: string | null
}

export interface AdminReview extends Review {
  doctor_name: string
  patient_id: number
  moderation_note: string | null
}

export interface AdminAppointment extends AppointmentSummary {
  patient_id: number
}

export interface AppointmentTypeAdmin extends AppointmentType {
  fee_override: Decimal | null
  specialty_id: number | null
  doctor_id: number | null
}

export interface ReportSummary {
  appointments_by_status: Record<string, number>
  payments_by_status: { status: PaymentStatus; count: number; total_amount: Decimal }[]
  top_specialties: { specialty_id: number; name: string; count: number }[]
  total_patients: number
  generated_at: string
}

export interface AuditLog {
  id: number
  actor_id: number | null
  actor_type: string
  action: string
  entity_type: string
  entity_id: string | null
  details: Record<string, unknown> | null
  request_id: string | null
  created_at: string
}
