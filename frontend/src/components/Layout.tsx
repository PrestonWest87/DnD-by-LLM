import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../lib/store'
import { LogOut, Sword, Map, Users, Shield, User, Sparkles } from 'lucide-react'

export default function Layout() {
  const { user, profile } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const logout = useAuthStore(state => state.logout)

  return (
    <div className="h-screen flex flex-col bg-background grid-bg overflow-hidden">
      <header className="glass sticky top-0 z-50 border-b border-border/50 shrink-0">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative">
              <Sword className="w-8 h-8 text-primary transition-transform group-hover:rotate-12" />
              <Sparkles className="w-3 h-3 absolute -top-1 -right-1 text-accent animate-pulse" />
            </div>
            <span className="font-display text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              DragonForge
            </span>
          </Link>

          <nav className="flex items-center gap-6">
            <Link 
              to="/" 
              className="flex items-center gap-2 text-textMuted hover:text-text transition-colors hover:scale-105"
            >
              <Map className="w-4 h-4" />
              <span>Campaigns</span>
            </Link>
            <Link 
              to="/character/create/0"
              className="flex items-center gap-2 text-textMuted hover:text-text transition-colors hover:scale-105"
            >
              <Users className="w-4 h-4" />
              <span>Create</span>
            </Link>
            {user?.is_admin && (
              <Link 
                to="/admin" 
                className="flex items-center gap-2 text-textMuted hover:text-danger transition-colors hover:scale-105"
              >
                <Shield className="w-4 h-4" />
                <span>Admin</span>
              </Link>
            )}
            {user && (
              <div className="flex items-center gap-4 border-l border-border pl-4">
                <Link
                  to="/profile"
                  className="flex items-center gap-3 text-textMuted hover:text-text transition-all hover:scale-105"
                >
                  {profile?.avatar_url ? (
                    <img
                      src={profile.avatar_url}
                      alt={profile.display_name || user.username}
                      className="w-8 h-8 rounded-full object-cover ring-2 ring-border"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-surface flex items-center justify-center ring-2 ring-border">
                      <User className="w-4 h-4 text-primary" />
                    </div>
                  )}
                  <span className="hidden md:inline">{profile?.display_name || user.username}</span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 text-textMuted hover:text-danger transition-all hover:scale-105"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </nav>
        </div>
      </header>

      <main className="flex-1 overflow-hidden p-0">
        <Outlet />
      </main>
    </div>
  )
}