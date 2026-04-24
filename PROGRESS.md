# DragonForge Development Progress

**Last Updated:** 2026-04-24 2:35 PM CST
**Status:** Active Development

---

## Completed This Session ✅

### 1. Message & AI Fixes
- AI DM won't speak for player characters (dm.py updated)
- Auto-select user's character on room entry
- Message formatting: dice rolls, HP, markdown

### 2. Initiative System
- `Encounter`, `InitiativeEntry`, `PlayerResponse` tables
- Full API: create, join, roll, next-turn, damage
- Player response tracking for DM prompts

### 3. UI Overhaul
- Grid background, glow effects
- Enhanced header with gradient logo
- GameRoom: collapsible sidebar, HP bars, initiative panel
- Dashboard: quick actions, improved campaign cards
- Mobile responsiveness

### 4. Map Generation
- **4 Algorithms**: standard, BSP, cellular automata, roguelike
- **7 Dungeon Themes**: standard, cave, crypt, fortress, underdark, temple, mine
- **7 Wilderness Biomes**: forest, desert, arctic, jungle, swamp, coastal, mountain
- **3 Settlement Types**: village, town, city
- Rich descriptions, enemy types, treasure types per theme

---

## Architecture

### Tech Stack
- **Frontend:** React + Vite + Tailwind
- **Backend:** FastAPI + SQLAlchemy (async)
- **Database:** PostgreSQL (pgvector)
- **AI DM:** Ollama (llama3.2:3b)

### New API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/encounters/` | POST | Create encounter |
| `/api/encounters/room/{room_id}` | GET | Get active encounter |
| `/api/encounters/{id}/join` | POST | Join encounter |
| `/api/encounters/{id}/roll` | POST | Roll initiative |
| `/api/encounters/{id}/next-turn` | POST | Advance turn |
| `/api/encounters/{id}/damage` | POST | Apply damage |
| `/api/encounters/{id}/prompt` | POST | Create player prompt |
| `/api/encounters/{id}/respond` | POST | Respond to prompt |

### Database Schema Added
```sql
CREATE TABLE encounters (
  id, room_id, map_id, name, status, current_turn, round
);

CREATE TABLE initiative_entries (
  id, encounter_id, character_id, initiative_roll,
  initiative_modifier, turn_order, is_active, hp_remaining, conditions
);

CREATE TABLE player_responses (
  id, encounter_id, room_id, character_id, prompt, response, responded
);
```

---

## What's Working ✅

### Completed Features
- Campaign management (create, join, start sessions)
- AI DM chat with character stats, story outline
- Character creation with D&D 5e rules
- Inventory management system
- Session persistence (chat history in rooms)
- Auth persistence on page refresh
- dm_mode check (human vs AI DM)
- **NEW: AI DM won't speak as players**
- **NEW: Auto-select user's character**
- **NEW: Message formatting**
- **NEW: Initiative system**
- **NEW: Player response tracking**

---

## Credentials
- **API:** http://localhost:8001
- **Frontend:** http://localhost:3001
- **Database:** localhost:5432
- **Ollama:** http://192.168.1.148:11434