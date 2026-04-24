import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { useAuthStore } from '../lib/store'
import { Plus, Copy, Map, Sparkles, Sword, Scroll, Globe, ArrowRight, Trash2 } from 'lucide-react'

interface Campaign {
  id: number
  name: string
  description: string
  join_code: string
  owner_id: number
}

export default function Dashboard() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newCampaign, setNewCampaign] = useState({ name: '', description: '' })
  const [joinCode, setJoinCode] = useState('')
  const [error, setError] = useState('')
  const { user } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    loadCampaigns()
  }, [])

  const loadCampaigns = async () => {
    try {
      const response = await api.get('/campaigns/')
      setCampaigns(response.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const createCampaign = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const response = await api.post('/campaigns/', newCampaign)
      setCampaigns([...campaigns, response.data])
      setShowCreate(false)
      setNewCampaign({ name: '', description: '' })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create campaign')
    }
  }

  const joinCampaign = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.post(`/campaigns/join/${joinCode}`)
      loadCampaigns()
      setJoinCode('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to join campaign')
    }
  }

  const deleteCampaign = async (id: number, e: React.MouseEvent) => {
    e.preventDefault()
    if (!confirm('Are you sure you want to delete this campaign? This action cannot be undone.')) return
    try {
      await api.delete(`/campaigns/${id}`)
      setCampaigns(campaigns.filter(c => c.id !== id))
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete campaign')
    }
  }

  const copyJoinCode = (code: string) => {
    navigator.clipboard.writeText(code)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold">
            <span className="text-primary">Adventures</span>
          </h1>
          <p className="text-textMuted mt-1">
            Welcome back, {user?.username}. Continue your quest or start a new one.
          </p>
        </div>
        <button 
          onClick={() => setShowCreate(true)} 
          className="btn-primary flex items-center gap-2 glow-purple"
        >
          <Sparkles className="w-4 h-4" />
          New Campaign
        </button>
      </div>

      {/* Quick Actions */}
      <div className="grid md:grid-cols-2 gap-4">
        <button 
          onClick={() => navigate('/character/create/0')}
          className="card p-6 text-left hover:border-primary group"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center group-hover:bg-primary/30 transition-colors">
              <Sword className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold text-lg">Create Character</h3>
              <p className="text-textMuted text-sm">Build a new hero for your adventure</p>
            </div>
          </div>
        </button>
        
        <div className="card p-6">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-12 h-12 rounded-xl bg-accent/20 flex items-center justify-center">
              <Scroll className="w-6 h-6 text-accent" />
            </div>
            <div>
              <h3 className="font-semibold text-lg">Join Campaign</h3>
              <p className="text-textMuted text-sm">Enter a campaign code</p>
            </div>
          </div>
          <form onSubmit={joinCampaign} className="flex gap-2">
            <input
              type="text"
              placeholder="CODE123"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
              className="input font-mono"
              maxLength={6}
            />
            <button type="submit" className="btn-primary px-4">
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/20 text-danger px-4 py-3 rounded-lg flex items-center gap-2">
          <Sparkles className="w-4 h-4" />
          {error}
        </div>
      )}

      {showCreate && (
        <div className="card p-6 space-y-4">
          <div className="flex items-center gap-3">
            <Sparkles className="w-5 h-5 text-primary" />
            <h2 className="font-display text-xl font-semibold">Create New Campaign</h2>
          </div>
          <form onSubmit={createCampaign} className="space-y-4">
            <input
              type="text"
              placeholder="Campaign Name"
              value={newCampaign.name}
              onChange={(e) => setNewCampaign({ ...newCampaign, name: e.target.value })}
              className="input"
              required
            />
            <textarea
              placeholder="Description (optional)"
              value={newCampaign.description}
              onChange={(e) => setNewCampaign({ ...newCampaign, description: e.target.value })}
              className="input min-h-[100px]"
            />
            <div className="flex gap-2">
              <button type="submit" className="btn-primary">Create</button>
              <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
            </div>
          </form>
        </div>
      )}

      {/* Campaign Grid */}
      <div>
        <h2 className="font-display text-xl font-semibold mb-4 flex items-center gap-2">
          <Globe className="w-5 h-5 text-primary" />
          Your Campaigns
        </h2>
        
        {campaigns.length === 0 ? (
          <div className="text-center py-16 bg-surface rounded-xl border border-dashed border-border">
            <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-surfaceHover flex items-center justify-center">
              <Map className="w-10 h-10 text-textMuted" />
            </div>
            <p className="text-lg text-textMuted">No campaigns yet</p>
            <p className="text-sm text-textMuted mt-2">Create one to start your adventure!</p>
            <button 
              onClick={() => setShowCreate(true)}
              className="btn-primary mt-4"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Campaign
            </button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {campaigns.map((campaign) => (
              <Link
                key={campaign.id}
                to={`/campaign/${campaign.id}`}
                className="card p-5 hover:border-primary group relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-bl from-primary/10 to-transparent" />
                <div className="flex items-start justify-between mb-3 relative">
                  <h3 className="font-display text-lg font-semibold group-hover:text-primary transition-colors">
                    {campaign.name}
                  </h3>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        copyJoinCode(campaign.join_code)
                      }}
                      className="text-textMuted hover:text-primary transition-colors"
                      title="Copy join code"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                    {user?.id === campaign.owner_id && (
                      <button
                        onClick={(e) => deleteCampaign(campaign.id, e)}
                        className="text-textMuted hover:text-red-400 transition-colors"
                        title="Delete campaign"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
                {campaign.description && (
                  <p className="text-textMuted text-sm mb-3 line-clamp-2">{campaign.description}</p>
                )}
                <div className="flex items-center justify-between text-sm">
                  <span className="font-mono text-xs bg-surfaceHover px-2 py-1 rounded">
                    {campaign.join_code}
                  </span>
                  <ArrowRight className="w-4 h-4 text-textMuted group-hover:text-primary transition-colors" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}