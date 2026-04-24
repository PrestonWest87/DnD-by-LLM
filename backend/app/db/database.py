import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, JSON, Float, text
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from contextlib import asynccontextmanager

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://dragonforge:changeme123@db:5432/dragonforge"
)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    async with async_session_maker() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        
        try:
            async with conn.transaction():
                await conn.execute(text("""
                    ALTER TABLE characters ADD COLUMN IF NOT EXISTS inventory JSON DEFAULT '[]';
                    ALTER TABLE characters ADD COLUMN IF NOT EXISTS stat_rolls JSON DEFAULT '[]';
                    ALTER TABLE characters ADD COLUMN IF NOT EXISTS stat_roll_count INTEGER DEFAULT 0;
                """))
        except Exception:
            pass

from sqlalchemy import text


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    profile = relationship("UserProfile", back_populates="user", uselist=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    display_name = Column(String(100))
    avatar_url = Column(String(500))
    theme = Column(String(20), default="dark")
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    join_code = Column(String(10), unique=True, nullable=False)
    story_outline = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), default="active")
    
    llm_model = Column(String(100))
    llm_temperature = Column(Float, default=0.7)
    llm_top_p = Column(Float, default=0.9)
    dm_personality = Column(Text)
    dm_mode = Column(String(20), default="ai")


class CampaignMember(Base):
    __tablename__ = "campaign_members"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="player")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())


class Character(Base):
    __tablename__ = "characters"
    # ... (fields from before)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    name = Column(String(100), nullable=False)
    race = Column(String(50), nullable=False)
    class_name = Column(String(50), nullable=False)
    subclass = Column(String(50))
    background = Column(String(50))
    level = Column(Integer, default=1)
    stats = Column(JSON)
    hp = Column(Integer)
    max_hp = Column(Integer)
    ac = Column(Integer)
    speed = Column(Integer)
    proficiency_bonus = Column(Integer, default=2)
    saving_throws = Column(JSON)
    skills = Column(JSON)
    features = Column(JSON)
    spells = Column(JSON)
    equipment = Column(JSON)
    inventory = Column(JSON)
    personality = Column(Text)
    backstory = Column(Text)
    portrait_url = Column(String(500))
    stat_rolls = Column(JSON)
    stat_roll_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CharacterItem(Base):
    __tablename__ = "character_items"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    quantity = Column(Integer, default=1)
    weight = Column(Float, default=0.0)
    item_type = Column(String(50))
    rarity = Column(String(20))
    equipped = Column(Boolean, default=False)
    damage = Column(String(20))
    armor_class = Column(Integer)
    damage_type = Column(String(20))
    range_value = Column(String(20))
    magical = Column(Boolean, default=False)
    cost = Column(Integer, default=0)


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    name = Column(String(100), nullable=False)
    join_code = Column(String(10), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    dm_mode = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    number = Column(Integer, nullable=False)
    title = Column(String(200))
    summary = Column(Text)
    full_transcript = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    character_id = Column(Integer, ForeignKey("characters.id"))
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="player")
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class CampaignMap(Base):
    __tablename__ = "campaign_maps"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    name = Column(String(100))
    seed = Column(String(50))
    width = Column(Integer, default=50)
    height = Column(Integer, default=50)
    data = Column(JSON)
    explored_cells = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MapEntity(Base):
    __tablename__ = "map_entities"

    id = Column(Integer, primary_key=True, index=True)
    map_id = Column(Integer, ForeignKey("campaign_maps.id"), nullable=False)
    character_id = Column(Integer, ForeignKey("characters.id"))
    name = Column(String(100))
    entity_type = Column(String(50))
    x = Column(Integer)
    y = Column(Integer)
    visible = Column(Boolean, default=True)


class SRDRule(Base):
    __tablename__ = "srd_rules"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50))
    title = Column(String(200))
    content = Column(Text)
    embedding = Column(Vector(768))


class CampaignEmbedding(Base):
    __tablename__ = "campaign_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    content = Column(Text)
    content_type = Column(String(50))
    embedding = Column(Vector(768))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CustomRule(Base):
    __tablename__ = "custom_rules"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    title = Column(String(200))
    content = Column(Text)
    source = Column(String(100))
    embedding = Column(Vector(768))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Spell(Base):
    __tablename__ = "spells"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    level = Column(Integer, default=0)
    school = Column(String(50))
    casting_time = Column(String(100))
    range_val = Column(String(100))
    components = Column(String(100))
    duration = Column(String(100))
    description = Column(Text)
    higher_level = Column(Text)
    classes = Column(JSON)
    embedding = Column(Vector(768))


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    ability = Column(String(3))
    description = Column(Text)
    armor_check = Column(Boolean, default=False)


class Feat(Base):
    __tablename__ = "feats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    prerequisites = Column(String(200))
    description = Column(Text)
    benefits = Column(Text)
    embedding = Column(Vector(768))


class ContentSource(Base):
    __tablename__ = "content_sources"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    source_type = Column(String(50))
    source_id = Column(Integer)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CampaignDocument(Base):
    __tablename__ = "campaign_documents"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), unique=True, nullable=False)
    content = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())