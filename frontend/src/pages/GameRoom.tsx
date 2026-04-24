import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import api from '../lib/api'
import { Send, Dices, User, X, MessageSquare } from 'lucide-react'

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
      case 'dm': return 'border-l-4 border-l-purple-500 bg-purple-900/20'
      case 'party': return 'border-l-4 border-l-yellow-500 bg-yellow-900/10'
      case 'speak': return 'border-l-4 border-l-blue-500 italic bg-blue-900/10'
      case 'action': return 'border-l-4 border-l-primary'
      default: return 'border-l-4 border-l-gray-500'
    }
  }

  const getMessageLabel = (msg: Message) => {
    switch (msg.message_type) {
      case 'dm': return 'The DM'
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
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No messages yet. Start the adventure!</p>
            </div>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className={`p-4 rounded-r-lg rounded-bl-lg ${getMessageStyle(msg)}`}>
              <div className="text-xs text-gray-400 mb-1">{getMessageLabel(msg)}</div>
              <div className="text-sm">{msg.content}</div>
              <div className="text-xs text-gray-500 mt-1">
                {new Date(msg.timestamp).toLocaleTimeString()}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-gray-400">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></span>
                <span className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                <span className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Chat Input */}
        <div className="p-4 border-t border-gray-800">
          <div className="flex gap-2 mb-3">
            {(['action', 'speak', 'party', 'dm'] as ChatMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setChatMode(mode)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  chatMode === mode 
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-900/20' 
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
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
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
              disabled={loading}
            />
            <button 
              type="submit" 
              className="bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
              disabled={loading}
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>

      {/* Sidebar */}
      <div className="w-72 border-l border-gray-800 p-4 space-y-4 overflow-y-auto">
        {/* Character Panel */}
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center gap-2 mb-3">
            <User className="w-4 h-4 text-purple-500" />
            <h3 className="font-semibold text-white">Character</h3>
          </div>
          <select
            value={selectedChar || ''}
            onChange={(e) => setSelectedChar(e.target.value ? Number(e.target.value) : null)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500"
          >
            <option value="">Select character</option>
            {characters.map((char) => (
              <option key={char.id} value={char.id}>
                {char.name} (L{char.level} {char.race} {char.class_name})
              </option>
            ))}
          </select>
          {selectedCharacter && (
            <div className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">HP</span>
                <span className="text-green-400">{selectedCharacter.hp}/{selectedCharacter.max_hp}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">AC</span>
                <span className="text-blue-400">{selectedCharacter.ac}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Level</span>
                <span className="text-white">{selectedCharacter.level}</span>
              </div>
            </div>
          )}
        </div>

        {/* Dice Panel */}
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <button onClick={() => setShowDice(!showDice)} className="flex items-center gap-2 w-full">
            <Dices className="w-4 h-4 text-purple-500" />
            <span className="font-semibold text-white">Dice Roller</span>
          </button>
          {showDice && (
            <div className="mt-3 space-y-3">
              <input
                type="text"
                value={diceInput}
                onChange={(e) => setDiceInput(e.target.value)}
                placeholder="1d20+5"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
              />
              <button 
                onClick={rollDice} 
                className="w-full bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg transition-colors"
              >
                Roll
              </button>
              {diceResults.length > 0 && (
                <div className="text-center py-2">
                  <div className="text-3xl font-bold text-purple-400">{diceResults[0].total}</div>
                  <div className="text-xs text-gray-500">= {diceResults[0].rolls.join(' + ')}</div>
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