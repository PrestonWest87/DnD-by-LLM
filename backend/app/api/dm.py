import json
import os
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import (
    Campaign, CampaignMember, Room, Session, ChatMessage,
    Character, CampaignEmbedding, SRDRule, CampaignMap, MapEntity, User, get_db
)
from app.services.ollama_client import OllamaClient

router = APIRouter()


class StoryOutlineRequest(BaseModel):
    campaign_id: int
    theme: str
    tone: str
    players: List[str]


class DMContextRequest(BaseModel):
    room_id: int
    player_input: str
    character_id: Optional[int] = None


class SessionSummaryRequest(BaseModel):
    session_id: int
    summary: str


ollama_client = OllamaClient()


@router.post("/generate-story-outline")
async def generate_story_outline(
    request: StoryOutlineRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Campaign).where(Campaign.id == request.campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    member_result = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == request.campaign_id,
            CampaignMember.user_id == current_user.id
        )
    )
    member = member_result.scalar_one_or_none()
    if not member and campaign.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized. Only campaign members can generate story outlines.")

    system_prompt = f"""You are a creative D&D Dungeon Master. Generate a compelling story outline for a campaign.

Theme: {request.theme}
Tone: {request.tone}
Players: {', '.join(request.players)}

Create a story outline that includes:
1. An engaging opening situation
2. 3-5 major plot arcs
3. Key NPCs and factions
4. Potential locations
5. A satisfying conclusion

Write in a narrative style that can guide your campaign sessions."""
    
    outline = await ollama_client.chat(
        messages=[{"role": "user", "content": system_prompt}],
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    )

    campaign.story_outline = outline
    await db.commit()

    return {"outline": outline}


@router.post("/chat")
async def dm_chat(
    request: DMContextRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    room = await db.execute(select(Room).where(Room.id == request.room_id))
    room = room.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    campaign = await db.execute(select(Campaign).where(Campaign.id == room.campaign_id))
    campaign = campaign.scalar_one_or_none()

    if campaign.dm_mode == "human":
        raise HTTPException(status_code=403, detail="This campaign is in human DM mode. Wait for the human DM to respond.")

    character = None
    if request.character_id:
        result = await db.execute(select(Character).where(Character.id == request.character_id))
        character = result.scalar_one_or_none()
        
        if character and character.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You can only play as your own character.")

    context_messages = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.room_id == request.room_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(20)
    )
    recent_messages = list(reversed(context_messages.scalars().all()))

    session_result = await db.execute(
        select(Session)
        .where(Session.campaign_id == room.campaign_id)
        .order_by(desc(Session.number))
    )
    sessions = session_result.scalars().all()
    current_session = sessions[0] if sessions else None
    
    if not current_session and campaign.dm_mode == "ai":
        current_session = Session(campaign_id=room.campaign_id, number=1, title="Session 1")
        db.add(current_session)
        await db.commit()
        await db.refresh(current_session)

    story_context = f"Campaign: {campaign.name}\n"
    if campaign.story_outline:
        story_context += f"Story Outline: {campaign.story_outline}\n"

    if sessions and len(sessions) > 1:
        story_context += "\nPrevious Sessions:\n"
        for s in sessions[:-1]:
            if s.summary:
                story_context += f"- Session {s.number}: {s.summary}\n"

    character_context = ""
    if character:
        stats_str = json.dumps(character.stats) if isinstance(character.stats, dict) else str(character.stats)
        character_context = f"Playing as: {character.name} (Level {character.level} {character.race} {character.class_name})\nHP: {character.hp}/{character.max_hp} | AC: {character.ac}\nStats: {stats_str}\n"

    messages_history = "\n".join([
        f"{m.message_type}: {m.content}" for m in recent_messages[-8:]
    ])

    system_prompt = f"""You are a D&D Dungeon Master. Continue the story naturally, advance the plot.

STORY CONTEXT:
{story_context}

CHARACTER:
{character_context}

RECENT CONVERSATION:
{messages_history}

Continue the adventure. Describe what happens as a result of the player's action. Advance the story, introduce new challenges or developments."""

    response_chunks = await ollama_client.chat_stream(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.player_input}
        ],
        model=os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    )
    response = "".join(response_chunks)

    if current_session:
        recent_transcript = "\n".join([
            f"{m.message_type}: {m.content[:100]}" for m in recent_messages[-10:]
        ])
        recent_transcript += f"\nplayer: {request.player_input[:50]}\ndm: {response[:50]}"
        
        summary_prompt = f"Given this recent conversation, write a 1-sentence summary of the current story state:\n\n{recent_transcript}"
        summary_resp = await ollama_client.chat(
            messages=[{"role": "user", "content": summary_prompt}],
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        )
        current_session.summary = summary_resp
        await db.commit()

    return {"response": response}


@router.get("/session/{session_id}/context")
async def get_session_context(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    session = await db.execute(select(Session).where(Session.id == session_id))
    session = session.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    embeddings = await db.execute(
        select(CampaignEmbedding)
        .where(CampaignEmbedding.session_id == session_id)
    )

    return {
        "session": session,
        "context": [e.content for e in embeddings.scalars().all()]
    }


@router.post("/session/{session_id}/summarize")
async def summarize_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    session = await db.execute(select(Session).where(Session.id == session_id))
    session = session.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.room_id == session.campaign_id)
        .order_by(ChatMessage.timestamp)
    )
    all_messages = messages.scalars().all()

    transcript = "\n".join([
        f"{m.message_type}: {m.content}" for m in all_messages[-50:]
    ])

    system_prompt = f"""Summarize this D&D session into a concise paragraph (100-200 words) that captures:
- What happened
- Key decisions made
- Important NPCs encountered
- Quests or goals established

Session transcript:
{transcript}"""

    summary = await ollama_client.chat(
        messages=[{"role": "user", "content": system_prompt}],
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    )

    session.summary = summary
    await db.commit()

    return {"summary": summary}


@router.get("/rule-lookup")
async def rule_lookup(
    query: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    results = await ollama_client.search_rules(query, limit=3)
    return {"rules": results}