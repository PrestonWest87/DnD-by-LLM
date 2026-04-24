import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { Send, Dices, User, Map, Settings, X, MessageSquare, Me } from 'lucide-react'

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
  name: string
  race: string
  class_name: string
  level: number
  hp: number
  max_hp: number
  ac: number
  stats: Record<string, number>
}

export default function GameRoom() {
  const { id, roomId } = useParams()
  const navigate = useNavigate()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [characters, setCharacters] = useState<Character[]>([])
  const [selectedChar, setSelectedChar] = useState<number | null>(null)
  const [showDice, setShowDice] = useState(false)
  const [diceInput, setDiceInput] = useState('1d20')
  const [diceResults, setDiceResults] = useState<any[]>([])
  const [showMap, setShowMap] = useState(false)
  const [maps, setMaps] = useState<any[]>([])
  const [mapError, setMapError] = useState<string | null>(null)
  const [chatMode, setChatMode] = useState<'action' | 'speak' | 'party' | 'dm'>('action')

  useEffect(() => {
    loadMessages()
    loadCharacters()
    loadMaps()
    const interval = setInterval(loadMessages, 3000)
    return () => clearInterval(interval)
  }, [roomId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadMessages = async () => {
    try {
      const response = await api.get(`/rooms/${roomId}/messages`)
      const newMessages = response.data.reverse()
      if (newMessages.length !== messages.length) {
        setMessages(newMessages)
      }
    } catch (err) {
      console.error(err)
    }
  }

  const loadCharacters = async () => {
    try {
      const response = await api.get(`/characters/campaign/${id}`)
      setCharacters(response.data)
      if (response.data.length > 0 && !selectedChar) {
        setSelectedChar(response.data[0].id)
      }
    } catch (err) {
      console.error(err)
    }
  }

  const loadMaps = async () => {
    try {
      const response = await api.get(`/maps/campaign/${id}`)
      setMaps(response.data)
    } catch (err) {
      console.error(err)
    }
  }

  const getMessageType = () => {
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

    const userMessage: Message = {
      id: Date.now(),
      user_id: 0,
      character_id: selectedChar || undefined,
      content: input,
      message_type: getMessageType(),
      timestamp: new Date().toISOString()
    }
    setMessages([...messages, userMessage])
    setLoading(true)

    try {
      let response
      if (chatMode === 'dm') {
        response = await api.post(`/dm/chat`, {
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
        setMessages(prev => [...prev, userMessage, dmMessage])
      } else {
        await api.post(`/rooms/${roomId}/messages`, {
          content: input,
          message_type: getMessageType(),
          character_id: selectedChar
        })
      }
    } catch (err) {
      console.error(err)
    } finally {
      setInput('')
      setLoading(false)
    }
  }

interface Character {
  id: number
  name: string
  race: string
  class_name: string
  level: number
  hp: number
  max_hp: number
  ac: number
  stats: Record<string, number>
}

export default function GameRoom() {
  const { id, roomId } = useParams()
  const navigate = useNavigate()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [characters, setCharacters] = useState<Character[]>([])
  const [selectedChar, setSelectedChar] = useState<number | null>(null)
  const [showDice, setShowDice] = useState(false)
  const [diceInput, setDiceInput] = useState('1d20')
  const [diceResults, setDiceResults] = useState<any[]>([])
  const [showMap, setShowMap] = useState(false)
  const [maps, setMaps] = useState<any[]>([])
  const [dmLoading, setDmLoading] = useState(false)
  const [mapError, setMapError] = useState<string | null>(null)

  useEffect(() => {
    loadMessages()
    loadCharacters()
    loadMaps()
  }, [roomId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadMessages = async () => {
    try {
      const response = await api.get(`/rooms/${roomId}/messages`)
      setMessages(response.data.reverse())
    } catch (err) {
      console.error(err)
    }
  }

const loadCharacters = async () => {
    try {
      const response = await api.get(`/characters/campaign/${id}`)
      setCharacters(response.data)
      if (response.data.length > 0 && !selectedChar) {
        setSelectedChar(response.data[0].id)
      }
    } catch (err) {
      console.error(err)
    }
  }
  }

  const loadMaps = async () => {
    try {
      const response = await api.get(`/maps/campaign/${id}`)
      setMaps(response.data)
    } catch (err) {
      console.error(err)
    }
  }

  const generateMap = async () => {
    if (!confirm('Generate a new dungeon map? This will create a 50x50 procedural dungeon.')) return
    setMapError(null)
    try {
      const response = await api.post('/maps/generate', {
        campaign_id: id,
        name: `Dungeon ${maps.length + 1}`,
        map_type: 'dungeon',
        width: 50,
        height: 50,
        difficulty: 'medium'
      })
      setMaps([...maps, response.data])
    } catch (err: any) {
      setMapError(err.response?.data?.detail || 'Failed to generate map')
      console.error(err)
    }
  }

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage: Message = {
      id: Date.now(),
      user_id: 0,
      content: input,
      message_type: 'player',
      timestamp: new Date().toISOString()
    }
    setMessages([...messages, userMessage])
    setLoading(true)

    try {
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
      setMessages(prev => [...prev, userMessage, dmMessage])
    } catch (err) {
      console.error(err)
    } finally {
      setInput('')
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

  const formatTimestamp = (ts: string) => {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="flex h-[calc(100vh-100px)] gap-4">
      <div className="flex-1 flex flex-col card">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h2 className="font-display text-xl font-semibold">Game Room</h2>
          <div className="flex gap-2">
            <button
              onClick={() => setShowMap(true)}
              className="btn-secondary text-sm flex items-center gap-2"
            >
              <Map className="w-4 h-4" />
              Map
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.message_type === 'player' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] p-3 rounded-lg ${
                  msg.message_type === 'dm'
                    ? 'bg-primary/10 border border-primary/20 text-text'
                    : 'bg-surfaceHover text-text'
                }`}
              >
                {msg.message_type === 'dm' && (
                  <div className="text-xs text-primary font-semibold mb-1">DM</div>
                )}
                <p className="whitespace-pre-wrap">{msg.content}</p>
                <div className="text-xs text-textMuted mt-2">
                  {formatTimestamp(msg.timestamp)}
                </div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-primary/10 border border-primary/20 p-3 rounded-lg">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce"></span>
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t border-border">
          <div className="flex gap-2 mb-2">
            <button
              type="button"
              onClick={() => setChatMode('action')}
              className={`px-3 py-1 rounded text-sm ${chatMode === 'action' ? 'bg-primary text-white' : 'bg-surfaceHover'}`}
            >
              Action
            </button>
            <button
              type="button"
              onClick={() => setChatMode('speak')}
              className={`px-3 py-1 rounded text-sm ${chatMode === 'speak' ? 'bg-primary text-white' : 'bg-surfaceHover'}`}
            >
              Speak
            </button>
            <button
              type="button"
              onClick={() => setChatMode('party')}
              className={`px-3 py-1 rounded text-sm ${chatMode === 'party' ? 'bg-primary text-white' : 'bg-surfaceHover'}`}
            >
              Party
            </button>
            <button
              type="button"
              onClick={() => setChatMode('dm')}
              className={`px-3 py-1 rounded text-sm ${chatMode === 'dm' ? 'bg-primary text-white' : 'bg-surfaceHover'}`}
            >
              DM
            </button>
          </div>
          <form onSubmit={sendMessage} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={chatMode === 'action' ? "What do you do?" : chatMode === 'speak' ? "Say something..." : chatMode === 'party' ? "Whisper to party..." : "Talk to the DM..."}
              className="input flex-1"
              disabled={loading}
            />
            <button type="submit" className="btn-primary" disabled={loading}>
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>

      <div className="w-80 space-y-4">
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-4">
            <User className="w-4 h-4 text-primary" />
            <h3 className="font-semibold">Active Character</h3>
          </div>
          <select
            value={selectedChar || ''}
            onChange={(e) => setSelectedChar(e.target.value ? Number(e.target.value) : null)}
            className="input"
          >
            <option value="">Select character</option>
            {characters.map((char) => (
              <option key={char.id} value={char.id}>
                {char.name} (Lvl {char.level} {char.race} {char.class_name})
              </option>
            ))}
          </select>

          {selectedChar && characters.find(c => c.id === selectedChar) && (
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-textMuted">HP</span>
                <span>{characters.find(c => c.id === selectedChar)?.hp} / {characters.find(c => c.id === selectedChar)?.max_hp}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-textMuted">AC</span>
                <span>{characters.find(c => c.id === selectedChar)?.ac}</span>
              </div>
              <div className="text-sm mt-2">
                <div className="text-textMuted mb-1">Stats</div>
                <div className="grid grid-cols-3 gap-1 text-xs">
                  {Object.entries(characters.find(c => c.id === selectedChar)?.stats || {}).map(([stat, val]) => (
                    <div key={stat} className="text-center">
                      <div className="text-textMuted uppercase">{stat.slice(0, 3)}</div>
                      <div>{val}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Dices className="w-4 h-4 text-accent" />
              <h3 className="font-semibold">Dice Roller</h3>
            </div>
          </div>
          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={diceInput}
              onChange={(e) => setDiceInput(e.target.value)}
              placeholder="1d20+5"
              className="input"
            />
            <button onClick={rollDice} className="btn-primary">
              Roll
            </button>
          </div>
          {diceResults.length > 0 && (
            <div className="space-y-2">
              {diceResults.map((result, i) => (
                <div key={i} className={`p-2 rounded text-center ${
                  result.is_critical ? 'bg-success/20 border border-success' :
                  result.is_fumble ? 'bg-danger/20 border border-danger' :
                  'bg-surfaceHover'
                }`}>
                  <div className="text-2xl font-bold">{result.total}</div>
                  <div className="text-xs text-textMuted">
                    {result.dice}: [{result.rolls.join(', ')}] {result.modifier > 0 ? `+${result.modifier}` : result.modifier < 0 ? result.modifier : ''}
                    {result.natural && ` (nat ${result.natural})`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {showMap && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="card w-[800px] h-[600px] flex flex-col">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h2 className="font-display text-xl font-semibold">Campaign Map</h2>
              <button onClick={() => setShowMap(false)} className="text-textMuted hover:text-text">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 p-4 overflow-auto">
              {maps.length === 0 ? (
                <div className="text-center py-12 text-textMuted">
                  <Map className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>No maps yet</p>
                  <button onClick={generateMap} className="btn-primary mt-4">Generate Map</button>
                  {mapError && <p className="text-danger mt-2">{mapError}</p>}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {maps.map((map) => (
                    <div
                      key={map.id}
                      className="aspect-square bg-surfaceHover rounded-lg flex items-center justify-center cursor-pointer hover:border-primary border border-transparent transition-colors"
                    >
                      {map.name}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}