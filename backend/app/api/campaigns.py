import secrets
import string
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user, generate_join_code
from app.db.database import Campaign, CampaignMember, User, CampaignDocument, Session, Room, ChatMessage, get_db

router = APIRouter()


def generate_campaign_code(length: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    dm_mode: Optional[str] = "ai"


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    story_outline: Optional[str] = None
    dm_mode: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    join_code: str
    owner_id: int
    story_outline: Optional[str]
    status: str
    dm_mode: str = "ai"

    class Config:
        from_attributes = True


class CampaignMemberResponse(BaseModel):
    id: int
    user_id: int
    campaign_id: int
    role: str
    username: str = ""

    class Config:
        from_attributes = True


class CampaignDocumentResponse(BaseModel):
    campaign_id: int
    content: str

    class Config:
        from_attributes = True


@router.post("/", response_model=CampaignResponse)
async def create_campaign(
    campaign: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    join_code = generate_campaign_code()
    db_campaign = Campaign(
        name=campaign.name,
        description=campaign.description,
        owner_id=current_user.id,
        join_code=join_code,
        dm_mode=campaign.dm_mode or "ai"
    )
    db.add(db_campaign)
    await db.commit()
    await db.refresh(db_campaign)

    member = CampaignMember(
        campaign_id=db_campaign.id,
        user_id=current_user.id,
        role="dm"
    )
    db.add(member)
    
    doc = CampaignDocument(
        campaign_id=db_campaign.id,
        content=f"# {campaign.name}\n\nThis is the campaign document for {campaign.name}. Key information about the campaign world, NPCs, and plot points will be recorded here."
    )
    db.add(doc)
    await db.commit()

    return db_campaign


@router.get("/", response_model=List[CampaignResponse])
async def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Campaign)
        .join(CampaignMember)
        .where(CampaignMember.user_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    member_result = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == current_user.id
        )
    )
    if not member_result.scalar_one_or_none() and campaign.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not a member of this campaign")
    
    return campaign


@router.post("/join/{join_code}")
async def join_campaign(
    join_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Campaign).where(Campaign.join_code == join_code))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    existing = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign.id,
            CampaignMember.user_id == current_user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already a member")

    member = CampaignMember(
        campaign_id=campaign.id,
        user_id=current_user.id,
        role="player"
    )
    db.add(member)
    await db.commit()
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    campaign_update: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if campaign_update.name:
        campaign.name = campaign_update.name
    if campaign_update.description:
        campaign.description = campaign_update.description
    if campaign_update.story_outline:
        campaign.story_outline = campaign_update.story_outline
    if campaign_update.dm_mode:
        campaign.dm_mode = campaign_update.dm_mode
    if campaign_update.llm_model is not None:
        campaign.llm_model = campaign_update.llm_model
    if campaign_update.llm_temperature is not None:
        campaign.llm_temperature = campaign_update.llm_temperature

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}/members", response_model=List[CampaignMemberResponse])
async def get_campaign_members(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(CampaignMember, User)
        .join(User, CampaignMember.user_id == User.id)
        .where(CampaignMember.campaign_id == campaign_id)
    )
    members = []
    for member, user in result.all():
        member.username = user.username
        members.append(member)
    return members


@router.get("/{campaign_id}/document")
async def get_campaign_document(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(CampaignDocument).where(CampaignDocument.campaign_id == campaign_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        campaign = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = campaign.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        doc = CampaignDocument(
            campaign_id=campaign_id,
            content=f"# {campaign.name}\n\nCampaign document initialized."
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
    
    return doc


@router.patch("/{campaign_id}/document")
async def update_campaign_document(
    campaign_id: int,
    content: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.db.database import Campaign
    campaign = await db.execute(select(Campaign).where(Campaign.id == campaign_id).limit(1))
    campaign = campaign.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await db.execute(
        select(CampaignDocument).where(CampaignDocument.campaign_id == campaign_id)
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        doc = CampaignDocument(campaign_id=campaign_id, content=content)
        db.add(doc)
    else:
        doc.content = content
    
    await db.commit()
    await db.refresh(doc)
    
    return doc


@router.post("/{campaign_id}/start-session")
async def start_session(
    campaign_id: int,
    room_id: int = None,
    title: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.db.database import Campaign
    try:
        campaign = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = campaign.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Check if user is a campaign member
        member = await db.execute(
            select(CampaignMember).where(
                CampaignMember.campaign_id == campaign_id,
                CampaignMember.user_id == current_user.id
            )
        )
        if not member.scalar_one_or_none() and campaign.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only campaign members can start sessions")
        
        # Get highest session number for this room
        query = select(Session).where(Session.room_id == room_id) if room_id else select(Session).where(Session.campaign_id == campaign_id)
        result = await db.execute(query.order_by(desc(Session.number)).limit(1))
        last_session = result.scalar_one_or_none()
        session_number = (last_session.number + 1) if last_session else 1
        
        session_title = title if title else f"Session {session_number}"
        
        new_session = Session(
            campaign_id=campaign_id,
            room_id=room_id,
            number=session_number,
            title=session_title
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        
        return new_session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.db.database import Room, Session as DBSession, ChatMessage, CampaignMap, MapEntity, CampaignEmbedding, CampaignDocument, CampaignMember
    
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the campaign owner can delete this campaign")
    
    rooms_result = await db.execute(select(Room).where(Room.campaign_id == campaign_id))
    rooms = rooms_result.scalars().all()
    
    for room in rooms:
        msgs_result = await db.execute(select(ChatMessage).where(ChatMessage.room_id == room.id))
        for msg in msgs_result.scalars().all():
            await db.delete(msg)
        
        sessions_result = await db.execute(select(DBSession).where(DBSession.room_id == room.id))
        for session in sessions_result.scalars().all():
            embeds_result = await db.execute(select(CampaignEmbedding).where(CampaignEmbedding.session_id == session.id))
            for emb in embeds_result.scalars().all():
                await db.delete(emb)
            await db.delete(session)
        
        await db.delete(room)
    
    maps_result = await db.execute(select(CampaignMap).where(CampaignMap.campaign_id == campaign_id))
    for campaign_map in maps_result.scalars().all():
        entities_result = await db.execute(select(MapEntity).where(MapEntity.map_id == campaign_map.id))
        for entity in entities_result.scalars().all():
            await db.delete(entity)
        await db.delete(campaign_map)
    
    members_result = await db.execute(select(CampaignMember).where(CampaignMember.campaign_id == campaign_id))
    for member in members_result.scalars().all():
        await db.delete(member)
    
    docs_result = await db.execute(select(CampaignDocument).where(CampaignDocument.campaign_id == campaign_id))
    for doc in docs_result.scalars().all():
        await db.delete(doc)
    
    await db.delete(campaign)
    await db.commit()
    
    return {"message": "Campaign deleted successfully"}