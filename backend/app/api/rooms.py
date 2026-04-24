import secrets
import string
from typing import List, Optional, Union
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_serializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import Room, Campaign, CampaignMember, User, ChatMessage, get_db

router = APIRouter()


def generate_room_code(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


class RoomCreate(BaseModel):
    campaign_id: int
    name: str


class RoomResponse(BaseModel):
    id: int
    campaign_id: int
    name: str
    join_code: str
    is_active: bool

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str
    message_type: str = "player"


class MessageResponse(BaseModel):
    id: int
    room_id: int
    user_id: Optional[int]
    character_id: Optional[int]
    content: str
    message_type: str
    timestamp: Union[str, datetime]

    @field_serializer('timestamp')
    def serialize_timestamp(self, value: datetime) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    class Config:
        from_attributes = True


@router.post("/", response_model=RoomResponse)
async def create_room(
    room: RoomCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Campaign).where(Campaign.id == room.campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    member = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == room.campaign_id,
            CampaignMember.user_id == current_user.id
        )
    )
    member_data = member.scalar_one_or_none()
    if not member_data:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    if campaign.owner_id != current_user.id and member_data.role != "dm":
        raise HTTPException(status_code=403, detail="Not authorized. Only campaign owners or DMs can create rooms.")

    join_code = generate_room_code()
    db_room = Room(
        campaign_id=room.campaign_id,
        name=room.name,
        join_code=join_code
    )
    db.add(db_room)
    await db.commit()
    await db.refresh(db_room)
    return db_room


@router.post("/join/{join_code}")
async def join_room(
    join_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Room).where(Room.join_code == join_code))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not room.is_active:
        raise HTTPException(status_code=400, detail="Room is not active")
    return room


@router.get("/campaign/{campaign_id}", response_model=List[RoomResponse])
async def list_rooms(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Room).where(Room.campaign_id == campaign_id)
    )
    return result.scalars().all()


@router.get("/{room_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    room_id: int,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.room_id == room_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/{room_id}/messages", response_model=MessageResponse)
async def send_message(
    room_id: int,
    message: MessageCreate,
    character_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    db_message = ChatMessage(
        room_id=room_id,
        user_id=current_user.id,
        character_id=character_id,
        content=message.content,
        message_type=message.message_type
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    return db_message