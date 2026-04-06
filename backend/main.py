import os
import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from backend.database import get_db, Character, ChatMessage, Campaign
from backend.ws_manager import room_manager
from backend.ai_engine import generate_ai_response, retrieve_relevant_rules

# Assume backend/auth.py contains your get_current_user and verification logic as before

app = FastAPI()
os.makedirs("./data", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

def parse_ai_commands(ai_response: str, campaign_id: int, db: Session):
    cleaned_text = ai_response
    hp_matches = re.finditer(r'\[UPDATE_HP:\s*(.+?),\s*([-+]\d+)\]', ai_response, re.IGNORECASE)
    
    for match in hp_matches:
        char_name = match.group(1).strip()
        hp_change = int(match.group(2))
        char = db.query(Character).filter(Character.campaign_id == campaign_id, Character.name.ilike(f"%{char_name}%")).first()
        if char:
            # FIX: Create a new dictionary to trigger SQLAlchemy JSON mutation tracking
            new_stats = dict(char.stats)
            new_stats["hp"] = max(0, new_stats.get("hp", 0) + hp_change)
            char.stats = new_stats
            db.commit()
        cleaned_text = cleaned_text.replace(match.group(0), "")

    turn_match = re.search(r'\[SET_TURN:\s*(.+?)\]', ai_response, re.IGNORECASE)
    if turn_match:
        target = turn_match.group(1).strip()
        room_manager.turn_order[campaign_id] = target
        cleaned_text = cleaned_text.replace(turn_match.group(0), f"\n**[Turn Order: {target}'s Turn]**\n")

    return cleaned_text.strip()

@app.websocket("/ws/map/{campaign_id}")
async def map_socket(websocket: WebSocket, campaign_id: int):
    # Setup token verification here
    await room_manager.connect(websocket, campaign_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "move":
                room_manager.update_token(campaign_id, data["id"], data["x"], data["y"])
                await room_manager.broadcast({"type": "state", "data": room_manager.campaign_states[campaign_id]}, campaign_id)
            else:
                await room_manager.broadcast(data, campaign_id)
    except WebSocketDisconnect:
        await room_manager.disconnect(websocket, campaign_id)

# Include the rest of your REST endpoints (register, login, chat) pointing to these refined services
