import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { useAuthStore } from '../lib/store'
import { 
  Send, Dices, User, MessageSquare, Sword, Shield, Zap, Users,
  ChevronDown, ChevronUp, Heart, Activity, Footprints, Sparkles,
  RotateCcw, Volume2, VolumeX, MoreHorizontal
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
  const [showCharPanel, setShowCharPanel] = useState(true)
  const [showInitiative, setShowInitiative] = useState(false)
  const [chatMode, setChatMode] = useState<ChatMode>('action')
  const [error, setError] = useState<string | null>(null)
  const [encounter, setEncounter] = useState<Encounter | null>(null)
  const [muted, setMuted] = useState(false)
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
    if (currentUser && characters.length > 0 && !selectedChar) {
      const userChars = characters.filter((c: Character) => c.user_id === currentUser.id)
      if (userChars.length > 0) {
        setSelectedChar(userChars[0].id)
      } else {
        setSelectedChar(characters[0].id)
      }
    }
  }, [currentUser, characters, selectedChar])

  const getMessageType = (): string => {
    switch (chatMode) {
      case 'speak': return 'speak'
      case 'party': return 'party'
      case 'action': return 'action'
      default: return 'player'
    }
  }

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMsg: Message = {
      id: Date.now(),
      user_id: 0,
      character_id: selectedChar || undefined,
      content: input,
      message_type: getMessageType(),
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)
    setInput('')
    
    try {
      if (chatMode === 'dm') {
        const response = await api.post(`/dm/chat`, {
          room_id: roomId,
          player_input: input,
          character_id: selectedChar
        })
        const dmMessage: Message = {
          id: Date.now() + 1,
          user_id: 0,
          content: response.data.response,
          message_type: 'dm',
          timestamp: new Date().toISOString()
        }
        setMessages(prev => [...prev, dmMessage])
        
        await api.post(`/rooms/${roomId}/messages`, {
          content: input,
          message_type: 'player',
          character_id: selectedChar
        })
        await api.post(`/rooms/${roomId}/messages`, {
          content: response.data.response,
          message_type: 'dm',
          character_id: null
        })
      } else {
        await api.post(`/rooms/${roomId}/messages`, {
          content: input,
          message_type: getMessageType(),
          character_id: selectedChar
        })
        await loadMessages()
      }
    } catch (err) {
      console.error(err)
      setError('Failed to send message')
    } finally {
      setLoading(false)
    }
  }

  const rollDice = async () => {
    try {
      const response = await api.post('/dice/roll', [{
        dice: diceInput,
        modifier: 0,
        advantage: false,
        disadvantage: false
      }])
      setDiceResults(response.data)
    } catch (err) {
      console.error(err)
    }
  }

  const getMessageStyle = (msg: Message) => {
    switch (msg.message_type) {
      case 'dm': 
        return 'border-l-4 border-l-purple-500 bg-purple-900/20'
      case 'party': 
        return 'border-l-4 border-l-yellow-500 bg-yellow-900/10'
      case 'speak': 
        return 'border-l-4 border-l-blue-500 italic bg-blue-900/10'
      case 'action': 
        return 'border-l-4 border-l-primary'
      case 'narrator':
        return 'border-l-4 border-l-cyan-500 bg-cyan-900/10'
      case 'whisper':
        return 'border-l-4 border-l-pink-500 bg-pink-900/10'
      default: 
        return 'border-l-4 border-l-gray-500'
    }
  }

  const getMessageIcon = (msg: Message) => {
    switch (msg.message_type) {
      case 'dm': return <Sparkles className="w-3 h-3 text-purple-400" />
      case 'action': return <Sword className="w-3 h-3 text-primary" />
      case 'speak': return <MessageSquare className="w-3 h-3 text-blue-400" />
      case 'party': return <Users className="w-3 h-3 text-yellow-400" />
      default: return <User className="w-3 h-3 text-gray-400" />
    }
  }

  const getMessageLabel = (msg: Message) => {
    switch (msg.message_type) {
      case 'dm': return 'The DM'
      case 'party': return 'Party'
      case 'speak': return 'Said'
      case 'action': return 'Action'
      case 'narrator': return 'Narrator'
      case 'whisper': return 'Whisper'
      case 'dice': return 'Dice Roll'
      case 'system': return 'System'
      default: return 'Player'
    }
  }

  const formatMessageContent = (content: string) => {
    let formatted = content
    
    formatted = formatted.replace(/\[?(\d+)d(\d+)([+-]\d+)?\s*=\s*(\d+)\]?/g, (_, count, die, mod, result) => {
      const total = parseInt(result)
      const isCrit = parseInt(die) === 20 && parseInt(count) === 1 && (total === 20 || total === 1)
      const isFail = parseInt(count) === 1 && parseInt(die) === 20 && total === 1
      let color = 'text-purple-400'
      if (isCrit) color = 'text-yellow-400'
      else if (isFail) color = 'text-red-400'
      else if (total >= 15) color = 'text-green-400'
      else if (total >= 10) color = 'text-yellow-400'
      else color = 'text-red-400'
      return `<span class="${color} font-bold">${count}d${die}${mod || ''} = ${result}</span>`
    })

    formatted = formatted.replace(/(HP|hp):\s*(\d+)\/(\d+)/g, '<span class="text-green-400">$1: $2/$3</span>')
    formatted = formatted.replace(/(restored|healed|gained)\s+(\d+)\s+(HP|hp)/gi, '<span class="text-green-400">$1 $2 $3</span>')
    formatted = formatted.replace(/(lost|take[sd]?|damage[sd]?)\s+(\d+)\s+(HP|hp)/gi, '<span class="text-red-400">$1 $2 $3</span>')
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>')
    formatted = formatted.replace(/__(.*?)__/g, '<u>$1</u>')
    formatted = formatted.replace(/`(.*?)`/g, '<code class="bg-gray-800 px-1 rounded text-purple-300">$1</code>')

    return formatted
  }

  const selectedCharacter = characters.find(c => c.id === selectedChar)

  const getCharacterById = (id: number) => characters.find(c => c.id === id)

  // Calculate HP percentage for progress bar
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
    <div className="flex h-[calc(100vh-4rem)] bg-surface overflow-hidden">
      {/* Map Area - 60% */}
      {currentMap && (
        <div className="w-[60%] border-r border-border relative overflow-hidden">
          <div className="absolute inset-0 p-2">
            <div 
              className="w-full h-full relative rounded-lg overflow-hidden"
              style={{ 
                backgroundColor: '#1a1a2e',
                backgroundImage: 'linear-gradient(#16213e 1px, transparent 1px), linear-gradient(90deg, #16213e 1px, transparent 1px)',
                backgroundSize: '20px 20px'
              }}
            >
              {/* Render map entities */}
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
                    className={`absolute w-4 h-4 rounded-full ${getEntityColor(entity.entity_type)} border-2 border-white shadow-lg flex items-center justify-center`}
                    style={{
                      left: `${(entity.x / (currentMap.width || 50)) * 100}%`,
                      top: `${(entity.y / (currentMap.height || 50)) * 100}%`,
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
                {currentMap.name || 'Dungeon Map'}
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
      )}
      
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Chat Header */}
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => navigate(`/campaign/${campaignId}`)}
              className="p-2 hover:bg-surfaceHover rounded-lg transition-colors"
            >
              <ChevronDown className="w-4 h-4 rotate-90" />
            </button>
            <div>
              <h2 className="font-display font-bold text-lg">Adventure</h2>
              <p className="text-xs text-textMuted">
                {messages.length} messages
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setMuted(!muted)}
              className={`p-2 rounded-lg transition-colors ${muted ? 'bg-red-900/30 text-red-400' : 'hover:bg-surfaceHover'}`}
            >
              {muted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
            <button
              onClick={() => setShowCharPanel(!showCharPanel)}
              className={`p-2 rounded-lg transition-colors ${showCharPanel ? 'bg-primary/20 text-primary' : 'hover:bg-surfaceHover'}`}
            >
              <MoreHorizontal className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin">
          {messages.length === 0 && (
            <div className="text-center text-textMuted py-12">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-surface flex items-center justify-center">
                <MessageSquare className="w-8 h-8 opacity-50" />
              </div>
              <p className="text-lg font-display">No messages yet</p>
              <p className="text-sm mt-2">Start the adventure by sending a message!</p>
            </div>
          )}
          {messages.map((msg) => (
            <div 
              key={msg.id} 
              className={`p-4 rounded-r-xl rounded-bl-xl ${getMessageStyle(msg)} message-enter`}
            >
              <div className="flex items-center gap-2 text-xs text-textMuted mb-2">
                {getMessageIcon(msg)}
                <span className="font-medium">{getMessageLabel(msg)}</span>
                {msg.character_id && (
                  <span className="text-primary">
                    • {getCharacterById(msg.character_id)?.name || 'Unknown'}
                  </span>
                )}
              </div>
              <div 
                className="text-sm leading-relaxed"
                dangerouslySetInnerHTML={{ __html: formatMessageContent(msg.content) }}
              />
              <div className="text-xs text-textMuted mt-2 opacity-60">
                {new Date(msg.timestamp).toLocaleTimeString()}
              </div>
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
        <div className="p-4 border-t border-border space-y-3">
          {/* Mode Tabs */}
          <div className="flex items-center gap-2 overflow-x-auto">
            {(['action', 'speak', 'party', 'dm'] as ChatMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setChatMode(mode)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                  chatMode === mode 
                    ? 'bg-primary text-white glow-purple' 
                    : 'bg-surfaceHover text-textMuted hover:text-text'
                }`}
              >
                {mode === 'action' && <Sword className="w-3 h-3 inline mr-1" />}
                {mode === 'speak' && <MessageSquare className="w-3 h-3 inline mr-1" />}
                {mode === 'party' && <Users className="w-3 h-3 inline mr-1" />}
                {mode === 'dm' && <Sparkles className="w-3 h-3 inline mr-1" />}
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </button>
            ))}
            <div className="flex-1" />
            <button
              type="button"
              onClick={async () => {
                if (selectedChar) {
                  try {
                    await api.post(`/sessions/room/${roomId}/ready`, { character_id: selectedChar })
                    setIsReady(!isReady)
                  } catch (err) {
                    console.error('Failed to toggle ready:', err)
                  }
                }
              }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap flex items-center gap-2 ${
                isReady 
                  ? 'bg-green-600 text-white glow-green' 
                  : 'bg-surfaceHover text-yellow-400 hover:text-yellow-300'
              }`}
            >
              <Shield className="w-4 h-4" />
              {isReady ? 'Ready!' : 'Ready Up'}
            </button>
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
              className="flex-1 input"
              disabled={loading}
            />
            <button 
              type="submit" 
              className="btn-primary px-4 disabled:opacity-50"
              disabled={loading}
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>

      {/* Sidebar */}
      {showCharPanel && (
        <div className="w-80 border-l border-border flex flex-col overflow-hidden">
          {/* Character Panel */}
          <div className="p-4 border-b border-border">
            <div className="flex items-center gap-2 mb-3">
              <User className="w-4 h-4 text-primary" />
              <h3 className="font-semibold">Character</h3>
            </div>
            
            <select
              value={selectedChar || ''}
              onChange={(e) => setSelectedChar(e.target.value ? Number(e.target.value) : null)}
              className="w-full input mb-3"
            >
              <option value="">Select character</option>
              {characters.map((char) => (
                <option key={char.id} value={char.id}>
                  {char.name} (L{char.level} {char.race} {char.class_name})
                </option>
              ))}
            </select>
            
            {selectedCharacter && (
              <div className="space-y-3">
                {/* HP Bar */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="flex items-center gap-1 text-textMuted">
                      <Heart className="w-3 h-3" /> HP
                    </span>
                    <span className="text-green-400 font-medium">
                      {selectedCharacter.hp}/{selectedCharacter.max_hp}
                    </span>
                  </div>
                  <div className="stat-bar">
                    <div 
                      className={`stat-bar-fill ${getHpColor(selectedCharacter.hp, selectedCharacter.max_hp)}`}
                      style={{ width: `${getHpPercent(selectedCharacter.hp, selectedCharacter.max_hp)}%` }}
                    />
                  </div>
                </div>
                
                {/* Stats Grid */}
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="bg-surfaceHover p-2 rounded-lg text-center">
                    <div className="flex items-center justify-center gap-1 text-textMuted mb-1">
                      <Shield className="w-3 h-3" /> AC
                    </div>
                    <div className="text-blue-400 font-bold text-lg">{selectedCharacter.ac}</div>
                  </div>
                  <div className="bg-surfaceHover p-2 rounded-lg text-center">
                    <div className="flex items-center justify-center gap-1 text-textMuted mb-1">
                      <Activity className="w-3 h-3" /> Level
                    </div>
                    <div className="text-primary font-bold text-lg">{selectedCharacter.level}</div>
                  </div>
                  <div className="bg-surfaceHover p-2 rounded-lg text-center">
                    <div className="flex items-center justify-center gap-1 text-textMuted mb-1">
                      <Footprints className="w-3 h-3" /> Speed
                    </div>
                    <div className="text-accent font-bold text-lg">30</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Dice Roller */}
          <div className="p-4 border-b border-border">
            <button 
              onClick={() => setShowDice(!showDice)} 
              className="flex items-center gap-2 w-full"
            >
              <Dices className="w-4 h-4 text-accent" />
              <span className="font-semibold flex-1 text-left">Dice Roller</span>
              {showDice ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            {showDice && (
              <div className="mt-3 space-y-3">
                <input
                  type="text"
                  value={diceInput}
                  onChange={(e) => setDiceInput(e.target.value)}
                  placeholder="1d20+5"
                  className="input text-center font-mono"
                />
                <div className="flex gap-2">
                  <button onClick={rollDice} className="btn-primary flex-1">
                    Roll
                  </button>
                  <button 
                    onClick={() => setDiceInput('1d20')} 
                    className="btn-secondary px-3"
                    title="Reset"
                  >
                    <RotateCcw className="w-4 h-4" />
                  </button>
                </div>
                {diceResults.length > 0 && (
                  <div className="text-center py-3 bg-surfaceHover rounded-lg">
                    <div className="text-4xl font-bold text-accent glow-gold">
                      {diceResults[0].total}
                    </div>
                    <div className="text-xs text-textMuted mt-1">
                      {diceResults[0].rolls.join(' + ')}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Initiative Panel */}
          <div className="p-4 border-b border-border">
            <button 
              onClick={() => setShowInitiative(!showInitiative)} 
              className="flex items-center gap-2 w-full"
            >
              <Zap className="w-4 h-4 text-yellow-400" />
              <span className="font-semibold flex-1 text-left">Initiative</span>
              {showInitiative ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            {showInitiative && (
              <div className="mt-3 space-y-2">
                {encounter ? (
                  <>
                    <div className="text-xs text-textMuted mb-2">
                      Round {encounter.round} • Turn {encounter.current_turn}
                    </div>
                    {encounter.participants?.map((p) => (
                      <div 
                        key={p.id}
                        className={`p-2 rounded-lg flex items-center justify-between ${
                          p.turn_order === encounter.current_turn 
                            ? 'bg-primary/20 border border-primary' 
                            : 'bg-surfaceHover'
                        }`}
                      >
                        <span className="text-sm">
                          {getCharacterById(p.character_id)?.name || 'Unknown'}
                        </span>
                        <span className="text-xs text-textMuted">
                          {p.hp_remaining} HP
                        </span>
                      </div>
                    ))}
                  </>
                ) : (
                  <div className="text-center py-4 text-textMuted text-sm">
                    No active encounter
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Error Display */}
          {error && (
            <div className="p-4 text-danger text-sm">{error}</div>
          )}
        </div>
      )}
    </div>
  )
}