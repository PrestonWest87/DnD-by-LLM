import secrets
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import (
    Room, Encounter, InitiativeEntry, Character, PlayerResponse, User, get_db
)

router = APIRouter()


class EncounterCreate(BaseModel):
    room_id: int
    name: Optional[str] = None
    map_id: Optional[int] = None


class EncounterResponse(BaseModel):
    id: int
    room_id: int
    map_id: Optional[int]
    name: Optional[str]
    status: str
    current_turn: int
    round: int

    class Config:
        from_attributes = True


class InitiativeJoin(BaseModel):
    character_id: int
    initiative_modifier: int = 0


class InitiativeRoll(BaseModel):
    character_id: int
    roll: int


class InitiativeAdvance(BaseModel):
    character_id: Optional[int] = None


@router.post("/", response_model=EncounterResponse)
async def create_encounter(
    encounter: EncounterCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Room).where(Room.id == encounter.room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    db_encounter = Encounter(
        room_id=encounter.room_id,
        map_id=encounter.map_id,
        name=encounter.name or f"Encounter {secrets.token_hex(2)}",
        status="pending"
    )
    db.add(db_encounter)
    await db.commit()
    await db.refresh(db_encounter)
    return db_encounter


@router.get("/room/{room_id}")
async def get_active_encounter(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Encounter)
        .where(Encounter.room_id == room_id)
        .order_by(desc(Encounter.created_at))
    )
    encounter = result.scalar_one_or_none()
    
    if not encounter:
        return {"encounter": None, "participants": []}
    
    participants_result = await db.execute(
        select(InitiativeEntry)
        .where(InitiativeEntry.encounter_id == encounter.id)
        .order_by(InitiativeEntry.turn_order)
    )
    participants = participants_result.scalars().all()
    
    return {
        "encounter": encounter,
        "participants": [
            {
                "id": p.id,
                "character_id": p.character_id,
                "initiative_roll": p.initiative_roll,
                "initiative_modifier": p.initiative_modifier,
                "turn_order": p.turn_order,
                "is_active": p.is_active,
                "hp_remaining": p.hp_remaining,
                "conditions": p.conditions
            }
            for p in participants
        ]
    }


@router.post("/{encounter_id}/join")
async def join_encounter(
    encounter_id: int,
    data: InitiativeJoin,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(InitiativeEntry).where(
            InitiativeEntry.encounter_id == encounter_id,
            InitiativeEntry.character_id == data.character_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Character already in encounter")
    
    count_result = await db.execute(
        select(InitiativeEntry).where(InitiativeEntry.encounter_id == encounter_id)
    )
    count = len(list(count_result.scalars().all()))
    
    db_entry = InitiativeEntry(
        encounter_id=encounter_id,
        character_id=data.character_id,
        initiative_modifier=data.initiative_modifier,
        turn_order=count + 1,
        hp_remaining=0
    )
    db.add(db_entry)
    await db.commit()
    
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if encounter:
        encounter.status = "active"
        await db.commit()
    
    return {"status": "joined", "turn_order": count + 1}


@router.post("/{encounter_id}/roll")
async def roll_initiative(
    encounter_id: int,
    data: InitiativeRoll,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(InitiativeEntry).where(
            InitiativeEntry.encounter_id == encounter_id,
            InitiativeEntry.character_id == data.character_id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Character not in encounter")
    
    entry.initiative_roll = data.roll
    await db.commit()
    
    entries_result = await db.execute(
        select(InitiativeEntry)
        .where(InitiativeEntry.encounter_id == encounter_id)
        .order_by(desc(InitiativeEntry.initiative_roll))
    )
    entries = list(entries_result.scalars().all())
    
    for i, entry in enumerate(entries):
        entry.turn_order = i + 1
    
    await db.commit()
    
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if encounter and encounter.current_turn == 0 and any(e.initiative_roll for e in entries):
        encounter.current_turn = 1
        await db.commit()
    
    return {"entries": [{"character_id": e.character_id, "turn_order": e.turn_order} for e in entries]}


@router.post("/{encounter_id}/next-turn")
async def next_turn(
    encounter_id: int,
    data: InitiativeAdvance,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    entries_result = await db.execute(
        select(InitiativeEntry)
        .where(InitiativeEntry.encounter_id == encounter_id)
        .order_by(InitiativeEntry.turn_order)
    )
    entries = list(entries_result.scalars().all())
    
    if not entries:
        raise HTTPException(status_code=400, detail="No participants")
    
    next_turn = encounter.current_turn + 1
    if next_turn > len(entries):
        next_turn = 1
        encounter.round += 1
    
    encounter.current_turn = next_turn
    await db.commit()
    
    current_entry = entries[next_turn - 1]
    return {
        "current_turn": next_turn,
        "round": encounter.round,
        "active_character_id": current_entry.character_id
    }


@router.post("/{encounter_id}/damage")
async def apply_damage(
    encounter_id: int,
    character_id: int,
    damage: int,
    heal: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(InitiativeEntry).where(
            InitiativeEntry.encounter_id == encounter_id,
            InitiativeEntry.character_id == character_id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Character not in encounter")
    
    char_result = await db.execute(select(Character).where(Character.id == character_id))
    char = char_result.scalar_one_or_none()
    
    if heal:
        entry.hp_remaining = min(char.max_hp if char else entry.hp_remaining + damage, entry.hp_remaining + damage)
    else:
        entry.hp_remaining -= damage
    
    if entry.hp_remaining <= 0:
        entry.is_active = False
    
    await db.commit()
    return {"hp_remaining": entry.hp_remaining, "is_active": entry.is_active}


@router.post("/{encounter_id}/condition")
async def add_condition(
    encounter_id: int,
    character_id: int,
    condition: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(InitiativeEntry).where(
            InitiativeEntry.encounter_id == encounter_id,
            InitiativeEntry.character_id == character_id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Character not in encounter")
    
    conditions = entry.conditions or []
    if condition not in conditions:
        conditions.append(condition)
        entry.conditions = conditions
        await db.commit()
    
    return {"conditions": entry.conditions}


@router.delete("/{encounter_id}")
async def end_encounter(
    encounter_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    encounter.status = "completed"
    await db.commit()
    return {"status": "completed"}


class PlayerPromptRequest(BaseModel):
    character_ids: List[int]
    prompt: str
    wait_for_all: bool = False


class PlayerResponseRequest(BaseModel):
    response: str


@router.post("/{encounter_id}/prompt")
async def create_player_prompt(
    encounter_id: int,
    request: PlayerPromptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    room_result = await db.execute(select(Room).where(Room.id == encounter.room_id))
    room = room_result.scalar_one_or_none()
    
    prompts = []
    for char_id in request.character_ids:
        db_response = PlayerResponse(
            encounter_id=encounter_id,
            room_id=room.id if room else None,
            character_id=char_id,
            prompt=request.prompt,
            responded=False
        )
        db.add(db_response)
        prompts.append({
            "character_id": char_id,
            "prompt": request.prompt,
            "wait_for_all": request.wait_for_all
        })
    
    await db.commit()
    return {"prompts": prompts, "wait_for_all": request.wait_for_all}


@router.get("/{encounter_id}/prompts")
async def get_player_prompts(
    encounter_id: int,
    character_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(PlayerResponse).where(PlayerResponse.encounter_id == encounter_id)
    
    if character_id:
        query = query.where(PlayerResponse.character_id == character_id)
    
    result = await db.execute(query.order_by(PlayerResponse.created_at.desc()))
    responses = result.scalars().all()
    
    pending = [r for r in responses if not r.responded]
    completed = [r for r in responses if r.responded]
    
    return {
        "pending": [{"id": r.id, "character_id": r.character_id, "prompt": r.prompt} for r in pending],
        "completed": [{"id": r.id, "character_id": r.character_id, "prompt": r.prompt, "response": r.response} for r in completed],
        "all_responded": len(pending) == 0 and len(responses) > 0
    }


@router.post("/{encounter_id}/respond")
async def respond_to_prompt(
    encounter_id: int,
    character_id: int,
    request: PlayerResponseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(PlayerResponse).where(
            PlayerResponse.encounter_id == encounter_id,
            PlayerResponse.character_id == character_id,
            PlayerResponse.responded == False
        )
    )
    pending = result.scalars().all()
    
    if not pending:
        return {"message": "No pending prompts"}
    
    prompt = pending[0]
    prompt.response = request.response
    prompt.responded = True
    await db.commit()
    
    return {"responded": True, "prompt": prompt.prompt}