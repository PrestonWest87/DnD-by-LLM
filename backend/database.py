from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, JSON, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import datetime
import secrets

SQLALCHEMY_DATABASE_URL = "sqlite:///./data/vtt_master.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    invite_code = Column(String, unique=True, index=True, default=lambda: secrets.token_hex(4))
    dm_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    custom_setting = Column(Text, nullable=True)
    story_outline = Column(Text, nullable=True) 
    is_session_active = Column(Boolean, default=False)
    last_active_time = Column(DateTime, default=datetime.datetime.utcnow)

class Character(Base):
    __tablename__ = "characters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    stats = Column(JSON) 
    backstory = Column(Text)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    sender_type = Column(String) 
    sender_name = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
