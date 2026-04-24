import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { Plus, Users, Crown, Copy, Trash2, Map } from 'lucide-react'

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
      <div className="flex items-center justify-between">
        <h1 className="font-display text-3xl font-bold">Your Campaigns</h1>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          New Campaign
        </button>
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/20 text-danger px-4 py-2 rounded-lg">
          {error}
        </div>
      )}

      {showCreate && (
        <div className="card p-6 space-y-4">
          <h2 className="font-display text-xl font-semibold">Create New Campaign</h2>
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

      <div className="card p-6">
        <h2 className="font-display text-xl font-semibold mb-4">Join Campaign</h2>
        <form onSubmit={joinCampaign} className="flex gap-2">
          <input
            type="text"
            placeholder="Enter join code"
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
            className="input max-w-xs"
            required
          />
          <button type="submit" className="btn-primary">Join</button>
        </form>
      </div>

      {campaigns.length === 0 ? (
        <div className="text-center py-12 text-textMuted">
          <Map className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p>No campaigns yet. Create one to start your adventure!</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {campaigns.map((campaign) => (
            <Link
              key={campaign.id}
              to={`/campaign/${campaign.id}`}
              className="card p-6 hover:border-primary group"
            >
              <div className="flex items-start justify-between mb-4">
                <h3 className="font-display text-xl font-semibold group-hover:text-primary transition-colors">
                  {campaign.name}
                </h3>
                <button
                  onClick={(e) => {
                    e.preventDefault()
                    copyJoinCode(campaign.join_code)
                  }}
                  className="text-textMuted hover:text-primary"
                  title="Copy join code"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
              {campaign.description && (
                <p className="text-textMuted text-sm mb-4 line-clamp-2">{campaign.description}</p>
              )}
              <div className="flex items-center gap-2 text-textMuted text-sm">
                <span className="font-mono text-xs bg-surfaceHover px-2 py-1 rounded">{campaign.join_code}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}