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

# --- WebSocket Manager for Map & Chat ---
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
        # If the payload is a chat message, broadcast it to the room immediately
        if data.get("type") == "chat":
            for connection in self.active_rooms[campaign_id]:
                await connection.send_text(json.dumps(data))
            return

        # Otherwise, update server state for map tokens
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

# --- Pydantic Schemas ---
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

# --- Routes ---
@app.get("/")
async def root():
    return FileResponse("static/index.html")

# --- Auth Routes ---
@app.post("/api/auth/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

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

# --- Character Routes ---
@app.post("/api/character")
def create_character(char: CharCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_char = Character(
        name=char.name,
        owner_id=current_user.id,
        campaign_id=char.campaign_id,
        stats=char.stats,
        backstory=char.backstory
    )
    db.add(db_char)
    db.commit()
    db.refresh(db_char)
    return db_char

@app.get("/api/campaigns/{campaign_id}/my-character")
def get_my_character(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if the active user has a character in this specific campaign
    char = db.query(Character).filter(Character.campaign_id == campaign_id, Character.owner_id == current_user.id).first()
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return char

@app.get("/api/campaigns/{campaign_id}/characters")
def get_campaign_characters(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Fetch the whole party so players can see each other
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
    # 1. Broadcast the user's action to the room immediately so everyone sees it
    await room_manager.broadcast({
        "type": "chat", "sender": request.character_name, "message": request.message, "role": "user"
    }, request.campaign_id)

    # 2. Save User Message to History
    user_msg = ChatMessage(campaign_id=request.campaign_id, sender_type="player", sender_name=request.character_name, content=request.message)
    db.add(user_msg)
    db.commit()

    # 3. Get Context (Backstory & Rules)
    char = db.query(Character).filter(Character.campaign_id == request.campaign_id, Character.owner_id == current_user.id).first()
    backstory = char.backstory if char and char.backstory else "A standard adventurer."
    relevant_rules = retrieve_relevant_rules(request.message)

    system_prompt = f"""You are the Dungeon Master. 
    Use the following rules to resolve the player's action if applicable:
    {relevant_rules}
    
    The player's character background:
    {backstory}
    
    Keep your response to 2-3 sentences. Describe the outcome of their action."""

    # 4. Fetch Campaign History & Call LLM
    history = db.query(ChatMessage).filter(ChatMessage.campaign_id == request.campaign_id).order_by(ChatMessage.id.desc()).limit(10).all()
    history.reverse()
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = "assistant" if msg.sender_type == "ai_dm" else "user"
        messages.append({"role": role, "content": f"[{msg.sender_name}]: {msg.content}"})

    payload = {"model": MODEL_NAME, "messages": messages, "stream": False}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=60.0)
            response.raise_for_status()
            ai_text = response.json().get("message", {}).get("content", "DM is silent.")
        except Exception as e:
            ai_text = f"System Error: {str(e)}"

    # 5. Save and Broadcast AI Response to everyone
    ai_msg = ChatMessage(campaign_id=request.campaign_id, sender_type="ai_dm", sender_name="DM", content=ai_text)
    db.add(ai_msg)
    db.commit()

    await room_manager.broadcast({
        "type": "chat", "sender": "DM", "message": ai_text, "role": "ai"
    }, request.campaign_id)

    return {"status": "success"}
