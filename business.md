# Healthcare Appointment Booking & Clinic Recommendation System
## Functional Requirements Document (FRD)

**Version:** 1.2  
**Date:** 30 October 2026  
**Document status:** Draft for academic project planning

---

## 1. Introduction

### 1.1 Purpose

This document defines the functional and non-functional requirements for a patient-facing healthcare appointment platform. The platform helps patients discover healthcare services, receive preliminary specialty recommendations based on reported symptoms, book appointments, make online payments, track appointment status, and review doctors after consultations.

The system is designed as an external-facing platform. It does not replace the hospital's existing Hospital Information System (HIS) or Enterprise Resource Planning (ERP) system.

### 1.2 Product scope

The proposed platform provides the following capabilities:

- Browse hospitals, departments, clinics, and doctors.
- Search and view doctor profiles and available appointment times.
- Receive rule-based specialty recommendations from entered symptoms.
- Create and manage appointments.
- Pay applicable appointment fees online.
- View appointment history and synchronized appointment status.
- Submit reviews for doctors after completed appointments.
- Receive notifications about relevant appointment events.
- Allow administrators to manage platform-level information and oversee system activity.

### 1.3 Out of scope

The following capabilities are excluded from the current project scope:

- Hospital partner onboarding and partner relationship management.
- Paid clinic advertising, sponsored listings, and campaign management.
- Health news, articles, and editorial content management.
- Hospital ERP replacement or internal hospital workflow management.
- Electronic medical records authoring and clinical diagnosis.
- Native Android and iOS applications.
- AI-based diagnosis or machine-learning-based treatment recommendations.
- Automated QR-based check-in, unless a supported hospital integration is available.

### 1.4 Target platform

The recommended MVP is a **responsive web application** that works on desktop and mobile browsers. A Progressive Web App (PWA) may be considered later. Separate native mobile applications are not required for the initial release.

---

## 2. Users and Roles

The system has three primary roles.

| Role | Description | Main capabilities |
|---|---|---|
| Guest | A visitor who has not signed in | Browse hospitals, departments, doctors, and general information; use the symptom recommendation feature if enabled |
| Patient | A registered and authenticated user | Manage profile, book and manage appointments, pay online, view appointment history and status, submit doctor reviews |
| Admin | A platform administrator | Manage platform information, user accounts, doctor/department listings, reviews, and operational reports |

**Boundary note:** Hospital doctors, receptionists, and other hospital employees are not separate roles in this platform's MVP. Their internal operations remain in the hospital's existing ERP/HIS. If integration is available, the platform exchanges relevant appointment and status data with that system.

---

## 3. System Context and External Integration

### 3.1 External platform boundary

The platform focuses on patient-facing discovery and appointment services. The hospital's existing ERP/HIS remains responsible for internal hospital operations, such as:

- Official doctor schedules and internal resource allocation.
- Hospital-side appointment confirmation and operational handling.
- Patient arrival processing and check-in.
- Clinical records, diagnoses, prescriptions, and treatment.
- Internal billing and other hospital workflows.

### 3.2 ERP/HIS integration

Where the hospital provides APIs or another supported integration mechanism, the platform should exchange only the information required for the patient-facing workflow.

Potential integration data includes:

- Hospital, department, doctor, and service information.
- Doctor availability and appointment capacity.
- Appointment creation or booking requests.
- Appointment confirmation, cancellation, and completion status.
- Check-in status.
- Appointment fee or payment-related information, where supported.

The exact integration method and source of truth must be confirmed with the hospital.

### 3.3 Integration assumptions

1. The hospital ERP/HIS is the source of truth for internal schedules and operational check-in.
2. The platform must not display an appointment as confirmed until the relevant booking operation has been accepted by the authoritative booking system.
3. If no real hospital API is available during development, the team may implement a mock ERP service or a clearly separated local scheduling module for demonstration.
4. The project must document which functions are simulated and which are genuinely integrated.

---

## 4. Functional Requirements

Priority labels:

- **Must:** Required for the MVP.
- **Should:** Important, but may be simplified if time is limited.
- **Could:** Optional enhancement.

### 4.1 User Account Management

| ID | Requirement | Priority |
|---|---|---|
| FR-ACC-01 | The system shall allow a guest to register an account using the required personal and authentication information. | Must |
| FR-ACC-02 | The system shall allow registered users to sign in and sign out securely. | Must |
| FR-ACC-03 | The system shall provide a password reset mechanism. | Should |
| FR-ACC-04 | The system shall restrict patient-specific functions to authenticated users. | Must |
| FR-ACC-05 | The system shall allow an administrator to view, activate, or deactivate user accounts. | Should |

### 4.2 Patient Profile Management

| ID | Requirement | Priority |
|---|---|---|
| FR-PRO-01 | The system shall allow patients to view their personal profile. | Must |
| FR-PRO-02 | The system shall allow patients to update permitted profile information, such as full name, date of birth, phone number, and contact details. | Must |
| FR-PRO-03 | The system shall validate required fields and applicable input formats. | Must |
| FR-PRO-04 | The system shall retain the patient identifier required to associate appointments with the correct patient. | Must |

### 4.3 Hospital, Department, and Doctor Discovery

| ID | Requirement | Priority |
|---|---|---|
| FR-DIS-01 | The system shall display available hospitals or healthcare facilities supported by the platform. | Must |
| FR-DIS-02 | The system shall allow users to browse departments or specialties within a hospital. | Must |
| FR-DIS-03 | The system shall display doctor profiles, including name, specialty, qualifications, experience, introduction, and available information. | Must |
| FR-DIS-04 | The system shall allow users to search or filter doctors by hospital, department, specialty, or doctor name. | Should |
| FR-DIS-05 | The system shall display relevant appointment fees when the information is available. | Should |
| FR-DIS-06 | The system shall display doctor ratings and reviews where available. | Should |

### 4.4 Hospital Appointment Booking and Scheduling

| ID | Requirement | Priority |
|---|---|---|
| FR-BOOK-01 | The system shall allow an authenticated patient to select a hospital, department, doctor, appointment date, and available appointment time. | Must |
| FR-BOOK-02 | The system shall display available appointment times based on the latest schedule and capacity information available to the platform. | Must |
| FR-BOOK-03 | The system shall collect the information required to create an appointment, including the reason for the visit when applicable. | Must |
| FR-BOOK-04 | The system shall validate appointment availability again when the patient submits a booking request. | Must |
| FR-BOOK-05 | The system shall prevent conflicting bookings when the authoritative scheduling service supports reservation locking or equivalent concurrency control. | Must |
| FR-BOOK-06 | The system shall display a booking reference after a booking has been successfully accepted. | Must |
| FR-BOOK-07 | The system shall clearly communicate whether an appointment is pending, confirmed, rejected, or otherwise awaiting processing. | Must |
| FR-BOOK-08 | The system should support configurable appointment durations based on doctor, specialty, or appointment type. | Should |
| FR-BOOK-09 | The system should account for buffer time between appointments where required. | Should |

#### 4.4.1 Scheduling design

Appointment duration may vary depending on the doctor, specialty, appointment type, and expected consultation complexity. Therefore, the system should not assume that every consultation has the same duration.

The recommended approach for the MVP is a **hybrid scheduling model**:

1. Define configurable appointment durations for relevant doctors, specialties, or appointment types.
2. Use standard start-time increments, such as every 10 or 15 minutes, to generate candidate start times.
3. Consider a candidate time available only if the entire required appointment duration and any required buffer fit within the doctor's available schedule.
4. Exclude times that overlap with existing appointments, unavailable periods, or capacity limits.
5. Revalidate availability when the patient submits the booking request.

**Illustrative example**

Suppose a doctor is available from 07:00 to 08:00.

- Appointment type A requires 20 minutes.
- Appointment type B requires 30 minutes.
- A 10-minute buffer may be required after a consultation.
- Candidate start times may be generated at 10-minute increments.
- A candidate is offered only if the full appointment interval, including the applicable buffer, fits and does not conflict with another booking.

The example is illustrative only. Actual durations, increments, buffers, and capacity rules must be configurable rather than hard-coded.

#### 4.4.2 Concurrent booking protection

Two patients may attempt to book the same remaining availability at nearly the same time. The system must revalidate availability during submission and rely on an atomic reservation operation, database constraint, transaction, or authoritative ERP booking API to prevent double booking.

The user interface's displayed availability is not a guarantee that a slot will remain available until submission.

### 4.5 Appointment Management

| ID | Requirement | Priority |
|---|---|---|
| FR-APT-01 | The system shall allow patients to view their upcoming appointments. | Must |
| FR-APT-02 | The system shall allow patients to view appointment details, including doctor, department, date, time, hospital, fee, and booking reference when available. | Must |
| FR-APT-03 | The system shall allow patients to request cancellation subject to the applicable cancellation policy. | Must |
| FR-APT-04 | The system shall display the latest appointment status available from the booking system. | Must |
| FR-APT-05 | The system should allow patients to view past appointments. | Must |
| FR-APT-06 | The system should explain why a booking was rejected or cancelled when that information is provided by the authoritative system. | Should |

### 4.6 Clinic and Specialty Discovery

This feature provides a directory of healthcare facilities and specialties. It does not include partner onboarding or advertising management.

| ID | Requirement | Priority |
|---|---|---|
| FR-CLN-01 | The system shall display the clinics or healthcare facilities available in the platform directory. | Must |
| FR-CLN-02 | The system shall display basic clinic information, such as name, address, contact information, and supported specialties. | Must |
| FR-CLN-03 | The system shall allow users to browse clinics by specialty. | Should |
| FR-CLN-04 | The system should allow users to search clinics by name or location. | Should |

### 4.7 Symptom-Based Specialty and Clinic Recommendation

| ID | Requirement | Priority |
|---|---|---|
| FR-REC-01 | The system shall allow users to enter or select symptoms they are experiencing. | Must |
| FR-REC-02 | The system shall process the selected symptoms using a predefined rule-based mapping. | Must |
| FR-REC-03 | The system shall suggest one or more relevant medical specialties based on the selected symptoms. | Must |
| FR-REC-04 | The system shall display clinics or departments that provide the suggested specialties, where directory data is available. | Should |
| FR-REC-05 | The system shall inform users that the recommendation is for navigation purposes and is not a medical diagnosis. | Must |
| FR-REC-06 | The system should display an appropriate warning to seek urgent medical care when a clinician-reviewed warning-sign rule is triggered. | Should |

#### 4.7.1 MVP recommendation approach

The MVP should use a transparent, rule-based approach rather than attempting to diagnose users with an AI model.

A simplified flow:

1. The user selects or enters symptoms.
2. The system maps the symptoms to relevant specialties using predefined rules.
3. The system displays suggested specialties and matching clinics or departments.
4. The user chooses whether to continue browsing or book an appointment.

Examples of possible mappings (to be reviewed by a qualified healthcare professional):

| Example symptom | Possible specialty |
|---|---|
| Persistent cough or breathing discomfort | Respiratory medicine |
| Skin rash or itching | Dermatology |
| Joint pain | Orthopedics or rheumatology |
| Eye discomfort or blurred vision | Ophthalmology |
| Digestive discomfort | Gastroenterology |

These examples are not clinical guidance and must not be treated as a complete medical decision tree. The final rules and any urgent-care warnings should be reviewed by qualified healthcare professionals.

### 4.8 Doctor Reviews and Ratings

| ID | Requirement | Priority |
|---|---|---|
| FR-REV-01 | The system shall allow a patient to submit a review for a doctor after an eligible completed appointment. | Must |
| FR-REV-02 | The system shall allow patients to provide a rating and optional written feedback. | Must |
| FR-REV-03 | The system shall prevent multiple reviews for the same eligible appointment, unless an edit policy is explicitly supported. | Must |
| FR-REV-04 | The system shall display published doctor ratings and reviews. | Should |
| FR-REV-05 | The system shall allow an administrator to review, hide, or remove inappropriate content according to the platform's moderation policy. | Should |

### 4.9 Appointment History and Available Medical History

| ID | Requirement | Priority |
|---|---|---|
| FR-HIS-01 | The system shall allow patients to view their past and upcoming appointment history. | Must |
| FR-HIS-02 | The system shall display appointment details and status changes available to the platform. | Must |
| FR-HIS-03 | If the hospital provides authorized integration, the system may display selected medical information made available to the patient. | Could |
| FR-HIS-04 | The system shall not create or modify clinical records that belong to the hospital ERP/HIS. | Must |

**Scope clarification:** For the MVP, appointment history is required. Full electronic medical record functionality is not required.

### 4.10 Online Payment Management

| ID | Requirement | Priority |
|---|---|---|
| FR-PAY-01 | The system shall display the payable appointment fee before payment. | Must |
| FR-PAY-02 | The system shall allow patients to initiate payment through a supported payment gateway. | Must |
| FR-PAY-03 | The system shall record the payment transaction reference and payment status returned by the gateway. | Must |
| FR-PAY-04 | The system shall update the payment status after receiving and validating the gateway response or callback. | Must |
| FR-PAY-05 | The system shall display payment results to the patient. | Must |
| FR-PAY-06 | The system should support payment failure handling and retry where permitted. | Should |
| FR-PAY-07 | The system should support refunds only if the selected payment provider and business policy support them. | Could |

Payment status must be tracked separately from appointment status. A successful payment does not necessarily mean that the hospital has confirmed the appointment unless the booking workflow explicitly defines that relationship.

### 4.11 Appointment Check-in Status

| ID | Requirement | Priority |
|---|---|---|
| FR-CIN-01 | The system shall display a booking reference or appointment identifier that the patient can present at the hospital. | Must |
| FR-CIN-02 | If the hospital ERP/HIS provides check-in status, the system shall display the synchronized status to the patient. | Should |
| FR-CIN-03 | The system shall not mark an appointment as checked in merely because the patient opens the appointment page or taps a button. | Must |
| FR-CIN-04 | The system may display a QR code containing a booking reference if supported by the hospital's workflow. | Could |

**MVP boundary:** Actual check-in is performed by hospital staff through the existing hospital system. The external platform only displays the status it receives. QR scanning and automated check-in can be considered later if the hospital provides a suitable API or operational process.

### 4.12 Notification Management

| ID | Requirement | Priority |
|---|---|---|
| FR-NOT-01 | The system shall notify patients when a booking request is successfully submitted. | Must |
| FR-NOT-02 | The system shall notify patients when an appointment is confirmed, rejected, cancelled, or rescheduled, when such status changes are received. | Should |
| FR-NOT-03 | The system shall notify patients about payment results. | Should |
| FR-NOT-04 | The system may support email or other notification channels depending on available services. | Could |

### 4.13 Administration

| ID | Requirement | Priority |
|---|---|---|
| FR-ADM-01 | The system shall provide a protected administrative interface. | Must |
| FR-ADM-02 | The administrator shall be able to manage hospital, department, specialty, and doctor directory information maintained by the platform. | Must |
| FR-ADM-03 | The administrator shall be able to manage patient accounts. | Should |
| FR-ADM-04 | The administrator shall be able to moderate doctor reviews. | Should |
| FR-ADM-05 | The administrator shall be able to view basic appointment and payment summaries available to the platform. | Should |
| FR-ADM-06 | The system shall record important administrative actions for accountability. | Should |

### 4.14 Basic Reporting

| ID | Requirement | Priority |
|---|---|---|
| FR-RPT-01 | The system should provide a basic overview of appointment counts by status. | Should |
| FR-RPT-02 | The system should provide basic payment summaries based on recorded transactions. | Should |
| FR-RPT-03 | The system may provide simple statistics about frequently selected specialties. | Could |

---

## 5. Main Workflows

### 5.1 Appointment Booking and Payment

1. The patient signs in.
2. The patient browses a hospital, department, or doctor.
3. The patient selects an appointment date and an available time.
4. The system displays the appointment information and applicable fee.
5. The patient confirms the booking request.
6. The system revalidates availability and submits the booking request to the authoritative scheduling service.
7. The system displays the resulting booking status and reference.
8. If payment is required online, the patient proceeds to the payment gateway.
9. The platform receives and validates the payment result.
10. The patient can view the appointment and payment statuses.

The exact order of booking confirmation and payment depends on the hospital's business rules and integration capabilities. This must be confirmed before implementation.

### 5.2 Symptom-Based Recommendation

1. The user opens the symptom recommendation feature.
2. The user selects or enters symptoms.
3. The system evaluates the symptoms using predefined rules.
4. The system displays suggested specialties and a non-diagnostic disclaimer.
5. Where applicable, the system displays a warning to seek urgent care.
6. The user browses matching clinics, departments, or doctors.

### 5.3 Doctor Review

1. The patient opens a completed appointment.
2. The system checks whether the appointment is eligible for a review.
3. The patient submits a rating and optional comment.
4. The system validates the review and prevents duplicate submissions for the same appointment.
5. The review is displayed according to the moderation policy.

### 5.4 Check-in Status Synchronization

1. The patient opens an upcoming appointment.
2. The platform displays the booking reference and the latest status available.
3. Hospital staff performs check-in through the hospital ERP/HIS.
4. The hospital system updates the check-in status.
5. If integration is available, the platform receives or retrieves the updated status and displays it to the patient.

---

## 6. Business Rules

| ID | Business rule |
|---|---|
| BR-01 | Only authenticated patients may create and manage their own appointments. |
| BR-02 | A booking is not considered confirmed until the authoritative booking service accepts it. |
| BR-03 | Appointment availability must be revalidated at submission time. |
| BR-04 | The system must prevent overlapping bookings according to the scheduling rules and capacity constraints. |
| BR-05 | Appointment duration and buffer time should be configurable rather than hard-coded. |
| BR-06 | Appointment cancellation must follow the applicable hospital or platform cancellation policy. |
| BR-07 | Payment status and appointment status must be represented separately. |
| BR-08 | A patient may review a doctor only after an eligible completed appointment. |
| BR-09 | A patient must not submit duplicate reviews for the same eligible appointment. |
| BR-10 | Symptom recommendations are informational and must not be presented as a diagnosis. |
| BR-11 | Check-in status must come from an authorized hospital workflow or integration, not from a patient self-declaration. |
| BR-12 | Patients may access only their own personal and appointment information. |
| BR-13 | Administrative functions must be restricted to authorized administrators. |

---

## 7. Status Definitions

### 7.1 Appointment status

The exact values should be aligned with the hospital ERP/HIS. A possible platform-level set is:

| Status | Meaning |
|---|---|
| Pending | Booking request has been submitted and is awaiting confirmation |
| Confirmed | Booking has been accepted by the authoritative booking system |
| Rejected | Booking request was not accepted |
| Cancelled | Appointment has been cancelled |
| Completed | Appointment has been marked as completed by the authorized hospital workflow |
| No-show | Patient did not attend, if this status is provided by the hospital |

### 7.2 Check-in status

| Status | Meaning |
|---|---|
| Not checked in | No check-in has been recorded |
| Checked in | Hospital workflow has recorded the patient's arrival |
| Unknown | The platform cannot obtain a reliable check-in status |

### 7.3 Payment status

| Status | Meaning |
|---|---|
| Unpaid | No successful payment has been recorded |
| Pending | Payment is being processed |
| Paid | A successful payment has been confirmed |
| Failed | The payment attempt failed |
| Refunded | A refund has been confirmed, if refunds are supported |

---

## 8. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Security | The system shall authenticate users and enforce role-based access control. |
| NFR-02 | Security | Passwords shall be stored using an appropriate secure password-hashing mechanism. |
| NFR-03 | Privacy | The system shall restrict access to personal and appointment information to authorized users. |
| NFR-04 | Privacy | The system shall collect and retain only information necessary for the platform's functions. |
| NFR-05 | Reliability | The system shall handle booking and payment failures without incorrectly reporting success. |
| NFR-06 | Consistency | The system shall validate booking availability at the time of submission and prevent duplicate reservations. |
| NFR-07 | Usability | The interface shall be responsive and usable on common desktop and mobile screen sizes. |
| NFR-08 | Performance | Common browsing and profile operations should return within an acceptable response time under the expected project workload. |
| NFR-09 | Maintainability | The system should separate user interface, business logic, data access, and external integration concerns. |
| NFR-10 | Auditability | Important actions, including booking status changes, payment updates, and administrative operations, should be logged. |
| NFR-11 | Interoperability | External hospital and payment integrations should use documented interfaces and validate received data. |
| NFR-12 | Availability | The system should provide clear error messages when an external integration is unavailable. |

---

## 9. Suggested Core Data Entities

The following entities are a starting point for database design. They do not prescribe a final schema.

| Entity | Purpose | Example attributes |
|---|---|---|
| User | Authentication and role information | UserId, Email, PasswordHash, Role, AccountStatus |
| PatientProfile | Patient details | PatientId, UserId, FullName, DateOfBirth, PhoneNumber |
| Hospital | Hospital directory information | HospitalId, Name, Address, Contact |
| Department | Hospital department or specialty | DepartmentId, HospitalId, Name, Description |
| Doctor | Doctor directory information | DoctorId, HospitalId, DepartmentId, Name, Qualifications, Experience |
| Appointment | Patient booking information | AppointmentId, PatientId, DoctorId, StartTime, EndTime, Status, BookingReference |
| AppointmentType | Appointment category and duration rules | AppointmentTypeId, Name, DefaultDuration |
| DoctorSchedule | Availability information, if maintained locally or cached | ScheduleId, DoctorId, StartTime, EndTime |
| Payment | Payment transaction information | PaymentId, AppointmentId, Amount, ProviderReference, Status |
| Review | Patient feedback | ReviewId, AppointmentId, PatientId, DoctorId, Rating, Comment |
| Symptom | Available symptom options | SymptomId, Name |
| SymptomSpecialtyRule | Rule mapping symptoms to specialties | RuleId, SymptomId, DepartmentId, Weight |
| Notification | Notification records | NotificationId, UserId, Type, Content, ReadAt |
| AuditLog | Important system activity | LogId, ActorId, Action, EntityType, EntityId, CreatedAt |

**Important design note:** If the hospital ERP/HIS is the source of truth for schedules and appointments, local schedule data may be a synchronized cache or temporary representation rather than an independent authoritative record. The implementation must make this boundary explicit.

---

## 10. Recommended MVP Scope

Given the limited development time, the following scope is recommended.

### 10.1 Must-have MVP

- Guest browsing of hospitals, departments, and doctors.
- Patient registration, login, and profile management.
- Doctor and specialty discovery.
- Basic symptom-to-specialty recommendations using predefined rules.
- Appointment booking with availability validation.
- Appointment list, details, and history.
- Online payment integration or a clearly identified payment-gateway sandbox.
- Doctor reviews for eligible completed appointments.
- Admin management of directory data and basic moderation.
- Basic appointment status display.
- Responsive web interface.

### 10.2 Simplified or conditional MVP features

- Check-in status: display it only if the hospital integration or mock service provides the status.
- QR code: optional display of a booking reference; do not implement a full scanning/check-in workflow unless required.
- Notifications: begin with in-app notifications; add email or other channels if time permits.
- Medical history: limit the MVP to appointment history. Do not implement a full EMR.

### 10.3 Future enhancements

- Native mobile applications.
- PWA capabilities and push notifications.
- QR-based hospital check-in integrated with the hospital system.
- More advanced scheduling optimization using historical appointment data.
- Predictive appointment-duration estimation after sufficient reliable data has been collected.
- AI/ML-assisted specialty navigation, subject to clinical review and appropriate safety controls.
- Deeper integration with hospital ERP/HIS systems.

---

## 11. Technical and Product Recommendations

1. **Build a responsive web application first.** This reduces development and maintenance effort compared with building separate native applications.
2. **Keep the hospital ERP/HIS boundary explicit.** Avoid recreating internal hospital workflows that already exist.
3. **Use rule-based symptom mapping for the MVP.** It is easier to implement, test, explain, and validate than an AI diagnosis feature.
4. **Use configurable duration-based scheduling.** Avoid assuming every appointment has a fixed duration.
5. **Treat payment and appointment status separately.** This avoids confusing a successful transaction with a confirmed booking.
6. **Implement integration adapters.** Keep hospital and payment gateway communication separate from core business logic so that mock services can be replaced later.
7. **Do not overbuild medical records.** Appointment history is sufficient for the current scope unless a real integration and explicit requirement exist.

---

## 12. Open Questions and Decisions Required

The following items should be clarified with the project supervisor, hospital representative, or team before implementation.

| ID | Question | Why it matters |
|---|---|---|
| OQ-01 | Is a real hospital ERP/HIS API available? | Determines whether schedules, bookings, and statuses can be synchronized or must be mocked. |
| OQ-02 | Which system is authoritative for appointment availability and confirmation? | Prevents conflicting or duplicate bookings. |
| OQ-03 | Does the hospital require payment before confirming a booking, or after confirmation? | Determines the booking and payment workflow. |
| OQ-04 | Who defines appointment duration, buffer time, and capacity? | These rules should reflect actual hospital operations. |
| OQ-05 | Which payment gateway will be used? | Determines payment API, callback validation, and sandbox requirements. |
| OQ-06 | Will symptom recommendations be reviewed by a healthcare professional? | Necessary to validate specialty mappings and warning-sign rules. |
| OQ-07 | Will the platform display only appointment history, or any additional medical information? | Controls privacy, integration complexity, and project scope. |
| OQ-08 | Which appointment and check-in statuses can the hospital provide? | Determines what the patient-facing platform can reliably display. |
| OQ-09 | What are the cancellation and refund policies? | Required to implement appointment and payment handling correctly. |

---

## 13. Glossary

| Term | Definition |
|---|---|
| ERP | Enterprise Resource Planning system used by an organization to manage internal processes. |
| HIS | Hospital Information System used to support hospital operations and information management. |
| EMR | Electronic Medical Record containing a patient's clinical information. |
| MVP | Minimum Viable Product: the smallest useful version of the product that can be delivered. |
| Appointment duration | The expected time reserved for a consultation or appointment. |
| Buffer time | Additional time reserved between appointments to accommodate operational needs. |
| Source of truth | The authoritative system responsible for maintaining the correct version of particular data. |
| Payment gateway | An external service that processes online payment transactions. |

---

**End of Document**