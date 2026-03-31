from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx
import json
import os
import secrets
import re
import datetime
from collections import defaultdict
from fastapi.security import OAuth2PasswordRequestForm
from backend.auth import get_password_hash, verify_password, create_access_token, get_current_user, verify_ws_token
from backend.database import get_db, Character, ChatMessage, User, Campaign
from backend.rag import retrieve_relevant_rules

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
MODEL_NAME = "phi4-mini:3.8b-q4_K_M"

@app.on_event("startup")
def startup_event():
    from backend.rag import ingest_rulebook, rules_collection
    import httpx
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    if rules_collection.count() == 0:
        if os.path.exists("core_rules.txt"):
            with open("core_rules.txt", "r", encoding="utf-8") as f:
                try:
                    ingest_rulebook(f.read())
                    print("Successfully ingested core_rules.txt into ChromaDB.")
                except httpx.ConnectError:
                    pass

class RoomManager:
    def __init__(self):
        self.active_rooms: dict[int, list[WebSocket]] = defaultdict(list)
        self.campaign_states: dict[int, dict] = defaultdict(dict)
        self.ready_states: dict[int, dict] = defaultdict(dict)
        self.turn_order: dict[int, str] = defaultdict(lambda: "Free Movement")

    async def connect(self, websocket: WebSocket, campaign_id: int):
        await websocket.accept()
        self.active_rooms[campaign_id].append(websocket)
        current_state = self.campaign_states.get(campaign_id, {})
        await websocket.send_text(json.dumps({"type": "state", "data": current_state}))
        await websocket.send_text(json.dumps({"type": "turn_update", "turn": self.turn_order[campaign_id]}))

    async def disconnect(self, websocket: WebSocket, campaign_id: int):
        if websocket in self.active_rooms[campaign_id]:
            self.active_rooms[campaign_id].remove(websocket)

    async def broadcast(self, data: dict, campaign_id: int):
        if data.get("type") in ["chat", "system", "turn_update", "char_update"]:
            for connection in self.active_rooms[campaign_id]:
                await connection.send_text(json.dumps(data))
            return

        if data.get("type") == "move":
            token_id = data.get("id")
            # Enforce turn order logic
            current_turn = self.turn_order[campaign_id]
            if current_turn != "Free Movement" and token_id != current_turn and not token_id.startswith("NPC"):
                return # Block movement if not their turn!

            if token_id not in self.campaign_states[campaign_id]:
                 self.campaign_states[campaign_id][token_id] = {"x": 0, "y": 0, "color": "#fff"}
            self.campaign_states[campaign_id][token_id]["x"] = data["x"]
            self.campaign_states[campaign_id][token_id]["y"] = data["y"]
            for connection in self.active_rooms[campaign_id]:
                await connection.send_text(json.dumps({"type": "state", "data": self.campaign_states[campaign_id]}))

room_manager = RoomManager()

class ChatRequest(BaseModel):
    campaign_id: int
    message: str
    character_name: str
    is_session_start: bool = False

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
    custom_setting: str = ""
    ai_dm: bool = False

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/api/auth/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
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

@app.post("/api/campaigns")
def create_campaign(campaign: CampaignCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dm_id = None if campaign.ai_dm else current_user.id
    new_campaign = Campaign(name=campaign.name, dm_id=dm_id, custom_setting=campaign.custom_setting)
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)
    return {"id": new_campaign.id, "name": new_campaign.name, "invite_code": new_campaign.invite_code}

@app.post("/api/campaigns/join/{invite_code}")
def join_campaign(invite_code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.invite_code == invite_code).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    return {"message": f"Joined", "campaign_id": campaign.id, "campaign_name": campaign.name}

@app.get("/api/campaigns/my")
def get_my_campaigns(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dm_campaigns = db.query(Campaign).filter(Campaign.dm_id == current_user.id).all()
    player_campaign_ids = [c.campaign_id for c in db.query(Character).filter(Character.owner_id == current_user.id).all()]
    player_campaigns = db.query(Campaign).filter(Campaign.id.in_(player_campaign_ids)).all()
    
    results = {}
    for c in dm_campaigns:
        results[c.id] = {"id": c.id, "name": c.name, "role": "DM", "invite_code": c.invite_code, "active": c.is_session_active}
    for c in player_campaigns:
        if c.id not in results:
            results[c.id] = {"id": c.id, "name": c.name, "role": "Player", "invite_code": c.invite_code, "active": c.is_session_active}
    return list(results.values())

@app.post("/api/campaigns/{campaign_id}/generate-outline")
async def generate_campaign_outline(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    characters = db.query(Character).filter(Character.campaign_id == campaign_id).all()
    
    party_desc = "\n".join([f"- {c.name} ({c.stats.get('char_class', 'Unknown')}): {c.backstory}" for c in characters])
    prompt = f"""You are an expert Dungeon Master creating a D&D 5e campaign.
    Setting Notes from Creator: {campaign.custom_setting}
    Party: {party_desc}
    Write a 3-act story outline with specific planned NPCs and encounters. Keep it secret."""
    
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{OLLAMA_URL}/api/generate", json={"model": MODEL_NAME, "prompt": prompt, "stream": False}, timeout=120.0)
        outline = response.json().get("response", "Default Outline.")
            
    campaign.story_outline = outline
    db.commit()
    return {"message": "Outline generated successfully", "outline": outline}

@app.post("/api/character")
def create_character(char: CharCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(Character).filter(Character.campaign_id == char.campaign_id, Character.owner_id == current_user.id).first()
    if existing:
        existing.name = char.name
        existing.stats = char.stats
        existing.backstory = char.backstory
        db.commit()
        db.refresh(existing)
        return existing
    db_char = Character(name=char.name, owner_id=current_user.id, campaign_id=char.campaign_id, stats=char.stats, backstory=char.backstory)
    db.add(db_char)
    db.commit()
    db.refresh(db_char)
    return db_char

@app.get("/api/campaigns/{campaign_id}/characters")
def get_campaign_characters(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Character).filter(Character.campaign_id == campaign_id).all()

@app.get("/api/campaigns/{campaign_id}/my-character")
def get_my_character(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if campaign and campaign.dm_id == current_user.id:
        return {"name": "DM", "role": "DM"}
    char = db.query(Character).filter(Character.campaign_id == campaign_id, Character.owner_id == current_user.id).first()
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return char

@app.get("/api/campaigns/{campaign_id}/chat-history")
def get_chat_history(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    history = db.query(ChatMessage).filter(ChatMessage.campaign_id == campaign_id).order_by(ChatMessage.id.asc()).all()
    return [{"sender": msg.sender_name, "message": msg.content, "role": "ai" if msg.sender_type == "ai_dm" else ("user" if msg.sender_type == "player" else "party")} for msg in history]

@app.websocket("/ws/map/{campaign_id}")
async def map_socket(websocket: WebSocket, campaign_id: int, token: str, db: Session = Depends(get_db)):
    user = verify_ws_token(token, db)
    if not user: return await websocket.close()
    await room_manager.connect(websocket, campaign_id)
    try:
        while True:
            data = await websocket.receive_text()
            await room_manager.broadcast(json.loads(data), campaign_id)
    except WebSocketDisconnect:
        await room_manager.disconnect(websocket, campaign_id)

def parse_ai_commands(ai_response: str, campaign_id: int, db: Session):
    """Intercepts commands like [UPDATE_HP: Cory, -5] and executes them before sending to UI"""
    cleaned_text = ai_response
    
    # 1. Handle HP Updates
    hp_matches = re.finditer(r'\[UPDATE_HP:\s*(.+?),\s*([-+]\d+)\]', ai_response, re.IGNORECASE)
    for match in hp_matches:
        char_name = match.group(1).strip()
        hp_change = int(match.group(2))
        char = db.query(Character).filter(Character.campaign_id == campaign_id, Character.name.ilike(f"%{char_name}%")).first()
        if char:
            stats = char.stats
            stats["hp"] = max(0, stats.get("hp", 0) + hp_change)
            char.stats = stats
            db.commit()
        cleaned_text = cleaned_text.replace(match.group(0), "")

    # 2. Handle Turn Order
    turn_match = re.search(r'\[SET_TURN:\s*(.+?)\]', ai_response, re.IGNORECASE)
    if turn_match:
        turn_target = turn_match.group(1).strip()
        room_manager.turn_order[campaign_id] = turn_target
        cleaned_text = cleaned_text.replace(turn_match.group(0), f"\n**[Turn Order: {turn_target}'s Turn]**\n")

    # 3. Handle Combat End
    if "[END_COMBAT]" in ai_response:
        room_manager.turn_order[campaign_id] = "Free Movement"
        cleaned_text = cleaned_text.replace("[END_COMBAT]", "\n**[Combat Ended. Free Movement Restored]**\n")
        
    return cleaned_text.strip()

@app.post("/api/chat")
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == request.campaign_id).first()
    
    # Timeout Check (45 Minutes)
    now = datetime.datetime.utcnow()
    if campaign.is_session_active and campaign.last_active_time:
        if (now - campaign.last_active_time).total_seconds() > 45 * 60:
            campaign.is_session_active = False
            db.commit()
            return {"error": "Session timed out due to inactivity."}
    
    campaign.last_active_time = now
    
    if request.is_session_start:
        campaign.is_session_active = True
    db.commit()

    await room_manager.broadcast({"type": "chat", "sender": request.character_name, "message": request.message, "role": "user"}, request.campaign_id)
    db.add(ChatMessage(campaign_id=request.campaign_id, sender_type="player", sender_name=request.character_name, content=request.message))
    db.commit()

    # Build the Party Context string so the AI knows EXACTLY who is in the game and their health
    all_chars = db.query(Character).filter(Character.campaign_id == request.campaign_id).all()
    party_context = "Current Party Roster (Use exact names):\n"
    for c in all_chars:
        st = c.stats
        party_context += f"- {c.name}: {st.get('hp')} HP, {st.get('ac')} AC. Weapons: {st.get('equipment', {}).get('weapon')}\n"

    char = db.query(Character).filter(Character.campaign_id == request.campaign_id, Character.owner_id == current_user.id).first()
    relevant_rules = retrieve_relevant_rules(request.message)

    # The New, Aggressive System Prompt
    system_prompt = f"""You are a ruthless, creative, and strictly Rules-As-Written Dungeons & Dragons 5e Dungeon Master.
    Campaign Setting: {campaign.custom_setting}
    Story Outline: {campaign.story_outline}
    {party_context}
    D&D Rules Context: {relevant_rules}
    
    CRITICAL AI DIRECTIVES (DO NOT FAIL THESE):
    1. NEVER repeat the phrase "Would you like an Intelligence check" or similar repetitive loops. You are the DM. You narrate what happens and move the story forward.
    2. YOU decide the consequences. If a player acts stupidly (e.g., throwing their arm), narrate the bloody, painful consequence and apply damage.
    3. TRACK HIT POINTS: If a character takes damage or heals, you MUST include this exact tag at the end of your response: [UPDATE_HP: CharacterName, -X] (e.g., [UPDATE_HP: Cory, -8]).
    4. COMBAT & TURNS: If a fight breaks out, announce initiative and set the turn by outputting: [SET_TURN: CharacterName]. When combat is over, output: [END_COMBAT].
    5. Be decisive. Do not ask permission. Describe the environment, state what the NPCs do, and ask what the specific player whose turn it is does next.
    """

    history = db.query(ChatMessage).filter(ChatMessage.campaign_id == request.campaign_id).order_by(ChatMessage.id.desc()).limit(12).all()
    history.reverse()
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": "assistant" if msg.sender_type == "ai_dm" else "user", "content": f"[{msg.sender_name}]: {msg.content}"})

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{OLLAMA_URL}/api/chat", json={"model": MODEL_NAME, "messages": messages, "stream": False}, timeout=60.0)
            response.raise_for_status()
            ai_text = response.json().get("message", {}).get("content", "The DM ponders in silence.")
        except Exception as e:
            ai_text = f"System Error: ({str(e)})"

    # Parse and execute hidden commands before sending to chat
    processed_ai_text = parse_ai_commands(ai_text, request.campaign_id, db)

    db.add(ChatMessage(campaign_id=request.campaign_id, sender_type="ai_dm", sender_name="DM", content=processed_ai_text))
    db.commit()
    
    await room_manager.broadcast({"type": "chat", "sender": "DM", "message": processed_ai_text, "role": "ai"}, request.campaign_id)
    
    # Broadcast an update signal so the UI refreshes the HP on the character cards
    await room_manager.broadcast({"type": "char_update"}, request.campaign_id)
    # Broadcast turn update
    await room_manager.broadcast({"type": "turn_update", "turn": room_manager.turn_order[request.campaign_id]}, request.campaign_id)

    return {"status": "success"}
