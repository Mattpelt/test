import { Routes, Route, Navigate } from 'react-router-dom'

import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'
import KioskPage from './pages/KioskPage'
import OnboardingPage from './pages/OnboardingPage'
import PrivateRoute from './components/PrivateRoute'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/kiosk" element={<KioskPage />} />
      <Route path="/onboarding" element={<OnboardingPage />} />

      {/* Routes protégées — utilisateur connecté */}
      <Route element={<PrivateRoute />}>
        <Route path="/" element={<HomePage />} />
      </Route>

      {/* Toute autre URL → accueil */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
