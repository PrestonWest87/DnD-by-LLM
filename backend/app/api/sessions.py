from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import (
    Room, Session as DBSession, Campaign, CampaignMap, MapEntity, Character, PlayerReady, User, get_db
)
from app.services.map_generator import MapGenerator

router = APIRouter()
map_generator = MapGenerator()


class SessionCreate(BaseModel):
    room_id: int
    title: Optional[str] = None


class SessionSummaryUpdate(BaseModel):
    summary: str


class SessionEnd(BaseModel):
    summary: str


class SessionResponse(BaseModel):
    id: int
    room_id: int
    title: str
    status: str
    running_summary: Optional[str]
    summary: Optional[str]

    class Config:
        from_attributes = True


class ReadyToggle(BaseModel):
    character_id: int


class ReadyResponse(BaseModel):
    character_id: int
    is_ready: bool
    updated_at: str

    class Config:
        from_attributes = True


@router.post("/create", response_model=SessionResponse)
async def create_session(
    request: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    room = await db.execute(select(Room).where(Room.id == request.room_id))
    room = room.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    result = await db.execute(
        select(DBSession)
        .where(DBSession.room_id == request.room_id)
        .order_by(desc(DBSession.number))
    )
    last_session = result.scalar_one_or_none()
    
    new_number = (last_session.number + 1) if last_session else 1
    
    db_session = DBSession(
        campaign_id=room.campaign_id,
        room_id=request.room_id,
        number=new_number,
        title=request.title or f"Session {new_number}",
        status="active",
        running_summary=""
    )
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)
    
    room.is_active_session = True
    await db.commit()
    
    return db_session


@router.get("/room/{room_id}")
async def get_active_session(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DBSession)
        .where(DBSession.room_id == room_id, DBSession.status == "active")
        .order_by(desc(DBSession.number))
    )
    session = result.scalar_one_or_none()
    
    if not session:
        return {"session": None, "summary": None}
    
    return {
        "session": session,
        "summary": session.running_summary
    }


@router.get("/{session_id}/summary")
async def get_session_summary(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"running_summary": session.running_summary, "summary": session.summary}


@router.post("/{session_id}/summary")
async def update_session_summary(
    session_id: int,
    request: SessionSummaryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.running_summary = request.summary
    await db.commit()
    await db.refresh(session)
    
    return {"status": "updated", "running_summary": session.running_summary}


@router.post("/{session_id}/end")
async def end_session(
    session_id: int,
    request: SessionEnd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.status = "completed"
    session.summary = request.summary
    session.running_summary = None
    await db.commit()
    
    if session.room_id:
        room_result = await db.execute(select(Room).where(Room.id == session.room_id))
        room = room_result.scalar_one_or_none()
        if room:
            room.is_active_session = False
            await db.commit()
    
    return {"status": "completed", "summary": session.summary}


@router.post("/{session_id}/generate-map")
async def generate_session_map(
    session_id: int,
    map_type: str = "dungeon",
    theme: str = "standard",
    difficulty: str = "medium",
    width: int = 50,
    height: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    session_result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    map_data = map_generator.generate(
        map_type=map_type,
        theme=theme,
        width=width,
        height=height,
        difficulty=difficulty
    )
    
    db_map = CampaignMap(
        campaign_id=session.campaign_id,
        name=f"Session {session.number} Map",
        seed=str(session.id),
        width=width,
        height=height,
        data=map_data
    )
    db.add(db_map)
    await db.commit()
    await db.refresh(db_map)
    
    if session.room_id:
        room_result = await db.execute(select(Room).where(Room.id == session.room_id))
        room = room_result.scalar_one_or_none()
        if room:
            room.map_id = db_map.id
            await db.commit()
    
    return {"map": db_map, "map_data": map_data}


@router.get("/room/{room_id}/ready")
async def get_ready_states(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(PlayerReady).where(PlayerReady.room_id == room_id)
    )
    ready_states = result.scalars().all()
    
    characters_result = await db.execute(
        select(Character).where(Character.campaign_id == (
            select(Room.campaign_id).where(Room.id == room_id)
        ))
    )
    characters = characters_result.scalars().all()
    
    return {
        "ready_states": [
            {
                "character_id": r.character_id,
                "is_ready": r.is_ready,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None
            }
            for r in ready_states
        ],
        "total_players": len(characters),
        "ready_count": sum(1 for r in ready_states if r.is_ready)
    }


@router.post("/room/{room_id}/ready")
async def toggle_ready(
    room_id: int,
    request: ReadyToggle,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(PlayerReady).where(
            PlayerReady.room_id == room_id,
            PlayerReady.character_id == request.character_id
        )
    )
    ready_record = result.scalar_one_or_none()
    
    if ready_record:
        from sqlalchemy.sql import func as sql_func
        ready_record.is_ready = not ready_record.is_ready
        ready_record.updated_at = sql_func.now()
    else:
        ready_record = PlayerReady(
            room_id=room_id,
            character_id=request.character_id,
            is_ready=True
        )
        db.add(ready_record)
    
    await db.commit()
    await db.refresh(ready_record)
    
    return {
        "character_id": request.character_id,
        "is_ready": ready_record.is_ready
    }


@router.get("/room/{room_id}/all-ready")
async def check_all_ready(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    room_result = await db.execute(select(Room).where(Room.id == room_id))
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    chars_result = await db.execute(
        select(Character).where(Character.campaign_id == room.campaign_id)
    )
    characters = list(chars_result.scalars().all())
    
    ready_result = await db.execute(
        select(PlayerReady).where(
            PlayerReady.room_id == room_id,
            PlayerReady.is_ready == True
        )
    )
    ready_states = list(ready_result.scalars().all())
    
    all_ready = len(characters) > 0 and len(ready_states) >= len(characters)
    
    return {
        "all_ready": all_ready,
        "total_players": len(characters),
        "ready_count": len(ready_states)
    }