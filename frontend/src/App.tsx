import { Route, Routes } from 'react-router-dom'
import { RequireAuth } from './auth/RequireAuth'
import { Layout } from './components/Layout'
import AdminDashboardPage from './pages/admin/AdminDashboardPage'
import AdminDirectoryPage from './pages/admin/AdminDirectoryPage'
import AdminRefundsPage from './pages/admin/AdminRefundsPage'
import AdminReviewsPage from './pages/admin/AdminReviewsPage'
import AdminSchedulesPage from './pages/admin/AdminSchedulesPage'
import AdminUsersPage from './pages/admin/AdminUsersPage'
import AppointmentDetailPage from './pages/AppointmentDetailPage'
import AppointmentsPage from './pages/AppointmentsPage'
import DepartmentDetailPage from './pages/DepartmentDetailPage'
import DepartmentsPage from './pages/DepartmentsPage'
import DoctorDetailPage from './pages/DoctorDetailPage'
import DoctorsPage from './pages/DoctorsPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import HomePage from './pages/HomePage'
import HospitalDetailPage from './pages/HospitalDetailPage'
import HospitalsPage from './pages/HospitalsPage'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import NotificationsPage from './pages/NotificationsPage'
import PaymentPage from './pages/PaymentPage'
import ProfilePage from './pages/ProfilePage'
import RegisterPage from './pages/RegisterPage'
import SymptomCheckerPage from './pages/SymptomCheckerPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        {/* Guest-accessible (FRD section 2) */}
        <Route index element={<HomePage />} />
        <Route path="hospitals" element={<HospitalsPage />} />
        <Route path="hospitals/:hospitalId" element={<HospitalDetailPage />} />
        <Route path="departments" element={<DepartmentsPage />} />
        <Route path="departments/:departmentId" element={<DepartmentDetailPage />} />
        <Route path="doctors" element={<DoctorsPage />} />
        <Route path="doctors/:doctorId" element={<DoctorDetailPage />} />
        <Route path="symptoms" element={<SymptomCheckerPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="forgot-password" element={<ForgotPasswordPage />} />

        {/* Patient-only (BR-01, BR-12) */}
        <Route element={<RequireAuth role="PATIENT" />}>
          <Route path="profile" element={<ProfilePage />} />
          <Route path="appointments" element={<AppointmentsPage />} />
          <Route path="appointments/:appointmentId" element={<AppointmentDetailPage />} />
          <Route path="payments/:paymentId" element={<PaymentPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
        </Route>

        {/* Admin-only (BR-13) */}
        <Route path="admin" element={<RequireAuth role="ADMIN" />}>
          <Route index element={<AdminDashboardPage />} />
          <Route path="directory" element={<AdminDirectoryPage />} />
          <Route path="schedules" element={<AdminSchedulesPage />} />
          <Route path="users" element={<AdminUsersPage />} />
          <Route path="reviews" element={<AdminReviewsPage />} />
          <Route path="refunds" element={<AdminRefundsPage />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
