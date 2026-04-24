import os
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.database import (
    Session, ChatMessage, CampaignEmbedding, SRDRule,
    Campaign, CampaignMap
)
from app.services.ollama_client import OllamaClient


class RAGService:
    MAX_CONTEXT_TOKENS = 4000
    SESSION_SUMMARY_THRESHOLD = 10

    def __init__(self):
        self.ollama = OllamaClient()

    async def get_campaign_context(
        self,
        campaign_id: int,
        db: AsyncSession,
        include_maps: bool = True
    ) -> Dict[str, Any]:
        campaign = await db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = campaign.scalar_one_or_none()

        recent_sessions = await db.execute(
            select(Session)
            .where(Session.campaign_id == campaign_id)
            .order_by(desc(Session.number))
            .limit(3)
        )
        recent_sessions = recent_sessions.scalars().all()

        context = {
            "campaign_name": campaign.name if campaign else "",
            "story_outline": campaign.story_outline if campaign else "",
            "recent_sessions": [
                {
                    "number": s.number,
                    "title": s.title,
                    "summary": s.summary
                }
                for s in recent_sessions if s.summary
            ]
        }

        if include_maps:
            maps = await db.execute(
                select(CampaignMap).where(CampaignMap.campaign_id == campaign_id)
            )
            context["maps"] = [
                {
                    "id": m.id,
                    "name": m.name,
                    "type": m.data.get("type", "unknown") if m.data else "unknown"
                }
                for m in maps.scalars().all()
            ]

        return context

    async def get_session_messages(
        self,
        session_id: int,
        db: AsyncSession,
        limit: int = 50
    ) -> List[Dict[str, str]]:
        messages = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.room_id == session_id)
            .order_by(ChatMessage.timestamp)
            .limit(limit)
        )
        return [
            {
                "type": m.message_type,
                "content": m.content,
                "timestamp": str(m.timestamp)
            }
            for m in messages.scalars().all()
        ]

    async def summarize_old_sessions(
        self,
        campaign_id: int,
        db: AsyncSession
    ) -> str:
        sessions = await db.execute(
            select(Session)
            .where(Session.campaign_id == campaign_id)
            .order_by(desc(Session.number))
            .offset(5)
            .limit(10)
        )
        sessions = sessions.scalars().all()

        if not sessions:
            return ""

        combined_summary = "Historical session summaries:\n"
        for session in reversed(sessions):
            if session.summary:
                combined_summary += f"- Session {session.number}: {session.summary}\n"

        condensed = await self.ollama.chat(
            messages=[{
                "role": "user",
                "content": f"Condense this summary into 2-3 bullet points:\n{combined_summary}"
            }],
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        )

        return condensed

    async def search_rules(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        query_embedding = await self.ollama.generate_embedding(query)

        result = await db.execute(
            select(SRDRule)
            .order_by(SRDRule.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )

        return [
            {
                "title": rule.title,
                "category": rule.category,
                "content": rule.content
            }
            for rule in result.scalars().all()
        ]

    async def build_dm_context(
        self,
        room_id: int,
        db: AsyncSession,
        player_input: str
    ) -> str:
        system_parts = []

        system_parts.append(
            "You are a creative and skilled D&D 5e Dungeon Master. "
            "Follow these guidelines:\n"
            "1. Describe scenes vividly but concisely\n"
            "2. React to player actions with consequences\n"
            "3. Follow D&D 5e rules when applicable\n"
            "4. Maintain narrative momentum\n"
            "5. Make rulings that keep the game fun\n"
        )

        return "\n\n".join(system_parts)

    async def get_character_context(
        self,
        character_id: int,
        db: AsyncSession
    ) -> str:
        from app.db.database import Character
        character = await db.execute(
            select(Character).where(Character.id == character_id)
        )
        character = character.scalar_one_or_none()

        if not character:
            return ""

        return (
            f"Character: {character.name}\n"
            f"Race: {character.race}\n"
            f"Class: {character.class_name} (Level {character.level})\n"
            f"HP: {character.hp}/{character.max_hp}\n"
            f"AC: {character.ac}\n"
            f"Stats: {character.stats}\n"
            f"Saving Throws: {character.saving_throws}\n"
            f"Skills: {character.skills}\n"
            f"Equipment: {character.equipment}\n"
            f"Features: {character.features}\n"
            f"Personality: {character.personality}\n"
            f"Backstory: {character.backstory}"
        )

    def format_map_description(
        self,
        map_data: Dict[str, Any],
        entities: List[Dict[str, Any]] = None
    ) -> str:
        description = f"Map: {map_data.get('name', 'Unnamed')}\n"
        description += f"Type: {map_data.get('type', 'unknown')}\n"

        rooms = map_data.get('rooms', [])
        if rooms:
            description += "\nNotable locations:\n"
            for room in rooms:
                description += f"- {room.get('name', 'Room')} at ({room['x']}, {room['y']})\n"

        if entities:
            description += "\nCurrent entities:\n"
            for entity in entities:
                description += f"- {entity.get('name', 'Unknown')} ({entity.get('type', 'unknown')}) at ({entity['x']}, {entity['y']})\n"

        return description