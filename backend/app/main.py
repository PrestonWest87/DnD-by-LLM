import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth, campaigns, rooms, characters, dice, dm, map_routes, admin, models, profile, settings, rag
from app.db.database import init_db, async_session_maker, User


async def create_default_admin():
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@dragonforge.local")

    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.username == ADMIN_USERNAME)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            password_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            admin = User(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                password_hash=password_hash,
                is_admin=True
            )
            session.add(admin)
            await session.commit()
            print(f"Created default admin user: {ADMIN_USERNAME}")
        else:
            if not admin.is_admin:
                admin.is_admin = True
                await session.commit()
                print(f"Updated user {ADMIN_USERNAME} to admin")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await create_default_admin()
    yield


app = FastAPI(
    title="DragonForge API",
    description="LLM-powered D&D tabletop system",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
app.include_router(characters.router, prefix="/api/characters", tags=["characters"])
app.include_router(dice.router, prefix="/api/dice", tags=["dice"])
app.include_router(dm.router, prefix="/api/dm", tags=["dm"])
app.include_router(map_routes.router, prefix="/api/maps", tags=["maps"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}