import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../lib/store'
import api from '../lib/api'
import { User, Save, LogOut } from 'lucide-react'

interface Profile {
  id: number
  display_name: string
  avatar_url: string
  theme: string
  preferences: Record<string, any>
}

export default function Profile() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [formData, setFormData] = useState({
    display_name: '',
    avatar_url: '',
    theme: 'dark'
  })

  useEffect(() => {
    fetchProfile()
  }, [])

  const fetchProfile = async () => {
    try {
      const response = await fetch('/api/profile', {
        headers: { Authorization: `Bearer ${useAuthStore.getState().token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setProfileState(data)
        setFormData({
          display_name: data.display_name || '',
          avatar_url: data.avatar_url || '',
          theme: data.theme || 'dark'
        })
      }
    } catch (err) {
      console.error('Failed to fetch profile:', err)
    } finally {
      setLoading(false)
    }
  }

  const saveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      await api.patch('/profile', formData)
      setSuccess('Profile updated successfully!')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update profile')
    } finally {
      setSaving(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setSuccess('')

    try {
      const token = useAuthStore.getState().token
      const response = await fetch('/api/profile', {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      })

      if (response.ok) {
        const data = await response.json()
        setProfileState(data)
        setSuccess('Profile updated successfully!')
      } else {
        const data = await response.json()
        setError(data.detail || 'Failed to update profile')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update profile')
    } finally {
      setSaving(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <User className="w-8 h-8 text-primary" />
          <h1 className="font-display text-3xl font-bold">Profile Settings</h1>
        </div>
        <button
          onClick={handleLogout}
          className="btn-secondary flex items-center gap-2 text-danger hover:text-danger"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/20 text-danger px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-success/10 border border-success/20 text-success px-4 py-3 rounded-lg">
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} className="card p-6 space-y-6">
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm text-textMuted">Username</label>
            <input
              type="text"
              value={user?.username || ''}
              disabled
              className="input bg-surfaceHover"
            />
            <p className="text-xs text-textMuted">Username cannot be changed</p>
          </div>

          <div className="space-y-2">
            <label className="text-sm text-textMuted">Display Name</label>
            <input
              type="text"
              value={formData.display_name}
              onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              placeholder="How others see you"
              className="input"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm text-textMuted">Avatar URL</label>
            <input
              type="url"
              value={formData.avatar_url}
              onChange={(e) => setFormData({ ...formData, avatar_url: e.target.value })}
              placeholder="https://example.com/avatar.jpg"
              className="input"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm text-textMuted">Theme</label>
            <select
              value={formData.theme}
              onChange={(e) => setFormData({ ...formData, theme: e.target.value })}
              className="input"
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
              <option value="auto">Auto (System)</option>
            </select>
          </div>
        </div>

        <button type="submit" className="btn-primary flex items-center gap-2" disabled={saving}>
          <Save className="w-4 h-4" />
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </form>

      <div className="card p-6">
        <h2 className="font-display text-xl font-semibold mb-4">Account Info</h2>
        <div className="space-y-2 text-textMuted">
          <p>Email: {user?.email}</p>
          <p>Admin: {user?.is_admin ? 'Yes' : 'No'}</p>
        </div>
      </div>
    </div>
  )
}