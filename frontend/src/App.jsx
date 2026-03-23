import { Routes, Route, Navigate } from 'react-router-dom'

// Pages (à implémenter — Sprint 3)
import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'
import AdminPage from './pages/AdminPage'
import OnboardingPage from './pages/OnboardingPage'
import PrivateRoute from './components/PrivateRoute'
import AdminRoute from './components/AdminRoute'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/onboarding" element={<OnboardingPage />} />

      {/* Routes protégées — utilisateur connecté */}
      <Route element={<PrivateRoute />}>
        <Route path="/" element={<HomePage />} />
      </Route>

      {/* Routes admin */}
      <Route element={<AdminRoute />}>
        <Route path="/admin" element={<AdminPage />} />
      </Route>

      {/* Toute autre URL → accueil */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
