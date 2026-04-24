import os
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import httpx

from app.api.auth import get_current_user
from app.db.database import User, Campaign, get_db
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.admin import require_admin

router = APIRouter()


class SystemSettings(BaseModel):
    ollama_url: Optional[str] = None
    ollama_embed_model: Optional[str] = None
    ollama_chat_model: Optional[str] = None
    jwt_secret: Optional[str] = None


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    models: Optional[List[dict]] = None


class StatsResponse(BaseModel):
    total_users: int
    total_campaigns: int
    active_sessions: int


async def get_current_ollama_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")


@router.get("/settings", response_model=SystemSettings)
async def get_system_settings(
    current_user: User = Depends(require_admin)
):
    return SystemSettings(
        ollama_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
        ollama_embed_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        ollama_chat_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        jwt_secret=os.getenv("JWT_SECRET", "")[:8] + "..." if os.getenv("JWT_SECRET") else None
    )


@router.post("/settings")
async def update_system_settings(
    settings: SystemSettings,
    current_user: User = Depends(require_admin)
):
    if settings.ollama_url:
        os.environ["OLLAMA_BASE_URL"] = settings.ollama_url
    if settings.ollama_embed_model:
        os.environ["OLLAMA_EMBED_MODEL"] = settings.ollama_embed_model
    if settings.ollama_chat_model:
        os.environ["OLLAMA_MODEL"] = settings.ollama_chat_model
    
    return {"message": "Settings updated (note: env vars reset on restart)"}


@router.get("/ollama/test", response_model=TestConnectionResponse)
async def test_ollama_connection(
    url: Optional[str] = None,
    current_user: User = Depends(require_admin)
):
    test_url = url or await get_current_ollama_url()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{test_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [{"name": m.get("name"), "size": m.get("size")} for m in data.get("models", [])]
                return TestConnectionResponse(
                    success=True,
                    message=f"Connected to Ollama at {test_url}",
                    models=models
                )
            else:
                return TestConnectionResponse(
                    success=False,
                    message=f"HTTP {response.status_code}"
                )
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=str(e)
        )


@router.get("/ollama/models")
async def get_ollama_models(
    current_user: User = Depends(require_admin)
):
    url = await get_current_ollama_url()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return {"models": data.get("models", [])}
            return {"models": []}
    except Exception as e:
        return {"models": [], "error": str(e)}


@router.get("/stats", response_model=StatsResponse)
async def get_system_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    user_count = await db.execute(select(func.count(User.id)))
    total_users = user_count.scalar() or 0
    
    campaign_count = await db.execute(select(func.count(Campaign.id)))
    total_campaigns = campaign_count.scalar() or 0
    
    return StatsResponse(
        total_users=total_users,
        total_campaigns=total_campaigns,
        active_sessions=total_campaigns
    )