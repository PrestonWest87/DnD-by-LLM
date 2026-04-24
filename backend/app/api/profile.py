from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import User, UserProfile, get_db
from app.api.auth import get_current_user

router = APIRouter()


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    theme: Optional[str] = None
    preferences: Optional[dict] = None


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    display_name: Optional[str]
    avatar_url: Optional[str]
    theme: str
    preferences: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        profile = UserProfile(
            user_id=current_user.id,
            display_name=current_user.username,
            theme="dark",
            preferences={}
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    
    return profile


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    profile_update: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        profile = UserProfile(
            user_id=current_user.id,
            display_name=current_user.username,
            theme="dark",
            preferences={}
        )
        db.add(profile)
    
    if profile_update.display_name is not None:
        profile.display_name = profile_update.display_name
    if profile_update.avatar_url is not None:
        profile.avatar_url = profile_update.avatar_url
    if profile_update.theme is not None:
        profile.theme = profile_update.theme
    if profile_update.preferences is not None:
        profile.preferences = profile_update.preferences
    
    await db.commit()
    await db.refresh(profile)
    
    return profile