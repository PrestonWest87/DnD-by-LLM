import { useState, useEffect } from 'react'
import { useAuthStore } from '../lib/store'
import { Shield, Trash2, RefreshCw, Users, AlertTriangle, Server, Database, Activity } from 'lucide-react'

interface User {
  id: number
  username: string
  email: string
  is_admin: boolean
  created_at: string
}

interface SystemStats {
  total_users: number
  total_campaigns: number
  active_sessions: number
}

interface OllamaModel {
  name: string
  size?: number
}

export default function AdminPanel() {
  const { user: currentUser, token } = useAuthStore()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [newPassword, setNewPassword] = useState('')
  const [activeTab, setActiveTab] = useState<'users' | 'system'>('users')
  
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [ollamaUrl, setOllamaUrl] = useState('')
  const [ollamaTestResult, setOllamaTestResult] = useState<{success: boolean, message: string, models?: OllamaModel[]} | null>(null)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    if (currentUser?.is_admin) {
      fetchUsers()
      fetchStats()
      fetchSettings()
    }
  }, [currentUser])

  const fetchUsers = async () => {
    try {
      const response = await fetch('/api/admin/users', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setUsers(data)
      }
    } catch (err) {
      console.error('Failed to fetch users:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/settings/stats', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  const fetchSettings = async () => {
    try {
      const response = await fetch('/api/settings', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setOllamaUrl(data.ollama_url || '')
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err)
    }
  }

  const testOllama = async () => {
    setTesting(true)
    setOllamaTestResult(null)
    try {
      const url = ollamaUrl || undefined
      const response = await fetch(`/api/settings/ollama/test?${url ? `url=${encodeURIComponent(url)}` : ''}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      const data = await response.json()
      setOllamaTestResult(data)
    } catch (err: any) {
      setOllamaTestResult({ success: false, message: err.message })
    } finally {
      setTesting(false)
    }
  }

  const handleDelete = async (userId: number) => {
    if (!confirm('Are you sure you want to delete this user?')) return
    
    try {
      const response = await fetch(`/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.ok) {
        setUsers(users.filter(u => u.id !== userId))
      }
    } catch (err) {
      setError('Failed to delete user')
    }
  }

  const handleResetPassword = async () => {
    if (!selectedUser || !newPassword) return

    try {
      const response = await fetch(
        `/api/admin/users/${selectedUser.id}/reset-password?new_password=${encodeURIComponent(newPassword)}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` }
        }
      )
      if (response.ok) {
        alert('Password reset successfully')
        setSelectedUser(null)
        setNewPassword('')
      }
    } catch (err) {
      setError('Failed to reset password')
    }
  }

  const toggleAdmin = async (user: User) => {
    try {
      const response = await fetch(`/api/admin/users/${user.id}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ is_admin: !user.is_admin })
      })
      if (response.ok) {
        fetchUsers()
      }
    } catch (err) {
      setError('Failed to update user')
    }
  }

  if (!currentUser?.is_admin) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-16 h-16 text-danger mx-auto mb-4" />
          <h1 className="text-2xl font-bold">Access Denied</h1>
          <p className="text-textMuted mt-2">You don't have admin access</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <Shield className="w-8 h-8 text-primary" />
          <h1 className="text-3xl font-bold">Admin Panel</h1>
        </div>

        <div className="flex gap-4 mb-6 border-b border-border">
          <button
            onClick={() => setActiveTab('users')}
            className={`pb-3 px-4 flex items-center gap-2 ${activeTab === 'users' ? 'border-b-2 border-primary text-primary' : 'text-textMuted'}`}
          >
            <Users className="w-4 h-4" />
            Users
          </button>
          <button
            onClick={() => setActiveTab('system')}
            className={`pb-3 px-4 flex items-center gap-2 ${activeTab === 'system' ? 'border-b-2 border-primary text-primary' : 'text-textMuted'}`}
          >
            <Server className="w-4 h-4" />
            System
          </button>
        </div>

        {error && (
          <div className="bg-danger/10 border border-danger/20 text-danger px-4 py-2 rounded-lg mb-4">
            {error}
          </div>
        )}

        {activeTab === 'users' && (
          <>
            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Users className="w-5 h-5" />
                  <h2 className="text-xl font-semibold">User Management</h2>
                </div>
                <div className="flex items-center gap-4 text-sm text-textMuted">
                  <span className="flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    {users.length} users
                  </span>
                </div>
              </div>

              {loading ? (
                <p className="text-textMuted">Loading...</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-3 px-4">Username</th>
                        <th className="text-left py-3 px-4">Email</th>
                        <th className="text-left py-3 px-4">Role</th>
                        <th className="text-left py-3 px-4">Created</th>
                        <th className="text-left py-3 px-4">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map(user => (
                        <tr key={user.id} className="border-b border-border">
                          <td className="py-3 px-4">{user.username}</td>
                          <td className="py-3 px-4">{user.email}</td>
                          <td className="py-3 px-4">
                            {user.is_admin ? (
                              <span className="text-primary">Admin</span>
                            ) : (
                              <span className="text-textMuted">User</span>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            {new Date(user.created_at).toLocaleDateString()}
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex gap-2">
                              <button
                                onClick={() => toggleAdmin(user)}
                                className="p-2 hover:bg-primary/10 rounded-lg"
                                title={user.is_admin ? "Remove admin" : "Make admin"}
                              >
                                <Shield className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => setSelectedUser(user)}
                                className="p-2 hover:bg-primary/10 rounded-lg"
                                title="Reset password"
                              >
                                <RefreshCw className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => handleDelete(user.id)}
                                className="p-2 hover:bg-danger/10 rounded-lg text-danger"
                                title="Delete user"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {selectedUser && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4">
                <div className="card p-6 max-w-md w-full">
                  <h3 className="text-xl font-semibold mb-4">
                    Reset Password for {selectedUser.username}
                  </h3>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="New password"
                    className="input w-full mb-4"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={handleResetPassword}
                      className="btn-primary flex-1"
                    >
                      Reset Password
                    </button>
                    <button
                      onClick={() => { setSelectedUser(null); setNewPassword('') }}
                      className="btn-secondary flex-1"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {activeTab === 'system' && (
          <div className="space-y-6">
            <div className="grid md:grid-cols-3 gap-4">
              <div className="card p-6">
                <div className="flex items-center gap-2 mb-2">
                  <Users className="w-5 h-5 text-primary" />
                  <h3 className="font-semibold">Total Users</h3>
                </div>
                <p className="text-3xl font-bold">{stats?.total_users || 0}</p>
              </div>
              <div className="card p-6">
                <div className="flex items-center gap-2 mb-2">
                  <Database className="w-5 h-5 text-primary" />
                  <h3 className="font-semibold">Campaigns</h3>
                </div>
                <p className="text-3xl font-bold">{stats?.total_campaigns || 0}</p>
              </div>
              <div className="card p-6">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="w-5 h-5 text-primary" />
                  <h3 className="font-semibold">Active Sessions</h3>
                </div>
                <p className="text-3xl font-bold">{stats?.active_sessions || 0}</p>
              </div>
            </div>

            <div className="card p-6">
              <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Server className="w-5 h-5" />
                Ollama Configuration
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-textMuted">Ollama Base URL</label>
                  <input
                    type="text"
                    value={ollamaUrl}
                    onChange={(e) => setOllamaUrl(e.target.value)}
                    placeholder="http://ollama:11434"
                    className="input w-full"
                  />
                </div>

                <button
                  onClick={testOllama}
                  disabled={testing}
                  className="btn-secondary"
                >
                  {testing ? 'Testing...' : 'Test Connection'}
                </button>

                {ollamaTestResult && (
                  <div className={`p-4 rounded-lg ${ollamaTestResult.success ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'}`}>
                    <p>{ollamaTestResult.message}</p>
                    {ollamaTestResult.models && (
                      <div className="mt-2">
                        <p className="text-sm">Available models:</p>
                        <ul className="text-sm mt-1">
                          {ollamaTestResult.models.slice(0, 5).map((m, i) => (
                            <li key={i} className="ml-4">• {m.name}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}