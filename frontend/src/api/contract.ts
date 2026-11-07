// Compile-time contract check between the hand-written client types (./types) and the types
// generated from the backend OpenAPI document (./schema.d.ts, `make gen-client`).
// If the backend changes a response or request shape, `npm run typecheck` fails here.
import type { components } from './schema'
import type * as T from './types'

type S = components['schemas']
/** true when every value of Actual is a valid Expected. */
type Fits<Actual, Expected> = [Actual] extends [Expected] ? true : false

// Responses: whatever the server sends must fit what the client reads.
export const responseContract: {
  UserMe: Fits<S['UserMe'], T.UserMe>
  TokenResponse: Fits<S['TokenResponse'], T.TokenResponse>
  Profile: Fits<S['ProfileOut'], T.Profile>
  Specialty: Fits<S['SpecialtyOut'], T.Specialty>
  HospitalPage: Fits<S['Page_HospitalSummary_'], T.Page<T.HospitalSummary>>
  HospitalDetail: Fits<S['HospitalDetail'], T.HospitalDetail>
  DepartmentPage: Fits<S['Page_DepartmentSummary_'], T.Page<T.DepartmentSummary>>
  DepartmentDetail: Fits<S['DepartmentPublicDetail'], T.DepartmentPublicDetail>
  DoctorPage: Fits<S['Page_DoctorSummary_'], T.Page<T.DoctorSummary>>
  DoctorDetail: Fits<S['DoctorDetail'], T.DoctorDetail>
  AdminDoctorDetail: Fits<S['AdminDoctorDetail'], T.AdminDoctorDetail>
  AdminSlot: Fits<S['AdminSlotOut'], T.AdminSlot>
  AdminSlotList: Fits<S['AdminSlotList'], T.AdminSlotList>
  AppointmentType: Fits<S['AppointmentTypeOut'], T.AppointmentType>
  Availability: Fits<S['AvailabilityResponse'], T.Availability>
  AppointmentPage: Fits<S['Page_AppointmentSummary_'], T.Page<T.AppointmentSummary>>
  AppointmentDetail: Fits<S['AppointmentDetail'], T.AppointmentDetail>
  PaymentInit: Fits<S['PaymentInitResponse'], T.PaymentInit>
  Payment: Fits<S['PaymentOut'], T.Payment>
  Review: Fits<S['ReviewOut'], T.Review>
  ReviewPage: Fits<S['Page_ReviewPublic_'], T.Page<T.ReviewPublic>>
  Symptom: Fits<S['SymptomOut'], T.Symptom>
  Recommendation: Fits<S['RecommendationResponse'], T.Recommendation>
  Notifications: Fits<S['NotificationList'], T.NotificationList>
  PasswordReset: Fits<S['PasswordResetRequested'], T.PasswordResetRequested>
  RegistrationPending: Fits<S['RegistrationPending'], T.RegistrationPending>
  AdminUserPage: Fits<S['Page_AdminUserOut_'], T.Page<T.AdminUser>>
  AdminReviewPage: Fits<S['Page_AdminReviewOut_'], T.Page<T.AdminReview>>
  AdminAppointmentPage: Fits<S['Page_AdminAppointmentOut_'], T.Page<T.AdminAppointment>>
  AppointmentTypeAdmin: Fits<S['AppointmentTypeAdminOut'], T.AppointmentTypeAdmin>
  ReportSummary: Fits<S['ReportSummary'], T.ReportSummary>
  AuditLogPage: Fits<S['Page_AuditLogOut_'], T.Page<T.AuditLog>>
} = {
  UserMe: true,
  TokenResponse: true,
  Profile: true,
  Specialty: true,
  HospitalPage: true,
  HospitalDetail: true,
  DepartmentPage: true,
  DepartmentDetail: true,
  DoctorPage: true,
  DoctorDetail: true,
  AdminDoctorDetail: true,
  AdminSlot: true,
  AdminSlotList: true,
  AppointmentType: true,
  Availability: true,
  AppointmentPage: true,
  AppointmentDetail: true,
  PaymentInit: true,
  Payment: true,
  Review: true,
  ReviewPage: true,
  Symptom: true,
  Recommendation: true,
  Notifications: true,
  PasswordReset: true,
  RegistrationPending: true,
  AdminUserPage: true,
  AdminReviewPage: true,
  AdminAppointmentPage: true,
  AppointmentTypeAdmin: true,
  ReportSummary: true,
  AuditLogPage: true,
}

// Requests: whatever the client sends must be accepted by the server schema.
export const requestContract: {
  Register: Fits<T.RegisterPayload, S['RegisterRequest']>
  ProfileUpdate: Fits<T.ProfileUpdate, S['ProfileUpdate']>
  AppointmentCreate: Fits<T.AppointmentCreate, S['AppointmentCreate']>
  SlotCreate: Fits<T.SlotCreate, S['SlotCreate']>
  SlotUpdate: Fits<T.SlotUpdate, S['SlotUpdate']>
  ReviewCreate: Fits<T.ReviewCreate, S['ReviewCreate']>
} = {
  Register: true,
  ProfileUpdate: true,
  AppointmentCreate: true,
  SlotCreate: true,
  SlotUpdate: true,
  ReviewCreate: true,
}
