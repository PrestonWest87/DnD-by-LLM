import os
import re
import json
import html
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.db.database import (
    CustomRule, Spell, Skill, Feat, ContentSource, Campaign,
    SRDRule, get_db, User, CampaignEmbedding
)
from app.api.auth import get_current_user
from app.services.ollama_client import OllamaClient

router = APIRouter()
ollama = OllamaClient()


class SourceToggle(BaseModel):
    campaign_id: int
    source_type: str
    source_id: int
    enabled: bool


async def get_current_user_dep(
    current_user: User = Depends(get_current_user)
) -> User:
    return current_user


@router.post("/upload")
async def upload_content(
    file: UploadFile = File(...),
    campaign_id: int = Form(...),
    content_type: str = Form("rule"),
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    campaign = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = campaign.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only campaign owner can upload content")
    
    content = await file.read()
    text = b""
    
    if file.filename:
        ext = file.filename.lower().split('.')[-1]
        
        if ext == 'pdf':
            text = content
        elif ext in ('md', 'txt'):
            text = content
        elif ext == 'json':
            text = content
        elif ext == 'html':
            text = content
        else:
            text = content
    
    text_str = content.decode('utf-8', errors='ignore') if content else ""
    
    chunks = chunk_text(text_str, 1000)
    
    saved_count = 0
    for chunk in chunks:
        embedding = await ollama.generate_embedding(chunk)
        
        rule = CustomRule(
            campaign_id=campaign_id,
            title=file.filename or "Untitled",
            content=chunk,
            source=file.filename or "upload",
            embedding=embedding
        )
        db.add(rule)
        saved_count += 1
    
    await db.commit()
    
    return {
        "message": f"Uploaded {saved_count} chunks from {file.filename}",
        "chunks": saved_count
    }


def chunk_text(text: str, chunk_size: int = 1000) -> List[str]:
    chunks = []
    paragraphs = re.split(r'\n\s*\n', text)
    
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current.strip())
            current = para
        else:
            current += "\n\n" + para if current else para
    
    if current.strip():
        chunks.append(current.strip())
    
    return [c for c in chunks if len(c) > 50]


@router.post("/spell")
async def add_spell(
    name: str = Form(...),
    level: int = Form(0),
    school: str = Form(""),
    casting_time: str = Form(""),
    range_val: str = Form(""),
    components: str = Form(""),
    duration: str = Form(""),
    description: str = Form(""),
    higher_level: str = Form(""),
    classes_json: str = Form("[]"),
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    import json
    classes = json.loads(classes_json)
    
    desc = f"{description}\n\n{higher_level}" if higher_level else description
    embedding = await ollama.generate_embedding(f"{name}: {desc}")
    
    spell = Spell(
        name=name,
        level=level,
        school=school,
        casting_time=casting_time,
        range_val=range_val,
        components=components,
        duration=duration,
        description=description,
        higher_level=higher_level,
        classes=classes,
        embedding=embedding
    )
    db.add(spell)
    await db.commit()
    
    return {"message": "Spell added", "id": spell.id}


@router.get("/spell/search")
async def search_spells(
    query: str,
    limit: int = 5,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    query_embedding = await ollama.generate_embedding(query)
    
    result = await db.execute(
        select(Spell)
        .order_by(Spell.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    
    return [
        {
            "id": s.id,
            "name": s.name,
            "level": s.level,
            "school": s.school,
            "description": s.description
        }
        for s in result.scalars().all()
    ]


@router.get("/rules/search")
async def search_rules(
    query: str,
    limit: int = 5,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    query_embedding = await ollama.generate_embedding(query)
    
    result = await db.execute(
        select(SRDRule)
        .order_by(SRDRule.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    
    return [
        {
            "id": r.id,
            "title": r.title,
            "category": r.category,
            "content": r.content[:200]
        }
        for r in result.scalars().all()
    ]


@router.get("/custom/search")
async def search_custom_rules(
    query: str,
    campaign_id: int,
    limit: int = 5,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    query_embedding = await ollama.generate_embedding(query)
    
    result = await db.execute(
        select(CustomRule)
        .where(CustomRule.campaign_id == campaign_id)
        .order_by(CustomRule.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    
    return [
        {
            "id": r.id,
            "title": r.title,
            "source": r.source,
            "content": r.content[:200]
        }
        for r in result.scalars().all()
    ]


@router.post("/source")
async def toggle_source(
    toggle: SourceToggle,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    campaign = await db.execute(
        select(Campaign).where(Campaign.id == toggle.campaign_id)
    )
    campaign = campaign.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only campaign owner can manage sources")
    
    existing = await db.execute(
        select(ContentSource).where(
            and_(
                ContentSource.campaign_id == toggle.campaign_id,
                ContentSource.source_type == toggle.source_type,
                ContentSource.source_id == toggle.source_id
            )
        )
    )
    existing = existing.scalar_one_or_none()
    
    if existing:
        existing.enabled = toggle.enabled
    else:
        source = ContentSource(
            campaign_id=toggle.campaign_id,
            source_type=toggle.source_type,
            source_id=toggle.source_id,
            enabled=toggle.enabled
        )
        db.add(source)
    
    await db.commit()
    
    return {"message": "Source toggled"}


@router.get("/sources/{campaign_id}")
async def get_sources(
    campaign_id: int,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ContentSource).where(ContentSource.campaign_id == campaign_id)
    )
    
    return [
        {
            "id": s.id,
            "source_type": s.source_type,
            "source_id": s.source_id,
            "enabled": s.enabled
        }
        for s in result.scalars().all()
    ]


@router.get("/search")
async def search_all(
    query: str,
    campaign_id: Optional[int] = None,
    sources: str = "rules,spells,custom",
    limit: int = 5,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    results = []
    source_list = sources.split(",")
    
    if "rules" in source_list:
        rules = await search_rules(query, limit, current_user, db)
        results.extend([{"type": "srd_rule", "data": r} for r in rules])
    
    if "spells" in source_list:
        spells = await search_spells(query, limit, current_user, db)
        results.extend([{"type": "spell", "data": s} for s in spells])
    
    if "custom" in source_list and campaign_id:
        custom = await search_custom_rules(query, campaign_id, limit, current_user, db)
        results.extend([{"type": "custom_rule", "data": c} for c in custom])
    
    return results[:limit * 3]