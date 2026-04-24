# DragonForge Feature Specification

**Last Updated:** 2026-04-24  
**Status:** Implementation In Progress

---

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2026-04-24 | Initial specification | In Progress |

---

# Table of Contents

1. [UI/UX Specifications](#phase-1-uiux-specifications)
2. [Session Management](#phase-2-session-management)
3. [Ready Up System](#phase-3-ready-up-system)
4. [RAG & Context](#phase-4-rag--context)
5. [Campaign & Story](#phase-5-campaign--story)
6. [Map Integration](#phase-6-map-integration)
7. [Technical Implementation](#technical-implementation)

---

# Phase 1: UI/UX Specifications

## 1.1 Game Room Layout

### Desktop (Primary)
```
┌─────────────────────────────────────────────────────────────────┐
│                         HEADER (48px)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────── 60% ──────────────────────────────┐  │
│  │                                                             │  │
│  │                      MAP VIEW                              │  │
│  │                                                             │  │
│  │    🔵 Player Markers    🟣 NPC Markers    🔴 Enemy         │  │
│  │                                                             │  │
│  │                                                             │  │
│  └────────────────────────────── 40% ───────────────────────────┘  │
│                               │                                   │
│  ┌──────────────────────────┴──────────────────────────────┐        │
│  │              OVERLAY PANEL (Modal/Sidebar)                  │        │
│  │  ┌──────────────────────────────────────────────────┐   │        │
│  │  │  Chat / Character / Dice / Initiative          │   │        │
│  │  │                                                │   │        │
│  │  │  Tab Toggle                                     │   │        │
│  │  └──────────────────────────────────────────────────┘   │        │
│  └──────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### Mobile Layout (Split View)
```
┌─────────────────────┐┌─────────────────────┐
│    MAP (50%)        ││   CHAT (50%)        │
│                    ││                    │
│   Tap for          ││   Scrollable       │
│   overlays         ││   messages         │
└─────────────────────┘└─────────────────────┘
```

## 1.2 Visual Design

### Color Palette
| Element | Color | Hex | Usage |
|---------|-------|-----|------|
| Primary | Purple | `#8b5cf6` | Buttons, highlights, player markers |
| Secondary | Cyan | `#06b6d4` | Interactive elements, NPC markers |
| Accent | Gold | `#f59e0b` | Dice, treasures, important items |
| Danger | Red | `#ef4444` | Enemies, damage, errors |
| Success | Green | `#10b981` | Healing, success states |
| Background | Dark | `#0a0a0f` | Main background |
| Surface | Darker | `#12121a` | Cards, panels |
| Border | Gray | `#2a2a3a` | Borders, dividers |

### Typography
- **Display Font:** Cinzel (headers, titles)
- **Body Font:** Inter (messages, UI)

## 1.3 Chat UI Components

### Message Display
- [x] Scrollable container with fixed height
- [x] Message type indicators (DM/Action/Speak/Party)
- [x] Character name badges
- [x] Formatted content (dice rolls, HP changes)
- [x] Timestamps

### Input Bar
- [x] Fixed at bottom of chat panel
- [x] Mode tabs (Action/Speak/Party/DM)
- [x] Ready button integrated

### Overlay Panels (Modal Dialogs)
| Panel | Trigger | Content |
|-------|---------|---------|
| Character | Click character | HP, AC, Level, Stats |
| Dice | Click dice icon | Dice roller |
| Initiative | Click sword icon | Turn order, conditions |
| Map Controls | Auto | Zoom, pan, Fog of War |

## 1.4 Character Auto-Selection
- [x] Auto-select user's character on room entry
- [x] Filter by `user_id === currentUser.id`
- [x] Visual indicator of selected character
- [x] Easy switch between owned characters

---

# Phase 2: Session Management

## 2.1 Session Flow

```
Player Enters Room
       ↓
Check for Active Session
       ↓
   ┌───┴───┐
   ↓       ↓
Exists?  No
   ↓       ↓
Load     Trigger "Start New Session"
Summary     ↓
   ↓   ┌───┴───┐
   ↓   ↓       ↓
Prepend Summary to DM Prompt  DM triggers Ready Up
Build context for player              ↓
       ↓                    Wait for All Players Ready
Join active session                  ↓
       ↓                    Trigger Session Start
Show map + chat                     ↓
                            Generate Map (if new session)
                            Load Map (if continuation)
```

## 2.2 Session Summary System

### Running Summary
- **Update Frequency:** After every DM message
- **Format:** Concise narrative of key events
- **Retention:** In session, included in every DM prompt
- **Example:**
```
SESSION_SUMMARY: The party entered the ancient tomb. Found a golden amulet in the first chamber. 
Grom the fighter took 5 damage from a trap. They are now exploring the inner sanctum.
```

### End of Session Summary
- **Trigger:** Manual (DM clicks "End Session") or timeout (1hr inactivity)
- **Format:** Full narrative paragraph (100-200 words)
- **Contents:**
  - What happened
  - Key decisions made
  - NPCs encountered
  - Quests/goals established
  - Treasure acquired

### Database Schema
```python
class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"))
    number = Column(Integer)
    title = Column(String(200))
    summary = Column(Text)  # End of session summary
    running_summary = Column(Text)  # Current running summary
    status = Column(String(20), default="active")  # active/completed
    created_at = Column(DateTime(timezone=True), default=func.now())
```

### API Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/sessions/room/{room_id}` | GET | Get active session |
| `/api/sessions/{id}/summary` | GET/POST | Get/update running summary |
| `/api/sessions/{id}/end` | POST | End session, save summary |
| `/api/sessions/{room_id}/message` | POST | Add message with summary update |

---

# Phase 3: Ready Up System

## 3.1 Ready States

### Player Ready Table
```python
class PlayerReady(Base):
    __tablename__ = "player_ready"
    
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    character_id = Column(Integer, ForeignKey("characters.id"))
    is_ready = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), default=func.now())
```

## 3.2 Ready Flow
```
Player clicks "Ready"
        ↓
Update PlayerReady.is_ready = TRUE
        ↓
Check: Are ALL players ready?
        ↓
    ┌───┴───┐
    ↓       ↓
 Yes      No
    ↓       
Notify DM: "All players ready. Begin session when ready."
        ↓
DM triggers session start
        ↓
Generate/Load map
        ↓
Begin gameplay
```

## 3.3 API Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/rooms/{room_id}/ready` | POST | Toggle ready state |
| `/api/rooms/{room_id}/ready` | GET | Get all ready states |
| `/api/rooms/{room_id}/all-ready` | GET | Check if all ready |

---

# Phase 4: RAG & Context

## 4.1 Enhanced Context Building

Every DM prompt includes:
```python
context = {
    "session_summary": running_summary,      # From session table
    "recent_messages": last_10_messages,   # Chat history
    "story_outline": campaign.story_outline,  # Campaign story
    "character_context": player_stats,    # Current character
    "rag_retrieved": rules_etc,            # RAG search results
    "map_description": current_map_state  # Map entities
}
```

## 4.2 Session-Aware RAG

When querying RAG:
1. Include session summary in search context
2. Prioritize rules relevant to current events
3. Include historical summaries in retrieval

---

# Phase 5: Campaign & Story

## 5.1 Story Visibility

| Role | Can View Story | Can Edit Story |
|------|----------------|----------------|
| Campaign Owner | ✅ | ✅ |
| DM (member role) | ✅ | ✅ |
| Player | ❌ | ❌ |

## 5.2 Owner-Only Settings

Hidden from non-owners:
- Story outline editing
- DM mode switching (AI/Human)
- Settings panel
- Delete campaign option

## 5.3 Human DM Features

- Manual story outline writing
- Notes section (private DM notepad)
- Manual session summaries
- NPC name/motivation notes

## 5.4 AI DM Spoiler Prevention

AI DM receives story outline in prompts:
```
STORY_CONTEXT (For DM only - do not reveal to players):
{campaign.story_outline}
```

Players see:
```
(No story details visible)
```

---

# Phase 6: Map Integration

## 6.1 Map as Primary View

- **Default:** Map takes 60% of screen
- **Interactive:** Players can pan/zoom
- **Fog of War:** Areas not yet explored are hidden

## 6.2 Marker System

| Marker Type | Color | Hex | Visible To |
|------------|-------|-----|-------------|
| Player Characters | Cyan | `#06b6d4` | All players |
| NPCs (Friendly) | Purple | `#8b5cf6` | Players who've met |
| NPCs (Hostile) | Red | `#ef4444` | Only DM initially |
| Enemies | Red | `#ef4444` | DM only until discovered |
| Treasure | Gold | `#f59e0b` | All (when found) |
| Exit/Entrance | Green | `#10b981` | All |

## 6.3 Session Map Flow

```
Session Start (New)
        ↓
DM triggers map generation
        ↓
Generate with selected theme/difficulty
        ↓
Place entrance marker
        ↓
Begin gameplay

Session Start (Continuation)
        ↓
Check for existing map in room
        ↓
Load existing CampaignMap
        ↓
Resume at last known position
```

## 6.4 Map Generation Triggers

- **New Session:** DM clicks "Start Session" → Generate map
- **Continuation:** Auto-load existing map
- **Manual:** DM can regenerate via map controls

---

# Technical Implementation

## File Changes Summary

### Database (`backend/app/db/database.py`)
```python
# New columns on campaigns table:
- notes: Text
- session_summary: Text
- last_session_id: Integer

# New columns on rooms table:
- map_id: Integer (FK)
- is_active_session: Boolean

# New table:
- PlayerReady
```

### API Files

| File | Changes |
|------|---------|
| `backend/app/api/sessions.py` | NEW - Session management |
| `backend/app/api/rooms.py` | Add ready endpoints |
| `backend/app/api/dm.py` | Add summary, context |
| `backend/app/api/map_routes.py` | Add session map endpoints |

### Frontend Files

| File | Changes |
|------|---------|
| `frontend/src/pages/GameRoom.tsx` | Complete overhaul |
| `frontend/src/pages/Campaign.tsx` | Owner-only settings |
| `frontend/src/pages/MapEditor.tsx` | Marker rendering |

---

# Implementation Order

1. **Database Schema** - Foundation
2. **Session API** - Core functionality  
3. **DM Enhancement** - AI context
4. **Ready System** - Gameplay flow
5. **Map Integration** - Visual base
6. **Chat UI** - Player interaction
7. **Phase 7 Polish** - Final tweaks

---

# Questions / Trade-offs (Resolved)

- [x] Map as default view? **YES** - 60% screen
- [x] Overlay style? **Modal dialogs**
- [x] Default chat? **Same as current** - toggleable
- [x] Initiative? **Both** - dots on map + sidebar panel
- [x] Mobile? **Split view** - 50/50
- [x] Auto-summary frequency? **Every DM message**
- [x] Position visibility? **Within visibility range**

---

# Checklist

## Phase 1: UI/UX
- [ ] Map 60%, overlay panel 40% layout
- [ ] Purple/cyan/gold color scheme
- [ ] Scrollable message container
- [ ] Fixed input bar
- [ ] Character auto-selection
- [ ] Modal dialogs for panels

## Phase 2: Session
- [ ] Running summary (after DM message)
- [ ] End of session summary
- [ ] Summary in DM prompts
- [ ] Session continuation logic

## Phase 3: Ready Up
- [ ] Ready button
- [ ] Ready state tracking
- [ ] All-ready check
- [ ] DM notification

## Phase 4: RAG
- [ ] Summary in retrieval
- [ ] Enhanced context building
- [ ] RAG + history query

## Phase 5: Campaign
- [ ] Owner-only settings visibility
- [ ] Story hidden from players
- [ ] Notes section
- [ ] Human DM writing

## Phase 6: Map
- [ ] Map as primary view
- [ ] Player markers (cyan)
- [ ] NPC markers (purple)
- [ ] Enemy markers (red)
- [ ] Session continuation
- [ ] DM-triggered generation