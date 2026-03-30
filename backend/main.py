from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx
import json
import os

from backend.database import get_db, Character, ChatMessage

app = FastAPI()

# Mount the static directory for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = "phi4-mini:3.8b-q4_K_M"

# --- WebSocket Manager for Map ---
class MapManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        # Support multiple tokens (e.g., Player and Goblin)
        self.tokens = {
            "player": {"x": 100, "y": 100, "color": "#3498db"},
            "goblin": {"x": 300, "y": 200, "color": "#e74c3c"}
        }

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await websocket.send_text(json.dumps(self.tokens))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        # Update state and broadcast
        token_id = data.get("id")
        if token_id in self.tokens:
            self.tokens[token_id]["x"] = data["x"]
            self.tokens[token_id]["y"] = data["y"]
        for connection in self.active_connections:
            await connection.send_text(json.dumps(self.tokens))

map_manager = MapManager()

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
