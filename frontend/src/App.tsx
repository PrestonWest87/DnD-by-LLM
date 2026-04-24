import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './lib/store'
import { useEffect } from 'react'
import Layout from './components/Layout'
import api from './lib/api'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Campaign from './pages/Campaign'
import GameRoom from './pages/GameRoom'
import CharacterCreator from './pages/CharacterCreator'
import CharacterDetail from './pages/CharacterDetail'
import MapEditor from './pages/MapEditor'
import AdminPanel from './pages/AdminPanel'
import Profile from './pages/Profile'
import RAGManager from './pages/RAGManager'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore()
  return token ? <>{children}</> : <Navigate to="/login" />
}

export default function App() {
  const { token, fetchProfile, setUser } = useAuthStore()

  useEffect(() => {
    if (token) {
      fetchProfile().catch(() => {})
      api.get('/auth/me').then(r => setUser(r.data)).catch(() => {})
    }
  }, [])

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={
        <PrivateRoute>
          <Layout />
        </PrivateRoute>
      }>
        <Route index element={<Dashboard />} />
        <Route path="campaign/:id" element={<Campaign />} />
        <Route path="campaign/:id/room/:roomId" element={<GameRoom />} />
        <Route path="character/create/:campaignId" element={<CharacterCreator />} />
        <Route path="campaign/:id/character/:characterId" element={<CharacterDetail />} />
        <Route path="campaign/:id/map/:mapId" element={<MapEditor />} />
        <Route path="admin" element={<AdminPanel />} />
        <Route path="profile" element={<Profile />} />
        <Route path="campaign/:id/rag" element={<RAGManager />} />
      </Route>
    </Routes>
  )
}