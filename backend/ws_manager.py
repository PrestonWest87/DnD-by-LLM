from fastapi import WebSocket
import json
from collections import defaultdict

class RoomManager:
    def __init__(self):
        self.active_rooms = defaultdict(list)
        self.campaign_states = defaultdict(dict)
        self.turn_order = defaultdict(lambda: "Free Movement")

    async def connect(self, websocket: WebSocket, campaign_id: int):
        await websocket.accept()
        self.active_rooms[campaign_id].append(websocket)
        await websocket.send_text(json.dumps({"type": "state", "data": self.campaign_states[campaign_id]}))
        await websocket.send_text(json.dumps({"type": "turn_update", "turn": self.turn_order[campaign_id]}))

    async def disconnect(self, websocket: WebSocket, campaign_id: int):
        if websocket in self.active_rooms[campaign_id]:
            self.active_rooms[campaign_id].remove(websocket)

    async def broadcast(self, data: dict, campaign_id: int):
        for connection in self.active_rooms[campaign_id]:
            await connection.send_text(json.dumps(data))

    def update_token(self, campaign_id: int, token_id: str, x: int, y: int):
        if token_id not in self.campaign_states[campaign_id]:
            self.campaign_states[campaign_id][token_id] = {"x": 0, "y": 0, "color": "#fff"}
        self.campaign_states[campaign_id][token_id]["x"] = x
        self.campaign_states[campaign_id][token_id]["y"] = y

room_manager = RoomManager()
