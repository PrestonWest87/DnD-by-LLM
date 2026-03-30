from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
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

app = FastAPI()

# Mount the static directory for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = "phi4-mini:3.8b-q4_K_M"

# --- WebSocket Manager for Map ---
class RoomManager:
    def __init__(self):
        # Maps campaign_id -> list of active WebSockets
        self.active_rooms: dict[int, list[WebSocket]] = defaultdict(list)
        # Maps campaign_id -> dictionary of token states
        self.campaign_states: dict[int, dict] = defaultdict(dict)

    async def connect(self, websocket: WebSocket, campaign_id: int):
        await websocket.accept()
        self.active_rooms[campaign_id].append(websocket)
        # Send current state of THIS campaign to the new connection
        current_state = self.campaign_states.get(campaign_id, {})
        await websocket.send_text(json.dumps(current_state))

    def disconnect(self, websocket: WebSocket, campaign_id: int):
        if websocket in self.active_rooms[campaign_id]:
            self.active_rooms[campaign_id].remove(websocket)

    async def broadcast(self, data: dict, campaign_id: int):
        # Update server state for this specific campaign
        token_id = data.get("id")
        if campaign_id not in self.campaign_states:
             self.campaign_states[campaign_id] = {}
             
        if token_id not in self.campaign_states[campaign_id]:
             self.campaign_states[campaign_id][token_id] = {"x": 0, "y": 0, "color": "#fff"}
             
        self.campaign_states[campaign_id][token_id]["x"] = data["x"]
        self.campaign_states[campaign_id][token_id]["y"] = data["y"]
        
        # Broadcast only to users in this campaign
        for connection in self.active_rooms[campaign_id]:
            await connection.send_text(json.dumps(self.campaign_states[campaign_id]))

room_manager = RoomManager()
# --- Pydantic Schemas for API ---
class ChatRequest(BaseModel):
    message: str

class CharCreate(BaseModel):
    name: str
    char_class: str
    hp: int
    ac: int

# --- Routes ---
@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.websocket("/ws/map")
async def map_socket(websocket: WebSocket):
    await map_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await map_manager.broadcast(json.loads(data))
    except WebSocketDisconnect:
        map_manager.disconnect(websocket)

@app.post("/api/character")
def create_character(char: CharCreate, db: Session = Depends(get_db)):
    db_char = Character(**char.model_dump())
    db.add(db_char)
    db.commit()
    db.refresh(db_char)
    return db_char

@app.get("/api/character")
def get_characters(db: Session = Depends(get_db)):
    return db.query(Character).all()

class UserCreate(BaseModel):
    username: str
    password: str

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

# --- Campaign Routing ---
class CampaignCreate(BaseModel):
    name: str

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
    
    # Logic to link current_user.id to this campaign via a Character or Player junction table goes here
    return {"message": f"Joined campaign {campaign.name}", "campaign_id": campaign.id}

# --- Protected WebSocket Route ---
# WebSockets can't easily send Auth headers in vanilla JS, so we pass the token in the URL query string
@app.websocket("/ws/map/{campaign_id}")
async def map_socket(websocket: WebSocket, campaign_id: int, token: str, db: Session = Depends(get_db)):
    try:
        # Validate the user's token before letting them into the room
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
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # 1. Save User Message
    user_msg = ChatMessage(campaign_id=1, sender_type="player", sender_name="Player 1", content=request.message)
    db.add(user_msg)
    db.commit()

    # 2. Retrieve the Character's Backstory from the SQL database
    # (Assuming we are querying for the active character. Hardcoded ID=1 for this example)
    character = db.query(Character).filter(Character.id == 1).first()
    backstory = character.backstory if character and character.backstory else "A standard adventurer."

    # 3. Retrieve relevant rules from the Vector Database
    relevant_rules = retrieve_relevant_rules(request.message)

    # 4. Construct the Augmented System Prompt
    system_prompt = f"""You are the Dungeon Master. 
    Use the following rules to resolve the player's action if applicable:
    {relevant_rules}
    
    The player's character background:
    {backstory}
    
    Keep your response to 2-3 sentences. Describe the outcome of their action."""

    # 5. Build Message History
    history = db.query(ChatMessage).order_by(ChatMessage.id.desc()).limit(10).all()
    history.reverse()
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        # Map our DB sender_type to Ollama's expected roles
        role = "assistant" if msg.sender_type == "ai_dm" else "user"
        messages.append({"role": role, "content": msg.content})

    # 6. Call Local LLM
    payload = {"model": MODEL_NAME, "messages": messages, "stream": False}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=60.0)
            response.raise_for_status()
            ai_text = response.json().get("message", {}).get("content", "DM is silent.")
        except Exception as e:
            ai_text = f"System Error: {str(e)}"

    # 7. Save AI Response
    ai_msg = ChatMessage(campaign_id=1, sender_type="ai_dm", sender_name="DM", content=ai_text)
    db.add(ai_msg)
    db.commit()

    return {"reply": ai_text}
