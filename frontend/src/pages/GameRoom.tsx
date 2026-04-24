import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { useAuthStore } from '../lib/store'
import { 
  Send, Dices, User, MessageSquare, Sword, Shield, Zap, Users,
  ChevronDown, Heart, Activity, Sparkles
} from 'lucide-react'

interface Message {
  id: number
  user_id: number
  character_id?: number
  content: string
  message_type: string
  timestamp: string
}

interface Character {
  id: number
  user_id: number
  name: string
  race: string
  class_name: string
  level: number
  hp: number
  max_hp: number
  ac: number
}

interface Encounter {
  id: number
  status: string
  current_turn: number
  round: number
  participants: Array<{
    id: number
    character_id: number
    hp_remaining: number
    turn_order: number
  }>
}

type ChatMode = 'action' | 'speak' | 'party' | 'dm'

export default function GameRoom() {
  const { id: campaignId, roomId } = useParams()
  const navigate = useNavigate()
  const { user: currentUser } = useAuthStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [characters, setCharacters] = useState<Character[]>([])
  const [selectedChar, setSelectedChar] = useState<number | null>(null)
  const [diceInput, setDiceInput] = useState('1d20')
  const [diceResults, setDiceResults] = useState<any[]>([])
  const [showDice, setShowDice] = useState(false)
  const [showInitiative, setShowInitiative] = useState(false)
  const [chatMode, setChatMode] = useState<ChatMode>('action')
  const [error, setError] = useState<string | null>(null)
  const [encounter, setEncounter] = useState<Encounter | null>(null)
  const [isReady, setIsReady] = useState(false)
  const [currentMap, setCurrentMap] = useState<any>(null)
  const [mapEntities, setMapEntities] = useState<any[]>([])

  const loadMessages = async () => {
    try {
      const response = await api.get(`/rooms/${roomId}/messages`)
      setMessages(response.data.reverse())
    } catch (err: any) {
      console.error('Failed to load messages:', err)
    }
  }

  const loadCharacters = async () => {
    try {
      const response = await api.get(`/characters/campaign/${campaignId}`)
      setCharacters(response.data)
    } catch (err) {
      console.error(err)
    }
  }

  const loadReadyStatus = async () => {
    if (!roomId || !selectedChar) return
    try {
      const response = await api.get(`/sessions/room/${roomId}/ready`)
      const readyStates = response.data.ready_states || []
      const myState = readyStates.find((r: any) => r.character_id === selectedChar)
      setIsReady(myState?.is_ready || false)
    } catch (err) {
      console.error('Failed to load ready status:', err)
    }
  }

  const loadEncounter = async () => {
    try {
      const response = await api.get(`/encounters/room/${roomId}`)
      if (response.data.encounter) {
        setEncounter(response.data)
        setShowInitiative(true)
      }
    } catch (err) {
      // No encounter exists
    }
  }

  const loadMap = async () => {
    try {
      const response = await api.get(`/rooms/${roomId}`)
      const roomData = response.data
      if (roomData.map_id) {
        const mapResponse = await api.get(`/maps/${roomData.map_id}`)
        setCurrentMap(mapResponse.data)
        const entitiesResponse = await api.get(`/maps/${roomData.map_id}/entities`)
        setMapEntities(entitiesResponse.data.entities || [])
      }
    } catch (err) {
      console.error('Failed to load map:', err)
    }
  }

  useEffect(() => {
    if (roomId) {
      loadMessages()
      loadCharacters()
      loadReadyStatus()
      loadEncounter()
      loadMap()
      const interval = setInterval(loadMessages, 3000)
      return () => clearInterval(interval)
    }
  }, [roomId])

  useEffect(() => {
    if (roomId && selectedChar) {
      loadReadyStatus()
    }
  }, [selectedChar, roomId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-select user's character when either characters or user changes
  useEffect(() => {
    if (characters.length > 0 && !selectedChar && currentUser) {
      const userChar = characters.find(c => c.user_id === currentUser.id)
      if (userChar) setSelectedChar(userChar.id)
    }
  }, [characters, currentUser, selectedChar])

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || !selectedChar) return

    setLoading(true)
    setInput('')

    try {
      if (chatMode === 'dm') {
        const response = await api.post('/dm/chat', {
          room_id: roomId,
          player_input: input,
          character_id: selectedChar
        })
        await loadMessages()
      } else {
        await api.post(`/rooms/${roomId}/messages`, {
          content: input,
          message_type: chatMode,
          character_id: selectedChar
        })
        await loadMessages()
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send message')
    } finally {
      setLoading(false)
    }
  }

  const getMessageStyle = (msg: Message) => {
    switch (msg.message_type) {
      case 'action': return 'bg-surfaceHover border-l-4 border-purple-500'
      case 'speak': return 'bg-surfaceHover border-l-4 border-blue-500'
      case 'party': return 'bg-surfaceHover border-l-4 border-green-500'
      case 'dm': return 'bg-primary/10 border-l-4 border-primary'
      default: return 'bg-surfaceHover'
    }
  }

  const getMessageIcon = (msg: Message) => {
    switch (msg.message_type) {
      case 'action': return <Sword className="w-3 h-3 text-purple-400" />
      case 'speak': return <MessageSquare className="w-3 h-3 text-blue-400" />
      case 'party': return <Users className="w-3 h-3 text-green-400" />
      case 'dm': return <Sparkles className="w-3 h-3 text-primary" />
      default: return null
    }
  }

  const getMessageLabel = (msg: Message) => {
    switch (msg.message_type) {
      case 'action': return 'Action'
      case 'speak': return 'Says'
      case 'party': return 'Party'
      case 'dm': return 'DM'
      default: return 'Player'
    }
  }

  const formatMessage = (content: string) => {
    let formatted = content
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>')
    formatted = formatted.replace(/`(.*?)`/g, '<code class="bg-gray-800 px-1 rounded text-purple-300">$1</code>')
    return formatted
  }

  const selectedCharacter = characters.find(c => c.id === selectedChar)
  const getCharacterById = (id: number) => characters.find(c => c.id === id)

  const getHpPercent = (current: number, max: number) => {
    if (!max) return 0
    return Math.max(0, Math.min(100, (current / max) * 100))
  }

  const getHpColor = (current: number, max: number) => {
    const percent = getHpPercent(current, max)
    if (percent > 66) return 'bg-green-500'
    if (percent > 33) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  return (
    <div className="flex flex-1 min-h-0 bg-surface overflow-hidden">
      {/* Map Area - 85% */}
      <div className="flex-[17] border-r border-border relative overflow-hidden">
        <div className="absolute inset-0 p-2">
          <div 
            className="w-full h-full relative rounded-lg overflow-hidden"
            style={{ 
              backgroundColor: '#0f0f1a',
              backgroundImage: 'linear-gradient(#1e1e3f 1px, transparent 1px), linear-gradient(90deg, #1e1e3f 1px, transparent 1px)',
              backgroundSize: '40px 40px'
            }}
          >
            {/* Render rooms as boxes */}
            {currentMap?.data?.rooms?.map((room: any, idx: number) => {
              const left = (room.x / (currentMap?.width || 50)) * 100
              const top = (room.y / (currentMap?.height || 50)) * 100
              const width = (room.width / (currentMap?.width || 50)) * 100
              const height = (room.height / (currentMap?.height || 50)) * 100
              
              return (
                <div
                  key={idx}
                  className="absolute border-2 border-purple-500/50 bg-purple-900/20 rounded flex items-center justify-center"
                  style={{
                    left: `${left}%`,
                    top: `${top}%`,
                    width: `${width}%`,
                    height: `${height}%`
                  }}
                  title={room.name}
                >
                  <span className="text-xs text-purple-300 px-1 text-center">{room.name}</span>
                </div>
              )
            })}
            
            {/* Render entities on map */}
            {mapEntities.map((entity) => {
              const getEntityColor = (type: string) => {
                if (type === 'player' || type === 'character') return 'bg-cyan-400'
                if (type === 'npc') return 'bg-purple-400'
                if (type === 'enemy' || type === 'monster') return 'bg-red-500'
                return 'bg-yellow-400'
              }
              return (
                <div
                  key={entity.id}
                  className={`absolute w-5 h-5 rounded-full ${getEntityColor(entity.entity_type)} border-2 border-white shadow-lg flex items-center justify-center z-10`}
                  style={{
                    left: `${(entity.x / (currentMap?.width || 50)) * 100}%`,
                    top: `${(entity.y / (currentMap?.height || 50)) * 100}%`,
                    transform: 'translate(-50%, -50%)'
                  }}
                  title={entity.name}
                >
                  <span className="text-[8px] text-white font-bold">
                    {entity.name?.charAt(0).toUpperCase()}
                  </span>
                </div>
              )
            })}
            
            {/* Map name overlay */}
            <div className="absolute top-2 left-2 bg-black/60 px-3 py-1 rounded text-white text-sm">
              {currentMap?.name || 'No Map - Click Ready to Generate'}
            </div>
          </div>
        </div>
        
        {/* Map controls */}
        <div className="absolute top-2 right-2 flex gap-1">
          <button className="p-2 bg-black/60 rounded hover:bg-black/80 text-white">
            <span className="text-xs">+</span>
          </button>
          <button className="p-2 bg-black/60 rounded hover:bg-black/80 text-white">
            <span className="text-xs">-</span>
          </button>
        </div>
      </div>
      
      {/* Right Sidebar - 15% */}
      <div className="w-[300px] flex flex-col min-h-0 border-l border-border">
        {/* Character + Ready Button */}
        <div className="p-3 border-b border-border">
          <div className="flex items-center gap-2 mb-2">
            <User className="w-4 h-4 text-primary" />
            <h3 className="font-semibold text-sm">Character</h3>
          </div>
          
          <div className="flex gap-2">
            <select
              value={selectedChar || ''}
              onChange={(e) => setSelectedChar(e.target.value ? Number(e.target.value) : null)}
              className="flex-1 input text-sm"
            >
              <option value="">Select...</option>
              {characters.map((char) => (
                <option key={char.id} value={char.id}>
                  {char.name}
                </option>
              ))}
            </select>
            
            <button
              type="button"
              onClick={async () => {
                if (selectedChar) {
                  try {
                    const res = await api.post(`/sessions/room/${roomId}/ready`, { character_id: selectedChar })
                    setIsReady(!isReady)
                    if (res.data.map_generated) {
                      loadMap()
                    }
                  } catch (err) {
                    console.error('Failed to toggle ready:', err)
                  }
                }
              }}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap flex items-center gap-1 ${
                isReady 
                  ? 'bg-green-600 text-white' 
                  : 'bg-surfaceHover text-yellow-400 hover:text-yellow-300'
              }`}
            >
              <Shield className="w-4 h-4" />
              {isReady ? 'Ready!' : 'Ready'}
            </button>
          </div>
        </div>
        
        {/* Chat Header */}
        <div className="px-4 py-2 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button 
              onClick={() => navigate(`/campaign/${campaignId}`)}
              className="p-1 hover:bg-surfaceHover rounded transition-colors"
            >
              <ChevronDown className="w-3 h-3 rotate-90" />
            </button>
            <h2 className="font-display font-bold text-sm">Chat</h2>
          </div>
        </div>

        {/* Messages - scrollable */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
          {messages.length === 0 && (
            <div className="text-center text-textMuted py-8">
              <p className="text-sm">No messages yet</p>
            </div>
          )}
          {messages.map((msg) => (
            <div 
              key={msg.id} 
              className={`p-3 rounded-lg text-sm ${getMessageStyle(msg)}`}
            >
              <div className="flex items-center gap-1 text-xs text-textMuted mb-1">
                {getMessageIcon(msg)}
                <span className="font-medium">{getMessageLabel(msg)}</span>
                {msg.character_id && (
                  <span className="text-primary">
                    {' '}{getCharacterById(msg.character_id)?.name || 'Unknown'}
                  </span>
                )}
              </div>
              <div 
                className="message-content"
                dangerouslySetInnerHTML={{ __html: formatMessage(msg.content) }}
              />
            </div>
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-textMuted p-4">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce"></span>
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
              </div>
              <span className="text-sm">The DM is thinking...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Chat Input */}
        <div className="p-3 border-t border-border space-y-2">
          {/* Mode Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto">
            {(['action', 'speak', 'party', 'dm'] as ChatMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setChatMode(mode)}
                className={`px-2 py-1 rounded text-xs font-medium transition-all whitespace-nowrap ${
                  chatMode === mode 
                    ? 'bg-primary text-white' 
                    : 'bg-surfaceHover text-textMuted hover:text-text'
                }`}
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </button>
            ))}
          </div>
          
          {/* Input Field */}
          <form onSubmit={sendMessage} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                chatMode === 'action' ? "What do you do?" :
                chatMode === 'speak' ? 'Say something...' :
                chatMode === 'party' ? 'Whisper to party...' :
                'Talk to the DM...'
              }
              className="flex-1 input text-sm"
              disabled={loading}
            />
            <button 
              type="submit" 
              className="btn-primary px-3 disabled:opacity-50"
              disabled={loading}
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}