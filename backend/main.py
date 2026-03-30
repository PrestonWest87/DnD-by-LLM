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
    import os
    import httpx
    
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    
    if rules_collection.count() == 0:
        if os.path.exists("core_rules.txt"):
            with open("core_rules.txt", "r", encoding="utf-8") as f:
                try:
                    ingest_rulebook(f.read())
                    print("Successfully ingested core_rules.txt into ChromaDB.")
                except httpx.ConnectError:
                    print("CRITICAL WARNING: Could not connect to Ollama at startup. RAG ingestion failed.")

class RoomManager:
    def __init__(self):
        self.active_rooms: dict[int, list[WebSocket]] = defaultdict(list)
        self.campaign_states: dict[int, dict] = defaultdict(dict)
        self.ready_states: dict[int, dict] = defaultdict(dict)

    async def connect(self, websocket: WebSocket, campaign_id: int):
        await websocket.accept()
        self.active_rooms[campaign_id].append(websocket)
        current_state = self.campaign_states.get(campaign_id, {})
        await websocket.send_text(json.dumps({"type": "state", "data": current_state}))
        await websocket.send_text(json.dumps({"type": "ready_update", "states": self.ready_states.get(campaign_id, {})}))

    async def disconnect(self, websocket: WebSocket, campaign_id: int):
        if websocket in self.active_rooms[campaign_id]:
            self.active_rooms[campaign_id].remove(websocket)
            await self.broadcast({"type": "system", "action": "reload_party"}, campaign_id)

    async def broadcast(self, data: dict, campaign_id: int):
        if data.get("type") in ["chat", "system"]:
            for connection in self.active_rooms[campaign_id]:
                await connection.send_text(json.dumps(data))
            return

        if data.get("type") == "ready_toggle":
            char_name = data.get("character_name")
            is_ready = data.get("is_ready")
            self.ready_states[campaign_id][char_name] = is_ready
            for connection in self.active_rooms[campaign_id]:
                await connection.send_text(json.dumps({"type": "ready_update", "states": self.ready_states[campaign_id]}))
            return

        if data.get("type") == "move":
            token_id = data.get("id")
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
    ai_dm: bool = False

@app.get("/")
async def root():
    return FileResponse("static/index.html")

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

@app.post("/api/campaigns")
def create_campaign(campaign: CampaignCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dm_id = None if campaign.ai_dm else current_user.id
    new_campaign = Campaign(name=campaign.name, dm_id=dm_id)
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

@app.post("/api/campaigns/{campaign_id}/generate-outline")
async def generate_campaign_outline(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    characters = db.query(Character).filter(Character.campaign_id == campaign_id).all()
    
    party_desc = "\n".join([f"- {c.name} ({c.stats.get('char_class', 'Unknown')}): {c.backstory}" for c in characters])
    prompt = f"""You are an expert Dungeon Master creating a new D&D 5e campaign named '{campaign.name}'.
    The party consists of:
    {party_desc}
    
    Write a concise, 3-act story outline with 3 planned combat encounters. Do not reveal this to the players. This is your secret DM notes."""
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate", 
                json={"model": MODEL_NAME, "prompt": prompt, "stream": False}, 
                timeout=120.0
            )
            response.raise_for_status()
            outline = response.json().get("response", "Default Outline.")
        except Exception as e:
            outline = f"Failed to generate outline: {str(e)}"
            
    campaign.story_outline = outline
    db.commit()
    return {"message": "Outline generated successfully", "outline": outline}


# NEW: Background Processing Function
def process_rulebook(content: bytes, filename: str):
    try:
        print(f"Starting to process massive rulebook: {filename}")
        if filename.endswith('.pdf'):
            import PyPDF2
            import io
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
        else:
            text = content.decode("utf-8")
            
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = splitter.split_text(text)
        
        print(f"Book parsed. Split into {len(chunks)} chunks. Beginning database ingestion...")
        
        from backend.rag import rules_collection
        
        # Batching to prevent overwhelming memory or Ollama connection limits
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            ids = [f"rule_{secrets.token_hex(4)}" for _ in batch_chunks]
            if batch_chunks:
                rules_collection.upsert(documents=batch_chunks, ids=ids)
            print(f"Embedded batch {i//batch_size + 1} of {(len(chunks)//batch_size) + 1}...")
            
        print(f"Finished successfully embedding {filename} into the AI's memory!")
    except Exception as e:
        print(f"CRITICAL ERROR processing rulebook {filename}: {str(e)}")


@app.post("/api/upload-rules")
async def upload_rules(background_tasks: BackgroundTasks, file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    content = await file.read()
    
    # Hand the heavy lifting off to the background task
    background_tasks.add_task(process_rulebook, content, file.filename)
    
    # Immediately tell the browser we caught it so it doesn't time out
    return {"message": "Upload caught! The AI is reading the rulebook in the background. Check your server console for progress."}


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

@app.get("/api/campaigns/{campaign_id}/my-character")
def get_my_character(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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

@app.get("/api/campaigns/{campaign_id}/chat-history")
def get_chat_history(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    history = db.query(ChatMessage).filter(ChatMessage.campaign_id == campaign_id).order_by(ChatMessage.id.asc()).all()
    formatted = []
    for msg in history:
        role = "ai" if msg.sender_type == "ai_dm" else ("user" if msg.sender_type == "player" else "party")
        formatted.append({"sender": msg.sender_name, "message": msg.content, "role": role})
    return formatted

@app.websocket("/ws/map/{campaign_id}")
async def map_socket(websocket: WebSocket, campaign_id: int, token: str, db: Session = Depends(get_db)):
    user = verify_ws_token(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    await room_manager.connect(websocket, campaign_id)
    await room_manager.broadcast({"type": "system", "action": "reload_party"}, campaign_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            await room_manager.broadcast(json.loads(data), campaign_id)
    except WebSocketDisconnect:
        await room_manager.disconnect(websocket, campaign_id)

@app.post("/api/chat")
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    await room_manager.broadcast({"type": "chat", "sender": request.character_name, "message": request.message, "role": "user"}, request.campaign_id)
    db.add(ChatMessage(campaign_id=request.campaign_id, sender_type="player", sender_name=request.character_name, content=request.message))
    db.commit()

    char = db.query(Character).filter(Character.campaign_id == request.campaign_id, Character.owner_id == current_user.id).first()
    backstory = char.backstory if char and char.backstory else "A standard adventurer."
    stats_str = ", ".join([f"{k.upper()}: {v}" for k, v in char.stats.items()]) if char and char.stats else "Unknown"
    relevant_rules = retrieve_relevant_rules(request.message)

    campaign = db.query(Campaign).filter(Campaign.id == request.campaign_id).first()
    outline = campaign.story_outline if campaign.story_outline else "No outline set. Generate a creative starting scenario."

    system_prompt = f"""You are an expert Dungeon Master running a strictly Rules-As-Written Dungeons & Dragons 5e campaign.
    Campaign Secret Outline: {outline}
    D&D 5e Rulebook Context: {relevant_rules}
    Current Player: {request.character_name}, Stats: {stats_str}, Background: {backstory}
    
    DIRECTIVES:
    1. ACT ENTIRELY AS THE DUNGEON MASTER. Never break character.
    2. Narrate the environment and the results of player actions.
    3. Require the player to make specific 1d20 rolls (e.g., 'Make a DC 15 Dexterity saving throw' or 'Roll a Perception check') when the outcome of an action is uncertain.
    4. Keep responses immersive but concise (2-4 sentences max)."""

    history = db.query(ChatMessage).filter(ChatMessage.campaign_id == request.campaign_id).order_by(ChatMessage.id.desc()).limit(15).all()
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
            ai_text = f"System Error: The fabric of reality stutters. ({str(e)})"

    db.add(ChatMessage(campaign_id=request.campaign_id, sender_type="ai_dm", sender_name="DM", content=ai_text))
    db.commit()
    await room_manager.broadcast({"type": "chat", "sender": "DM", "message": ai_text, "role": "ai"}, request.campaign_id)
    return {"status": "success"}
