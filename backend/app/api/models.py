import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_client import llm_client
from app.services.ollama_client import OllamaClient
from app.api.auth import get_current_user
from app.db.database import Campaign, CampaignMember, User, get_db

router = APIRouter()
ollama_client = OllamaClient()


class CampaignSettings(BaseModel):
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = None
    llm_top_p: Optional[float] = None
    dm_personality: Optional[str] = None


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str


class ModelsResponse(BaseModel):
    available: List[ModelInfo]
    current: Optional[str] = None
    provider: str


class LLMTestResponse(BaseModel):
    success: bool
    provider: str
    models: Optional[list] = None
    error: Optional[str] = None


@router.get("/available")
async def get_available_models(
    current_user: User = Depends(get_current_user)
):
    try:
        models = await ollama_client.list_models()
    except Exception:
        models = [{"name": "qwen2.5:7b"}]
    
    return {
        "models": [{"id": m.get("name", ""), "name": m.get("name", ""), "provider": "ollama"} for m in models],
        "default": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    }


@router.get("/test", response_model=LLMTestResponse)
async def test_llm_connection():
    result = llm_client.test_connection()
    return LLMTestResponse(**result)


@router.get("/campaign/{campaign_id}")
async def get_campaign_ai_settings(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    member_result = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == current_user.id
        )
    )
    member = member_result.scalar_one_or_none()
    
    if campaign.owner_id != current_user.id and (not member or member.role != "dm"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "llm_model": campaign.llm_model or llm_client.default_model,
        "llm_temperature": campaign.llm_temperature or llm_client.temperature,
        "llm_top_p": campaign.llm_top_p or llm_client.top_p,
        "dm_personality": campaign.dm_personality or ""
    }


@router.patch("/campaign/{campaign_id}")
async def update_campaign_ai_settings(
    campaign_id: int,
    settings: CampaignSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only campaign owner can update settings")
    
    if settings.llm_model is not None:
        campaign.llm_model = settings.llm_model
    if settings.llm_temperature is not None:
        campaign.llm_temperature = settings.llm_temperature
    if settings.llm_top_p is not None:
        campaign.llm_top_p = settings.llm_top_p
    if settings.dm_personality is not None:
        campaign.dm_personality = settings.dm_personality
    
    await db.commit()
    await db.refresh(campaign)
    
    return {
        "llm_model": campaign.llm_model,
        "llm_temperature": campaign.llm_temperature,
        "llm_top_p": campaign.llm_top_p,
        "dm_personality": campaign.dm_personality
    }


@router.post("/campaign/{campaign_id}/test")
async def test_campaign_model(
    campaign_id: int,
    model: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only campaign owner can test models")
    
    test_model = model or campaign.llm_model or llm_client.default_model
    
    test_messages = [
        {"role": "system", "content": "You are a helpful D&D assistant."},
        {"role": "user", "content": "Say 'OK' if you understand."}
    ]
    
    try:
        response = await llm_client.chat(test_messages, model=test_model)
        return {
            "success": True,
            "model": test_model,
            "response": response[:200]
        }
    except Exception as e:
        return {
            "success": False,
            "model": test_model,
            "error": str(e)
        }