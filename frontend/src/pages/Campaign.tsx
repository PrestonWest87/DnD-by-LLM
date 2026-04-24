import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import api from '../lib/api'
import { Users, Crown, Map, Plus, Play, Settings, Copy, BookOpen, Bot, User } from 'lucide-react'

interface Campaign {
  id: number
  name: string
  description: string
  join_code: string
  owner_id: number
  story_outline: string
  dm_mode: string
  llm_model: string
}

interface Member {
  id: number
  user_id: number
  role: string
  username: string
}

interface Character {
  id: number
  name: string
  race: string
  class_name: string
  level: number
}

export default function Campaign() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [members, setMembers] = useState<Member[]>([])
  const [characters, setCharacters] = useState<Character[]>([])
  const [loading, setLoading] = useState(true)
  const [showRooms, setShowRooms] = useState(false)
  const [rooms, setRooms] = useState<any[]>([])
  const [newRoomName, setNewRoomName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [dmMode, setDmMode] = useState(campaign?.dm_mode || 'ai')
  const [llmModel, setLlmModel] = useState(campaign?.llm_model || '')

  useEffect(() => {
    loadData()
  }, [id])

  const loadData = async () => {
    setError(null)
    try {
      const [campaignRes, membersRes, charsRes] = await Promise.all([
        api.get(`/campaigns/${id}`),
        api.get(`/campaigns/${id}/members`),
        api.get(`/characters/campaign/${id}`)
      ])
      setCampaign(campaignRes.data)
      setMembers(membersRes.data)
      setCharacters(charsRes.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load campaign data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const loadRooms = async () => {
    setError(null)
    try {
      const response = await api.get(`/rooms/campaign/${id}`)
      setRooms(response.data)
      setShowRooms(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load rooms')
      console.error(err)
    }
  }

  const createRoom = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const response = await api.post('/rooms/', { campaign_id: id, name: newRoomName })
      setRooms([...rooms, response.data])
      setNewRoomName('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create room. Only DMs can create rooms.')
      console.error(err)
    }
  }

  const generateStoryOutline = async () => {
    setError(null)
    try {
      const response = await api.post('/dm/generate-story-outline', {
        campaign_id: id,
        theme: 'Epic Fantasy',
        tone: 'Serious with moments of humor',
        players: members.map(m => m.username)
      })
      setCampaign({ ...campaign!, story_outline: response.data.outline })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate story outline. Only campaign DMs can generate outlines.')
      console.error(err)
    }
  }

  const startSession = async () => {
    if (!campaign?.story_outline) {
      setError('Generate a story outline first before starting a session.')
      return
    }
    setError(null)
    try {
      const res = await api.post(`/campaigns/${id}/start-session`, { title: 'Session 1' })
      setCampaign({ ...campaign!, status: 'in_progress' })
      const roomsRes = await api.get(`/rooms/campaign/${id}`)
      if (roomsRes.data.length > 0) {
        navigate(`/campaign/${id}/room/${roomsRes.data[0].id}`)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start session')
      console.error(err)
    }
  }

  const updateSettings = async () => {
    setError(null)
    try {
      await api.patch(`/campaigns/${id}`, {
        dm_mode: dmMode,
        llm_model: llmModel
      })
      setCampaign({ ...campaign!, dm_mode: dmMode, llm_model: llmModel })
      setShowSettings(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update settings')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!campaign) {
    return <div>Campaign not found</div>
  }

  return (
    <div className="space-y-8">
      {error && (
        <div className="bg-danger/10 border border-danger/20 text-danger px-4 py-3 rounded-lg">
          {error}
        </div>
      )}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold">{campaign.name}</h1>
          <button
            onClick={() => navigator.clipboard.writeText(campaign.join_code)}
            className="flex items-center gap-2 text-textMuted mt-2 hover:text-primary"
          >
            <Copy className="w-4 h-4" />
            Join Code: <span className="font-mono">{campaign.join_code}</span>
          </button>
        </div>
        <div className="flex gap-2">
          <button onClick={loadRooms} className="btn-secondary flex items-center gap-2">
            <Play className="w-4 h-4" />
            Play
          </button>
          <Link to={`/character/create/${id}`} className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" />
            New Character
          </Link>
        </div>
      </div>

      {campaign.description && (
        <p className="text-textMuted">{campaign.description}</p>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-primary" />
            <h2 className="font-display text-xl font-semibold">Party Members</h2>
          </div>
          {members.length === 0 ? (
            <p className="text-textMuted">No members yet</p>
          ) : (
            <div className="space-y-3">
              {members.map((member) => (
                <div key={member.id} className="flex items-center justify-between">
                  <div>
                    <span className="font-medium">{member.username}</span>
                    {member.role === 'dm' && (
                      <span className="ml-2 text-xs bg-accent/20 text-accent px-2 py-0.5 rounded flex items-center gap-1 inline-flex">
                        <Crown className="w-3 h-3" />
                        DM
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Map className="w-5 h-5 text-primary" />
            <h2 className="font-display text-xl font-semibold">Characters</h2>
          </div>
          {characters.length === 0 ? (
            <p className="text-textMuted">No characters yet</p>
          ) : (
            <div className="space-y-3">
              {characters.map((char) => (
                <Link
                  key={char.id}
                  to={`/campaign/${id}/character/${char.id}`}
                  className="block p-3 bg-surfaceHover rounded-lg hover:bg-border transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{char.name}</span>
                    <span className="text-textMuted text-sm">Level {char.level}</span>
                  </div>
                  <span className="text-textMuted text-sm">
                    {char.race} {char.class_name}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {showRooms && (
        <div className="card p-6">
          <h2 className="font-display text-xl font-semibold mb-4">Game Rooms</h2>
          <form onSubmit={createRoom} className="flex gap-2 mb-4">
            <input
              type="text"
              placeholder="Room name"
              value={newRoomName}
              onChange={(e) => setNewRoomName(e.target.value)}
              className="input max-w-xs"
              required
            />
            <button type="submit" className="btn-primary">Create Room</button>
          </form>
          {rooms.length === 0 ? (
            <p className="text-textMuted">No rooms yet</p>
          ) : (
            <div className="space-y-2">
              {rooms.map((room) => (
                <div
                  key={room.id}
                  className="flex items-center justify-between p-3 bg-surfaceHover rounded-lg"
                >
                  <div>
                    <span className="font-medium">{room.name}</span>
                    <span className="text-textMuted text-sm ml-4">
                      Code: {room.join_code}
                    </span>
                  </div>
                  <Link
                    to={`/campaign/${id}/room/${room.id}`}
                    className="btn-primary text-sm"
                  >
                    Join
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

<div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Settings className="w-5 h-5 text-primary" />
              <h2 className="font-display text-xl font-semibold">Campaign Settings</h2>
            </div>
            <button onClick={() => setShowSettings(!showSettings)} className="btn-secondary text-sm">
              {showSettings ? 'Hide' : 'Edit'}
            </button>
          </div>
          
          {showSettings && (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm text-textMuted">DM Mode</label>
                <select
                  value={dmMode}
                  onChange={(e) => setDmMode(e.target.value)}
                  className="input w-full"
                >
                  <option value="ai">AI Dungeon Master</option>
                  <option value="human">Human Dungeon Master</option>
                  <option value="hybrid">Hybrid (AI assists)</option>
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm text-textMuted">LLM Model</label>
                <input
                  type="text"
                  value={llmModel}
                  onChange={(e) => setLlmModel(e.target.value)}
                  placeholder={campaign?.llm_model || "qwen2.5:7b"}
                  className="input w-full"
                />
              </div>
              <button onClick={updateSettings} className="btn-primary">
                Save Settings
              </button>
            </div>
          )}
        </div>

        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="w-5 h-5 text-primary" />
            <h2 className="font-display text-xl font-semibold">RAG Content</h2>
          </div>
          <Link to={`/campaign/${id}/rag`} className="btn-primary">
            Manage Rules & Content
          </Link>
        </div>

        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Settings className="w-5 h-5 text-primary" />
            <h2 className="font-display text-xl font-semibold">Story Outline</h2>
          </div>
        {campaign.story_outline ? (
          <div className="prose prose-invert max-w-none">
            <p className="whitespace-pre-wrap">{campaign.story_outline}</p>
            {campaign.status !== 'in_progress' && (
              <button onClick={startSession} className="btn-primary mt-4">
                Start Session
              </button>
            )}
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-textMuted mb-4">No story outline yet</p>
            <button onClick={generateStoryOutline} className="btn-primary">
              Generate Story Outline
            </button>
          </div>
        )}
      </div>
    </div>
  )
}