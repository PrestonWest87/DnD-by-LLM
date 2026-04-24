import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../lib/api'
import { ArrowLeft, ArrowRight, Check, User, Shield, Heart, RefreshCw } from 'lucide-react'

const STAT_NAMES = ['str', 'dex', 'con', 'int', 'wis', 'cha'] as const

const STAT_LABELS: Record<string, string> = {
  str: 'Strength',
  dex: 'Dexterity',
  con: 'Constitution',
  int: 'Intelligence',
  wis: 'Wisdom',
  cha: 'Charisma',
}

const RACES = [
  { id: 'human', name: 'Human', bonus: '+1 to all stats' },
  { id: 'elf', name: 'Elf', bonus: '+2 Dex, +1 Int' },
  { id: 'dwarf', name: 'Dwarf', bonus: '+2 Con, +1 Wis' },
  { id: 'halfling', name: 'Halfling', bonus: '+2 Dex, +1 Cha' },
  { id: 'gnome', name: 'Gnome', bonus: '+2 Int, +1 Dex' },
  { id: 'dragonborn', name: 'Dragonborn', bonus: '+2 Str, +1 Cha' },
  { id: 'half-orc', name: 'Half-Orc', bonus: '+2 Str, +1 Con' },
  { id: 'tiefling', name: 'Tiefling', bonus: '+2 Cha, +1 Int' },
]

const CLASSES = [
  { id: 'fighter', name: 'Fighter', hitDie: 'd10', desc: 'Skilled martial warriors' },
  { id: 'rogue', name: 'Rogue', hitDie: 'd8', desc: 'Stealthy tricksters' },
  { id: 'wizard', name: 'Wizard', hitDie: 'd6', desc: 'Arcane spellcasters' },
  { id: 'cleric', name: 'Cleric', hitDie: 'd8', desc: 'Divine healers' },
  { id: 'paladin', name: 'Paladin', hitDie: 'd10', desc: 'Holy warriors' },
  { id: 'ranger', name: 'Ranger', hitDie: 'd10', desc: 'Wilderness experts' },
  { id: 'barbarian', name: 'Barbarian', hitDie: 'd12', desc: 'Fierce berserkers' },
  { id: 'bard', name: 'Bard', hitDie: 'd8', desc: 'Charming performers' },
  { id: 'druid', name: 'Druid', hitDie: 'd8', desc: 'Nature magic users' },
  { id: 'monk', name: 'Monk', hitDie: 'd8', desc: 'Martial artists' },
  { id: 'warlock', name: 'Warlock', hitDie: 'd8', desc: 'Pact magic users' },
  { id: 'sorcerer', name: 'Sorcerer', hitDie: 'd6', desc: 'Innate spellcasters' },
]

const BACKGROUNDS = [
  { id: 'acolyte', name: 'Acolyte', skills: 'Insight, Religion' },
  { id: 'folk_hero', name: 'Folk Hero', skills: 'Animal Handling, Survival' },
  { id: 'criminal', name: 'Criminal', skills: 'Deception, Stealth' },
  { id: 'sage', name: 'Sage', skills: 'Arcana, History' },
  { id: 'soldier', name: 'Soldier', skills: 'Athletics, Intimidation' },
  { id: 'outlander', name: 'Outlander', skills: 'Athletics, Survival' },
  { id: 'noble', name: 'Noble', skills: 'History, Persuasion' },
  { id: 'entrant', name: 'Entrant', skills: 'Performance, Persuasion' },
]

const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

type StatKey = typeof STAT_NAMES[number]

interface AssignedStats {
  str: number | null
  dex: number | null
  con: number | null
  int: number | null
  wis: number | null
  cha: number | null
}

const RACE_BONUSES: Record<string, Record<string, number>> = {
  human: { str: 1, dex: 1, con: 1, int: 1, wis: 1, cha: 1 },
  elf: { dex: 2, int: 1 },
  dwarf: { con: 2, wis: 1 },
  halfling: { dex: 2, cha: 1 },
  gnome: { int: 2, dex: 1 },
  dragonborn: { str: 2, cha: 1 },
  'half-orc': { str: 2, con: 1 },
  tiefling: { cha: 2, int: 1 },
}

export default function CharacterCreator() {
  const { campaignId } = useParams()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [character, setCharacter] = useState({
    name: '',
    race: '',
    class_name: '',
    background: 'acolyte',
    personality: '',
    backstory: '',
  })
  const [assignedStats, setAssignedStats] = useState<AssignedStats>({
    str: null, dex: null, con: null, int: null, wis: null, cha: null,
  })
  const [useStandardArray, setUseStandardArray] = useState(false)
  const [rolling, setRolling] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rerollsUsed, setRerollsUsed] = useState(0)
  const [hasRolledOnce, setHasRolledOnce] = useState(false)

  const totalSteps = 4

  const nextStep = () => setStep(Math.min(step + 1, totalSteps))
  const prevStep = () => setStep(Math.max(step - 1, 1))

  const rollAllStats = async () => {
    setRolling(true)
    setUseStandardArray(false)
    setError(null)
    try {
      const response = await api.post('/characters/roll-stats')
      const newRolls = response.data.rolls
      setAssignedStats({
        str: newRolls[0],
        dex: newRolls[1],
        con: newRolls[2],
        int: newRolls[3],
        wis: newRolls[4],
        cha: newRolls[5],
      })
      setHasRolledOnce(true)
    } catch (err) {
      console.error('Failed to roll stats:', err)
      setError('Failed to roll stats')
    } finally {
      setRolling(false)
    }
  }

  const useStandard = () => {
    setAssignedStats({
      str: STANDARD_ARRAY[0],
      dex: STANDARD_ARRAY[1],
      con: STANDARD_ARRAY[2],
      int: STANDARD_ARRAY[3],
      wis: STANDARD_ARRAY[4],
      cha: STANDARD_ARRAY[5],
    })
    setUseStandardArray(true)
    setHasRolledOnce(true)
    setError(null)
  }

  const rerollStat = async (stat: StatKey) => {
    if (assignedStats[stat] === null) return
    if (rerollsUsed >= 3) {
      setError('No rerolls left. Use Standard Array instead.')
      return
    }
    setRolling(true)
    setError(null)
    try {
      const response = await api.post('/characters/roll-stats')
      const newRoll = response.data.rolls[0]
      setAssignedStats({ ...assignedStats, [stat]: newRoll })
      setRerollsUsed((r) => r + 1)
    } catch (err) {
      console.error('Failed to reroll:', err)
      setError('Failed to reroll')
    } finally {
      setRolling(false)
    }
  }

  const getFinalStat = (stat: StatKey): number => {
    const base = assignedStats[stat]
    if (base === null) return 0
    const race = character.race as keyof typeof RACE_BONUSES
    const bonus = RACE_BONUSES[race]?.[stat] ?? 0
    return base + bonus
  }

  const getModifier = (stat: number) => {
    if (stat <= 0) return 0
    return stat >= 10 ? `+${Math.floor((stat - 10) / 2)}` : `${Math.floor((stat - 10) / 2)}`
  }

  const allStatsAssigned = Object.values(assignedStats).every((v) => v !== null)

  const submitCharacter = async () => {
    if (!campaignId) {
      setError('No campaign selected')
      return
    }
    if (!character.name || !character.race || !character.class_name) {
      setError('Please fill in name, race, and class')
      return
    }
    if (!allStatsAssigned) {
      setError('Please fill in all ability scores')
      return
    }
    
    setLoading(true)
    setError(null)
    console.log('Submitting character with:', {
      campaign_id: parseInt(campaignId),
      name: character.name,
      race: character.race,
      class_name: character.class_name,
      background: character.background,
      stat_rolls: STAT_NAMES.map((s) => getFinalStat(s)),
      use_standard_array: useStandardArray,
      personality: character.personality,
      backstory: character.backstory,
    })
    try {
      const response = await api.post('/characters/create-with-rolls', {
        campaign_id: parseInt(campaignId),
        name: character.name,
        race: character.race,
        class_name: character.class_name,
        background: character.background,
        stat_rolls: STAT_NAMES.map((s) => getFinalStat(s)),
        use_standard_array: useStandardArray,
        personality: character.personality,
        backstory: character.backstory,
      })
      console.log('Character created:', response.data)
      navigate(`/campaign/${campaignId}`)
    } catch (err: any) {
      console.error('Failed to create character:', err)
      console.error('Error response:', err.response)
      setError(err.response?.data?.detail || err.message || 'Failed to create character')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-textMuted hover:text-text mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back
      </button>

      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold mb-2">Create Your Character</h1>
        <div className="flex gap-2">
          {[1, 2, 3, 4].map((s) => (
            <div
              key={s}
              className={`h-2 flex-1 rounded-full transition-colors ${
                s <= step ? 'bg-primary' : 'bg-surfaceHover'
              }`}
            />
          ))}
        </div>
      </div>

      <div className="card p-6">
        {step === 1 && (
          <div className="space-y-6">
            <h2 className="font-display text-xl font-semibold flex items-center gap-2">
              <User className="w-5 h-5 text-primary" />
              Basic Information
            </h2>
            <div className="space-y-2">
              <label className="text-sm text-textMuted">Character Name</label>
              <input
                type="text"
                value={character.name}
                onChange={(e) => setCharacter({ ...character, name: e.target.value })}
                className="input"
                placeholder="Enter your character's name"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm text-textMuted">Race</label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {RACES.map((race) => (
                  <button
                    key={race.id}
                    onClick={() => setCharacter({ ...character, race: race.id })}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      character.race === race.id
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <div className="font-semibold">{race.name}</div>
                    <div className="text-xs text-textMuted">{race.bonus}</div>
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm text-textMuted">Class</label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {CLASSES.map((cls) => (
                  <button
                    key={cls.id}
                    onClick={() => setCharacter({ ...character, class_name: cls.id })}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      character.class_name === cls.id
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <div className="font-semibold">{cls.name}</div>
                    <div className="text-xs text-textMuted">Hit Die: {cls.hitDie}</div>
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm text-textMuted">Background</label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {BACKGROUNDS.map((bg) => (
                  <button
                    key={bg.id}
                    onClick={() => setCharacter({ ...character, background: bg.id })}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      character.background === bg.id
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <div className="font-semibold text-sm">{bg.name}</div>
                    <div className="text-xs text-textMuted">{bg.skills}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6">
            <h2 className="font-display text-xl font-semibold flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              Ability Scores
            </h2>
            
            {!hasRolledOnce && (
              <div className="space-y-4">
                <p className="text-textMuted">
                  Roll all 6 ability scores at once using 4d6, drop the lowest die.
                </p>
                <button
                  onClick={rollAllStats}
                  disabled={rolling}
                  className="btn-primary flex items-center gap-2"
                >
                  <RefreshCw className={`w-5 h-5 ${rolling ? 'animate-spin' : ''}`} />
                  {rolling ? 'Rolling...' : 'Roll All Stats'}
                </button>
                <div className="text-sm text-textMuted">or</div>
                <button onClick={useStandard} className="btn-secondary">
                  Use Standard Array (15, 14, 13, 12, 10, 8)
                </button>
              </div>
            )}

            {hasRolledOnce && (
              <div className="space-y-6">
                <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
                  {STAT_NAMES.map((stat) => {
                    const value = assignedStats[stat]
                    const isAssigned = value !== null
                    const finalStat = getFinalStat(stat)
                    
                    return (
                      <div key={stat} className="space-y-1">
                        <button
                          onClick={() => !useStandardArray && rerollStat(stat)}
                          disabled={rolling || useStandardArray}
                          className={`w-full p-3 rounded-lg border text-center transition-all ${
                            isAssigned && !useStandardArray
                              ? 'border-border hover:border-primary/50 cursor-pointer'
                              : 'border-border'
                          }`}
                        >
                          <div className="text-xs text-textMuted uppercase">
                            {STAT_LABELS[stat]}
                          </div>
                          <div className="text-2xl font-bold">
                            {isAssigned ? finalStat : '-'}
                          </div>
                          {isAssigned && (
                            <div className="text-xs text-textMuted">
                              {getModifier(finalStat)}
                            </div>
                          )}
                        </button>
                        {!useStandardArray && isAssigned && (
                          <button
                            onClick={() => rerollStat(stat)}
                            disabled={rolling || rerollsUsed >= 3}
                            className="text-xs text-primary hover:underline"
                          >
                            Reroll
                          </button>
                        )}
                      </div>
                    )
                  })}
                </div>

                {character.race && allStatsAssigned && (
                  <div className="bg-surfaceHover rounded-lg p-4 space-y-2">
                    <h3 className="font-semibold text-sm">Final Stats (with racial bonuses)</h3>
                    <div className="grid grid-cols-6 gap-2 text-center">
                      {STAT_NAMES.map((stat) => {
                        const finalStat = getFinalStat(stat)
                        const bonus = RACE_BONUSES[character.race as keyof typeof RACE_BONUSES]?.[stat]
                        
                        return (
                          <div key={stat}>
                            <div className="text-xs text-textMuted uppercase">
                              {stat.slice(0, 3)}
                            </div>
                            <div className="font-bold">
                              {finalStat}
                              {bonus ? (
                                <span className="text-xs text-primary"> (+{bonus})</span>
                              ) : null}
                            </div>
                            <div className="text-xs text-textMuted">
                              {getModifier(finalStat)}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {error && (
              <div className="text-red-500 text-sm">{error}</div>
            )}

            {hasRolledOnce && !useStandardArray && (
              <button onClick={rollAllStats} disabled={rolling} className="btn-secondary">
                Reroll All (uses reroll)
              </button>
            )}

            {hasRolledOnce && (
              <button onClick={useStandard} className="btn-secondary">
                Use Standard Array Instead
              </button>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-6">
            <h2 className="font-display text-xl font-semibold flex items-center gap-2">
              <Heart className="w-5 h-5 text-primary" />
              Personality & Backstory
            </h2>
            <div className="space-y-2">
              <label className="text-sm text-textMuted">Personality Traits</label>
              <textarea
                value={character.personality}
                onChange={(e) => setCharacter({ ...character, personality: e.target.value })}
                className="input min-h-[100px]"
                placeholder="How does your character act?"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm text-textMuted">Backstory</label>
              <textarea
                value={character.backstory}
                onChange={(e) => setCharacter({ ...character, backstory: e.target.value })}
                className="input min-h-[150px]"
                placeholder="Where does your character come from?"
              />
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-6">
            <h2 className="font-display text-xl font-semibold flex items-center gap-2">
              <Check className="w-5 h-5 text-primary" />
              Review Character
            </h2>
            <div className="bg-surfaceHover rounded-lg p-6 space-y-4">
              <div className="text-center">
                <h3 className="text-2xl font-display font-bold">{character.name || 'Unnamed'}</h3>
                <p className="text-textMuted">
                  {RACES.find((r) => r.id === character.race)?.name || 'Race'}{' '}
                  {CLASSES.find((c) => c.id === character.class_name)?.name || 'Class'}
                </p>
                <p className="text-sm text-textMuted">
                  {BACKGROUNDS.find((b) => b.id === character.background)?.name || 'Background'}
                </p>
              </div>
              
              {allStatsAssigned && (
                <div className="grid grid-cols-6 gap-2 text-center">
                  {STAT_NAMES.map((stat) => {
                    const finalStat = getFinalStat(stat)
                    const bonus = RACE_BONUSES[character.race as keyof typeof RACE_BONUSES]?.[stat]
                    
                    return (
                      <div key={stat}>
                        <div className="text-xs text-textMuted uppercase">{stat.slice(0, 3)}</div>
                        <div className="font-bold">
                          {finalStat}
                          {bonus ? <span className="text-xs text-primary">+{bonus}</span> : null}
                        </div>
                        <div className="text-xs text-textMuted">{getModifier(finalStat)}</div>
                      </div>
                    )
                  })}
                </div>
              )}
              
              {character.personality && (
                <div>
                  <div className="text-sm text-textMuted mb-1">Personality</div>
                  <p className="text-sm">{character.personality}</p>
                </div>
              )}
              {character.backstory && (
                <div>
                  <div className="text-sm text-textMuted mb-1">Backstory</div>
                  <p className="text-sm">{character.backstory}</p>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="flex justify-between mt-8 pt-6 border-t border-border">
          {step > 1 ? (
            <button onClick={prevStep} className="btn-secondary flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" />
              Previous
            </button>
          ) : (
            <div />
          )}
          {step < totalSteps ? (
            <button
              onClick={nextStep}
              disabled={step === 1 && (!character.name || !character.race || !character.class_name)}
              className="btn-primary flex items-center gap-2"
            >
              Next
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={submitCharacter}
              disabled={loading || !allStatsAssigned}
              className="btn-primary flex items-center gap-2"
            >
              {loading ? 'Creating...' : 'Create Character'}
              <Check className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}