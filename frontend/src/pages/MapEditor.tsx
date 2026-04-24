import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { ArrowLeft, Plus, Settings, Eye, EyeOff } from 'lucide-react'

interface MapCell {
  terrain: string
  features: string[]
  entities: any[]
}

interface MapData {
  id: number
  name: string
  type: string
  width: number
  height: number
  data: {
    grid: MapCell[][]
    rooms: any[]
  }
  explored_cells: Record<string, boolean>
}

const TERRAIN_COLORS: Record<string, string> = {
  floor: '#2a2a3a',
  wall: '#1a1a25',
  corridor: '#3a3a4a',
  door: '#8b5cf6',
  water: '#06b6d4',
  lava: '#ef4444',
  pit: '#000000',
  treasure: '#f59e0b',
  trap: '#dc2626',
  stairs_up: '#22c55e',
  stairs_down: '#f97316',
  counter: '#78350f',
}

export default function MapEditor() {
  const { id, mapId } = useParams()
  const navigate = useNavigate()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [map, setMap] = useState<MapData | null>(null)
  const [loading, setLoading] = useState(true)
  const [cellSize] = useState(12)
  const [showLabels, setShowLabels] = useState(true)

  useEffect(() => {
    loadMap()
  }, [mapId])

  useEffect(() => {
    if (map) {
      renderMap()
    }
  }, [map, showLabels])

  const loadMap = async () => {
    try {
      const response = await api.get(`/maps/${mapId}`)
      setMap(response.data.map)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const renderMap = () => {
    const canvas = canvasRef.current
    if (!canvas || !map) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = map.data.width * cellSize
    canvas.height = map.data.height * cellSize

    ctx.fillStyle = '#0a0a0f'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    for (let y = 0; y < map.data.height; y++) {
      for (let x = 0; x < map.data.width; x++) {
        const cell = map.data.grid[y]?.[x]
        if (cell) {
          ctx.fillStyle = TERRAIN_COLORS[cell.terrain] || '#1a1a25'
          ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize)

          if (showLabels && cell.features.length > 0) {
            ctx.fillStyle = '#e2e8f0'
            ctx.font = '8px sans-serif'
            ctx.textAlign = 'center'
            ctx.fillText(cell.features[0], x * cellSize + cellSize / 2, y * cellSize + cellSize / 2)
          }
        }
      }
    }

    ctx.strokeStyle = '#2a2a3a'
    for (let x = 0; x <= map.data.width; x++) {
      ctx.beginPath()
      ctx.moveTo(x * cellSize, 0)
      ctx.lineTo(x * cellSize, canvas.height)
      ctx.stroke()
    }
    for (let y = 0; y <= map.data.height; y++) {
      ctx.beginPath()
      ctx.moveTo(0, y * cellSize)
      ctx.lineTo(canvas.width, y * cellSize)
      ctx.stroke()
    }
  }

  const handleCellClick = async (x: number, y: number) => {
    try {
      await api.post(`/maps/${mapId}/explore`, { x, y })
      setMap({
        ...map!,
        explored_cells: { ...map!.explored_cells, [`${x},${y}`]: true }
      })
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!map) {
    return <div>Map not found</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="text-textMuted hover:text-text">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="font-display text-2xl font-bold">{map.name}</h1>
            <p className="text-textMuted text-sm">
              {map.type} • {map.width} x {map.height}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowLabels(!showLabels)}
            className={`btn-secondary ${showLabels ? 'text-primary' : ''}`}
          >
            {showLabels ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            Labels
          </button>
        </div>
      </div>

      <div className="card p-4 overflow-auto">
        <canvas
          ref={canvasRef}
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect()
            const x = Math.floor((e.clientX - rect.left) / cellSize)
            const y = Math.floor((e.clientY - rect.top) / cellSize)
            handleCellClick(x, y)
          }}
          style={{ cursor: 'pointer', imageRendering: 'pixelated' }}
        />
      </div>

      <div className="card p-4">
        <h2 className="font-semibold mb-4">Legend</h2>
        <div className="grid grid-cols-4 gap-3">
          {Object.entries(TERRAIN_COLORS).map(([terrain, color]) => (
            <div key={terrain} className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded"
                style={{ backgroundColor: color }}
              />
              <span className="text-sm capitalize">{terrain.replace('_', ' ')}</span>
            </div>
          ))}
        </div>
      </div>

      {map.data.rooms && map.data.rooms.length > 0 && (
        <div className="card p-4">
          <h2 className="font-semibold mb-4">Notable Locations</h2>
          <div className="space-y-2">
            {map.data.rooms.map((room: any, i: number) => (
              <div key={i} className="p-3 bg-surfaceHover rounded-lg flex justify-between">
                <span>{room.name}</span>
                <span className="text-textMuted text-sm">
                  ({room.x}, {room.y})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}