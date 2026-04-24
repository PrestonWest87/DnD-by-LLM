import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../lib/store'
import { LogOut, Sword, Map, Users, Shield, User } from 'lucide-react'

export default function Layout() {
  const { user, profile } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const logout = useAuthStore(state => state.logout)

  return (
    <div className="min-h-screen bg-background">
      <header className="glass sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <Sword className="w-8 h-8 text-primary" />
            <span className="font-display text-xl font-bold">DragonForge</span>
          </Link>

          <nav className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2 text-textMuted hover:text-text transition-colors">
              <Map className="w-4 h-4" />
              <span>Campaigns</span>
            </Link>
            {user?.is_admin && (
              <Link to="/admin" className="flex items-center gap-2 text-textMuted hover:text-text transition-colors">
                <Shield className="w-4 h-4" />
                <span>Admin</span>
              </Link>
            )}
            {user && (
              <div className="flex items-center gap-4">
                <Link
                  to="/profile"
                  className="flex items-center gap-2 text-textMuted hover:text-text transition-colors"
                >
                  {profile?.avatar_url ? (
                    <img
                      src={profile.avatar_url}
                      alt={profile.display_name || user.username}
                      className="w-8 h-8 rounded-full object-cover"
                    />
                  ) : (
                    <User className="w-4 h-4" />
                  )}
                  <span>{profile?.display_name || user.username}</span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 text-textMuted hover:text-danger transition-colors"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}