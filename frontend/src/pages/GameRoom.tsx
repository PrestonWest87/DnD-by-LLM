import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import api from '../lib/api'
import { Send, Dices, User, X } from 'lucide-react'

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
}

type ChatMode = 'action' | 'speak' | 'party' | 'dm'

export default function GameRoom() {
  const { id: campaignId, roomId } = useParams()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [characters, setCharacters] = useState<Character[]>([])
  const [selectedChar, setSelectedChar] = useState<number | null>(null)
  const [diceInput, setDiceInput] = useState('1d20')
  const [diceResults, setDiceResults] = useState<any[]>([])
  const [showDice, setShowDice] = useState(false)
  const [chatMode, setChatMode] = useState<ChatMode>('action')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (roomId) {
      loadMessages()
      loadCharacters()
      const interval = setInterval(loadMessages, 3000)
      return () => clearInterval(interval)
    }
  }, [roomId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
      if (response.data.length > 0 && !selectedChar) {
        setSelectedChar(response.data[0].id)
      }
    } catch (err) {
      console.error(err)
    }
  }

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

    setLoading(true)
    try {
      if (chatMode === 'dm') {
        const response = await api.post(`/dm/chat`, {
          room_id: roomId,
          player_input: input,
          character_id: selectedChar
        })
        const dmMessage: Message = {
          id: Date.now(),
          user_id: 0,
          content: response.data.response,
          message_type: 'dm',
          timestamp: new Date().toISOString()
        }
        setMessages(prev => [...prev, { id: Date.now(), user_id: 0, content: input, message_type: 'player', timestamp: new Date().toISOString() }, dmMessage])
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

  const getMessageStyle = (msg: Message) => {
    switch (msg.message_type) {
      case 'dm': return 'bg-purple-900/30 border-l-4 border-purple-500'
      case 'party': return 'bg-yellow-900/20 border-l-4 border-yellow-500'
      case 'speak': return 'bg-blue-900/20 border-l-4 border-blue-500 italic'
      case 'action': return 'bg-surfaceHover border-l-4 border-primary'
      default: return 'bg-surfaceHover'
    }
  }

  const getMessageLabel = (msg: Message) => {
    switch (msg.message_type) {
      case 'dm': return 'DM'
      case 'party': return 'Party'
      case 'speak': return 'Said'
      case 'action': return 'Action'
      default: return 'Player'
    }
  }

  const selectedCharacter = characters.find(c => c.id === selectedChar)

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {messages.map((msg) => (
            <div key={msg.id} className={`p-3 rounded-lg ${getMessageStyle(msg)}`}>
              <div className="text-xs text-textMuted mb-1">{getMessageLabel(msg)}</div>
              <div>{msg.content}</div>
              <div className="text-xs text-textMuted mt-1">
                {new Date(msg.timestamp).toLocaleTimeString()}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-textMuted">
              <span>Thinking</span>
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0s' }}></span>
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t border-border">
          <div className="flex gap-2 mb-2">
            {(['action', 'speak', 'party', 'dm'] as ChatMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setChatMode(mode)}
                className={`px-3 py-1 rounded text-sm capitalize ${chatMode === mode ? 'bg-primary text-white' : 'bg-surfaceHover'}`}
              >
                {mode}
              </button>
            ))}
          </div>
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
              className="input flex-1"
              disabled={loading}
            />
            <button type="submit" className="btn-primary" disabled={loading}>
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>

      {/* Sidebar */}
      <div className="w-80 border-l border-border p-4 space-y-4 overflow-y-auto">
        {/* Character Panel */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-4">
            <User className="w-4 h-4 text-primary" />
            <h3 className="font-semibold">Character</h3>
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
          {selectedCharacter && (
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-textMuted">HP</span>
                <span>{selectedCharacter.hp} / {selectedCharacter.max_hp}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-textMuted">AC</span>
                <span>{selectedCharacter.ac}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-textMuted">Level</span>
                <span>{selectedCharacter.level}</span>
              </div>
            </div>
          )}
        </div>

        {/* Dice Panel */}
        <div className="card p-4">
          <button onClick={() => setShowDice(!showDice)} className="flex items-center gap-2 w-full">
            <Dices className="w-4 h-4" />
            <span className="font-semibold">Dice</span>
          </button>
          {showDice && (
            <div className="mt-4 space-y-2">
              <input
                type="text"
                value={diceInput}
                onChange={(e) => setDiceInput(e.target.value)}
                placeholder="1d20+5"
                className="input"
              />
              <button onClick={rollDice} className="btn-secondary w-full">Roll</button>
              {diceResults.length > 0 && (
                <div className="text-center mt-2">
                  <div className="text-2xl font-bold">{diceResults[0].total}</div>
                  <div className="text-sm text-textMuted">= {diceResults[0].rolls.join(' + ')}</div>
                </div>
              )}
            </div>
          )}
        </div>

        {error && <div className="text-red-500 text-sm">{error}</div>}
      </div>
    </div>
  )
}