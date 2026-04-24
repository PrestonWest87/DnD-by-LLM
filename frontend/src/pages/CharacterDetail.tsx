import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import api from '../lib/api'
import { ArrowLeft, Edit, Save, Sword, Shield, Heart, Zap } from 'lucide-react'

interface Character {
  id: number
  name: string
  race: string
  class_name: string
  level: number
  stats: { str: number; dex: number; con: number; int: number; wis: number; cha: number }
  hp: number
  max_hp: number
  ac: number
  speed: number
  personality: string
  backstory: string
}

const STAT_LABELS: Record<string, string> = {
  str: 'Strength',
  dex: 'Dexterity',
  con: 'Constitution',
  int: 'Intelligence',
  wis: 'Wisdom',
  cha: 'Charisma',
}

export default function CharacterDetail() {
  const { id, characterId } = useParams()
  const navigate = useNavigate()
  const [character, setCharacter] = useState<Character | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editForm, setEditForm] = useState<Partial<Character>>({})

  useEffect(() => {
    loadCharacter()
  }, [characterId])

  const loadCharacter = async () => {
    setError(null)
    try {
      const response = await api.get(`/characters/${characterId}`)
      setCharacter(response.data)
      setEditForm(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load character')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const saveCharacter = async () => {
    setSaving(true)
    setError(null)
    try {
      const response = await api.patch(`/characters/${characterId}`, editForm)
      setCharacter(response.data)
      setEditing(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save character')
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!character) {
    return (
      <div className="text-center py-12">
        <p className="text-textMuted mb-4">Character not found</p>
        <Link to={`/campaign/${id}`} className="btn-primary">
          Back to Campaign
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate(`/campaign/${id}`)}
          className="btn-secondary flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Campaign
        </button>
        {!editing ? (
          <button onClick={() => setEditing(true)} className="btn-secondary flex items-center gap-2">
            <Edit className="w-4 h-4" />
            Edit
          </button>
        ) : (
          <button onClick={saveCharacter} disabled={saving} className="btn-primary flex items-center gap-2">
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save'}
          </button>
        )}
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/20 text-danger px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      <div className="card p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            {editing ? (
              <input
                type="text"
                value={editForm.name || ''}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                className="input text-2xl font-bold"
              />
            ) : (
              <h1 className="font-display text-3xl font-bold">{character.name}</h1>
            )}
            <p className="text-textMuted">
              Level {character.level} {character.race} {character.class_name}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className="flex items-center gap-1 text-danger">
                <Heart className="w-5 h-5" />
                <span className="text-2xl font-bold">{character.hp}</span>
              </div>
              <div className="text-xs text-textMuted">HP</div>
            </div>
            <div className="text-center">
              <div className="flex items-center gap-1 text-primary">
                <Shield className="w-5 h-5" />
                <span className="text-2xl font-bold">{character.ac}</span>
              </div>
              <div className="text-xs text-textMuted">AC</div>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h2 className="font-display text-xl font-semibold mb-4 flex items-center gap-2">
              <Sword className="w-5 h-5 text-primary" />
              Ability Scores
            </h2>
            <div className="space-y-2">
              {Object.entries(character.stats).map(([stat, value]) => (
                <div key={stat} className="flex items-center justify-between p-2 bg-surfaceHover rounded-lg">
                  <span className="font-medium">{STAT_LABELS[stat]}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold w-8 text-right">{value}</span>
                    <span className="text-textMuted text-sm">
                      ({Math.floor((value - 10) / 2) >= 0 ? '+' : ''}{Math.floor((value - 10) / 2)})
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <h2 className="font-display text-xl font-semibold mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-primary" />
                Speed
              </h2>
              <p className="text-2xl font-bold">{character.speed} ft.</p>
            </div>

            {character.personality && (
              <div>
                <h2 className="font-display text-xl font-semibold mb-2">Personality</h2>
                {editing ? (
                  <textarea
                    value={editForm.personality || ''}
                    onChange={(e) => setEditForm({ ...editForm, personality: e.target.value })}
                    className="input w-full h-24"
                  />
                ) : (
                  <p className="text-textMuted">{character.personality}</p>
                )}
              </div>
            )}

            {character.backstory && (
              <div>
                <h2 className="font-display text-xl font-semibold mb-2">Backstory</h2>
                {editing ? (
                  <textarea
                    value={editForm.backstory || ''}
                    onChange={(e) => setEditForm({ ...editForm, backstory: e.target.value })}
                    className="input w-full h-32"
                  />
                ) : (
                  <p className="text-textMuted whitespace-pre-wrap">{character.backstory}</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}