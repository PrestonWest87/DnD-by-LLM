import random
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import CampaignMap, MapEntity, Campaign, CampaignMember, User, Character, get_db
from app.services.map_generator import MapGenerator

router = APIRouter()

map_generator = MapGenerator()


class MapGenerateRequest(BaseModel):
    campaign_id: int
    name: Optional[str] = "Main Map"
    map_type: str = "dungeon"
    theme: Optional[str] = "standard"
    algorithm: Optional[str] = "standard"
    width: int = 50
    height: int = 50
    difficulty: str = "medium"
    seed: Optional[str] = None


class EntityCreate(BaseModel):
    name: str
    entity_type: str
    x: int
    y: int
    character_id: Optional[int] = None


class EntityResponse(BaseModel):
    id: int
    name: str
    entity_type: str
    x: int
    y: int
    visible: bool

    class Config:
        from_attributes = True


class CellResponse(BaseModel):
    x: int
    y: int
    terrain: str
    explored: bool


@router.post("/generate")
async def generate_map(
    request: MapGenerateRequest,
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
    if campaign.owner_id != current_user.id and (not member or member.role != "dm"):
        raise HTTPException(status_code=403, detail="Not authorized. Only campaign owners or DMs can generate maps.")

    map_data = map_generator.generate(
        map_type=request.map_type,
        theme=request.theme,
        width=request.width,
        height=request.height,
        difficulty=request.difficulty,
        seed=request.seed,
        algorithm=request.algorithm
    )

    db_map = CampaignMap(
        campaign_id=request.campaign_id,
        name=request.name,
        seed=request.seed or str(random.randint(100000, 999999)),
        width=request.width,
        height=request.height,
        data=map_data
    )
    db.add(db_map)
    await db.commit()
    await db.refresh(db_map)

    return db_map


@router.get("/themes")
async def get_available_themes():
    """Get available dungeon themes"""
    return {
        "dungeon": list(MapGenerator.DUNGEON_THEMES.keys()),
        "wilderness": list(MapGenerator.WILDERNESS_BIOMES.keys()),
        "settlement": list(MapGenerator.SETTLEMENT_TYPES.keys()),
        "algorithms": {
            "standard": "Random room placement with corridors",
            "bsp": "Binary space partitioning - more evenly distributed rooms",
            "caverns": "Cellular automata - organic cave-like structures",
            "roguelike": "Dense room placement with minimum spacing"
        }
    }


@router.get("/campaign/{campaign_id}")
async def get_campaign_maps(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    member = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == current_user.id
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a campaign member")

    result = await db.execute(
        select(CampaignMap).where(CampaignMap.campaign_id == campaign_id)
    )
    return result.scalars().all()


@router.get("/{map_id}")
async def get_map(
    map_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CampaignMap).where(CampaignMap.id == map_id))
    map_data = result.scalar_one_or_none()
    if not map_data:
        raise HTTPException(status_code=404, detail="Map not found")

    member = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == map_data.campaign_id,
            CampaignMember.user_id == current_user.id
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a campaign member")

    entities = await db.execute(
        select(MapEntity).where(MapEntity.map_id == map_id)
    )

    return {
        "map": map_data,
        "entities": entities.scalars().all()
    }


@router.post("/{map_id}/explore")
async def explore_cell(
    map_id: int,
    x: int,
    y: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CampaignMap).where(CampaignMap.id == map_id))
    map_data = result.scalar_one_or_none()
    if not map_data:
        raise HTTPException(status_code=404, detail="Map not found")

    explored = map_data.explored_cells or {}
    explored[f"{x},{y}"] = True
    map_data.explored_cells = explored
    await db.commit()

    return {"explored": True}


@router.post("/{map_id}/entities")
async def add_entity(
    map_id: int,
    entity: EntityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CampaignMap).where(CampaignMap.id == map_id))
    map_data = result.scalar_one_or_none()
    if not map_data:
        raise HTTPException(status_code=404, detail="Map not found")

    member = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == map_data.campaign_id,
            CampaignMember.user_id == current_user.id
        )
    )
    if not member.scalar_one_or_none() or member.scalar_one().role != "dm":
        raise HTTPException(status_code=403, detail="Only DMs can add entities")

    db_entity = MapEntity(
        map_id=map_id,
        name=entity.name,
        entity_type=entity.entity_type,
        x=entity.x,
        y=entity.y
    )
    db.add(db_entity)
    await db.commit()
    await db.refresh(db_entity)

    return db_entity


@router.patch("/{map_id}/entities/{entity_id}")
async def update_entity(
    map_id: int,
    entity_id: int,
    x: Optional[int] = None,
    y: Optional[int] = None,
    visible: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MapEntity).where(
            MapEntity.id == entity_id,
            MapEntity.map_id == map_id
        )
    )
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    if x is not None:
        entity.x = x
    if y is not None:
        entity.y = y
    if visible is not None:
        entity.visible = visible

    await db.commit()
    await db.refresh(entity)
    return entity


@router.get("/{map_id}/describe")
async def describe_map_for_ai(
    map_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CampaignMap).where(CampaignMap.id == map_id))
    map_data = result.scalar_one_or_none()
    if not map_data:
        raise HTTPException(status_code=404, detail="Map not found")

    entities = await db.execute(
        select(MapEntity, Character)
        .join(Character, MapEntity.character_id == Character.id)
        .where(MapEntity.map_id == map_id)
    )

    description = map_generator.describe_for_ai(map_data.data, entities.all())

    return {"description": description}