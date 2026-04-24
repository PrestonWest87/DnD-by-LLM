# DragonForge Development Progress

**Last Updated:** 2026-04-24 1:55 PM CST
**Status:** Active Development

---

## Current Issues 🔴

### 1. Rooms showing blank screens
- **Status:** SIMPLIFYING (2026-04-24 1:55 PM)
- **Priority:** HIGH
- **Notes:** Simplified GameRoom to minimum - should now show room ID. If still blank, the issue is before rendering.

**Debug Steps Taken:**
- Simplified GameRoom.tsx to basic functionality
- Added console.log for campaignId/roomId
- Added error display
- Removed character/maps/dice complexity

### 2. AI DM not responding
- **Status:** UNTESTED
- **Priority:** HIGH
- **Notes:** 

### 3. Messages not syncing between users
- **Status:** FIXED (2026-04-24)
- **Solution:** Added 3-second polling interval - waiting for room fix to test

---

## Recently Fixed ✅

### 1. Character Creator Stat Rolling
- **Fixed:** 2026-04-24
- **Issue:** Duplicate rolls, Create Character button not working
- **Solution:** Rewrote CharacterCreator.tsx with proper D&D 5e flow (4d6 drop lowest, reroll support)

### 2. Session/Chat Multi-user Issues
- **Fixed:** 2026-04-24
- **Issue:** Sessions shared across all users/campaigns, DM only aware of current user
- **Solution:** 
  - Added `room_id` to Session model
  - Sessions now per-room not global
  - DM prompt includes all party members and messages

### 3. Chat Modes (Action/Speak/Party/DM)
- **Fixed:** 2026-04-24
- **Issue:** No way to do in-character speech vs actions vs party chat
- **Solution:** Added chat mode buttons to GameRoom

### 4. Message Polling
- **Fixed:** 2026-04-24
- **Issue:** Messages not syncing between users
- **Solution:** Added 3-second polling interval in GameRoom

---

## Architecture

### Tech Stack
- **Frontend:** React + Vite + Tailwind
- **Backend:** FastAPI + SQLAlchemy (async)
- **Database:** PostgreSQL (pgvector)
- **Cache:** Redis
- **AI DM:** Ollama (llama3.2:3b)

### Key Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/rooms/{id}/messages` | GET/POST | Chat messages |
| `/api/dm/chat` | POST | AI DM conversation |
| `/api/characters/create-with-rolls` | POST | Create character with stats |
| `/api/maps/generate` | POST | Generate dungeon map |

### Database Schema
- **Campaigns** - Campaign data
- **CampaignMembers** - User roles in campaigns
- **Rooms** - Chat rooms within campaigns
- **Sessions** - Game sessions (per-room now)
- **Characters** - Player characters
- **ChatMessages** - All chat history

---

## Action Items

### For Next Session
1. [ ] Fix blank room screens - check room loading
2. [ ] Verify message sync is working  
3. [ ] Test AI DM response
4. [ ] Add session summary tracking to file

### Later Features
- [ ] DM-triggered map generation (AI decides when to generate maps)
- [ ] Interactive map with player tokens
- [ ] Real-time message sync via WebSocket
- [ ] Character sheet view

---

## Credentials
- **API:** http://localhost:8001
- **Frontend:** http://localhost:3001
- **Database:** localhost:5432
- **Ollama:** http://192.168.1.148:11434

---

## GitHub
- **Repo:** https://github.com/PrestonWest87/DnD-by-LLM
- **Branch:** master