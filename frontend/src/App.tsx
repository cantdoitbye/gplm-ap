import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import Dashboard from './pages/Dashboard'
import PropertyDetection from './pages/PropertyDetection'
import ChangeDetection from './pages/ChangeDetection'
import Alerts from './pages/Alerts'
import MapView from './pages/MapView'
import Settings from './pages/Settings'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="detection" element={<PropertyDetection />} />
            <Route path="changes" element={<ChangeDetection />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="map" element={<MapView />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
