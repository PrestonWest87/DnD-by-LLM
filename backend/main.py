from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx
import json
import os
from collections import defaultdict
from fastapi.security import OAuth2PasswordRequestForm
from backend.auth import get_password_hash, verify_password, create_access_token, get_current_user
from backend.database import get_db, Character, ChatMessage, User, Campaign
from backend.rag import retrieve_relevant_rules

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = "phi4-mini:3.8b-q4_K_M"

class RoomManager:
    def __init__(self):
        self.active_rooms: dict[int, list[WebSocket]] = defaultdict(list)
        self.campaign_states: dict[int, dict] = defaultdict(dict)

    async def connect(self, websocket: WebSocket, campaign_id: int):
        await websocket.accept()
        self.active_rooms[campaign_id].append(websocket)
        current_state = self.campaign_states.get(campaign_id, {})
        await websocket.send_text(json.dumps({"type": "state", "data": current_state}))

    def disconnect(self, websocket: WebSocket, campaign_id: int):
        if websocket in self.active_rooms[campaign_id]:
            self.active_rooms[campaign_id].remove(websocket)

    async def broadcast(self, data: dict, campaign_id: int):
        if data.get("type") == "chat":
            for connection in self.active_rooms[campaign_id]:
                await connection.send_text(json.dumps(data))
            return

        if data.get("type") == "move":
            token_id = data.get("id")
            if campaign_id not in self.campaign_states:
                 self.campaign_states[campaign_id] = {}
            if token_id not in self.campaign_states[campaign_id]:
                 self.campaign_states[campaign_id][token_id] = {"x": 0, "y": 0, "color": "#fff"}
            self.campaign_states[campaign_id][token_id]["x"] = data["x"]
            self.campaign_states[campaign_id][token_id]["y"] = data["y"]
            for connection in self.active_rooms[campaign_id]:
                await connection.send_text(json.dumps({"type": "state", "data": self.campaign_states[campaign_id]}))

room_manager = RoomManager()

# --- Schemas ---
class ChatRequest(BaseModel):
    campaign_id: int
    message: str
    character_name: str

class CharCreate(BaseModel):
    name: str
    campaign_id: int
    stats: dict
    backstory: str = "A standard adventurer."

class UserCreate(BaseModel):
    username: str
    password: str

class CampaignCreate(BaseModel):
    name: str

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# --- Auth Routes ---
@app.post("/api/auth/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    new_user = User(username=user.username, hashed_password=get_password_hash(user.password))
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"access_token": create_access_token(data={"sub": user.username}), "token_type": "bearer"}

# --- Campaign Routes ---
@app.post("/api/campaigns")
def create_campaign(campaign: CampaignCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_campaign = Campaign(name=campaign.name, dm_id=current_user.id)
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)
    return {"id": new_campaign.id, "name": new_campaign.name, "invite_code": new_campaign.invite_code}

@app.post("/api/campaigns/join/{invite_code}")
def join_campaign(invite_code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.invite_code == invite_code).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    return {"message": f"Joined campaign {campaign.name}", "campaign_id": campaign.id, "campaign_name": campaign.name}

# NEW: Dashboard Endpoint
@app.get("/api/campaigns/my")
def get_my_campaigns(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dm_campaigns = db.query(Campaign).filter(Campaign.dm_id == current_user.id).all()
    chars = db.query(Character).filter(Character.owner_id == current_user.id).all()
    player_campaign_ids = [c.campaign_id for c in chars]
    player_campaigns = db.query(Campaign).filter(Campaign.id.in_(player_campaign_ids)).all()
    
    results = {}
    for c in dm_campaigns:
        results[c.id] = {"id": c.id, "name": c.name, "role": "DM", "invite_code": c.invite_code}
    for c in player_campaigns:
        if c.id not in results:
            results[c.id] = {"id": c.id, "name": c.name, "role": "Player", "invite_code": c.invite_code}
    return list(results.values())

# --- Character Routes ---
@app.post("/api/character")
def create_character(char: CharCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_char = Character(name=char.name, owner_id=current_user.id, campaign_id=char.campaign_id, stats=char.stats, backstory=char.backstory)
    db.add(db_char)
    db.commit()
    db.refresh(db_char)
    return db_char

@app.get("/api/campaigns/{campaign_id}/my-character")
def get_my_character(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if user is the DM. If so, they don't need a character sheet.
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if campaign and campaign.dm_id == current_user.id:
        return {"name": "DM", "role": "DM"}

    char = db.query(Character).filter(Character.campaign_id == campaign_id, Character.owner_id == current_user.id).first()
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return char

@app.get("/api/campaigns/{campaign_id}/characters")
def get_campaign_characters(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Character).filter(Character.campaign_id == campaign_id).all()

# --- WebSocket & AI Chat ---
@app.websocket("/ws/map/{campaign_id}")
async def map_socket(websocket: WebSocket, campaign_id: int, token: str, db: Session = Depends(get_db)):
    try:
        user = get_current_user(token, db)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await room_manager.connect(websocket, campaign_id)
    try:
        while True:
            data = await websocket.receive_text()
            await room_manager.broadcast(json.loads(data), campaign_id)
    except WebSocketDisconnect:
        room_manager.disconnect(websocket, campaign_id)

@app.post("/api/chat")
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    await room_manager.broadcast({"type": "chat", "sender": request.character_name, "message": request.message, "role": "user"}, request.campaign_id)
    db.add(ChatMessage(campaign_id=request.campaign_id, sender_type="player", sender_name=request.character_name, content=request.message))
    db.commit()

    char = db.query(Character).filter(Character.campaign_id == request.campaign_id, Character.owner_id == current_user.id).first()
    backstory = char.backstory if char and char.backstory else "A standard adventurer."
    stats_str = ", ".join([f"{k.upper()}: {v}" for k, v in char.stats.items()]) if char and char.stats else "Unknown"
    relevant_rules = retrieve_relevant_rules(request.message)

    system_prompt = f"""You are the Dungeon Master. 
    Rules Context: {relevant_rules}
    Player Sheet: Name: {request.character_name}, {stats_str}, Background: {backstory}
    Keep response to 2-3 sentences. Describe the outcome taking their specific character stats and modifiers into account."""

    history = db.query(ChatMessage).filter(ChatMessage.campaign_id == request.campaign_id).order_by(ChatMessage.id.desc()).limit(10).all()
    history.reverse()
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": "assistant" if msg.sender_type == "ai_dm" else "user", "content": f"[{msg.sender_name}]: {msg.content}"})

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{OLLAMA_URL}/api/chat", json={"model": MODEL_NAME, "messages": messages, "stream": False}, timeout=60.0)
            response.raise_for_status()
            ai_text = response.json().get("message", {}).get("content", "DM is silent.")
        except Exception as e:
            ai_text = f"System Error: {str(e)}"

    db.add(ChatMessage(campaign_id=request.campaign_id, sender_type="ai_dm", sender_name="DM", content=ai_text))
    db.commit()
    await room_manager.broadcast({"type": "chat", "sender": "DM", "message": ai_text, "role": "ai"}, request.campaign_id)
    return {"status": "success"}
