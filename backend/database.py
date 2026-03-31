from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, JSON, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import secrets
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./vtt_master.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    characters = relationship("Character", back_populates="owner")
    dm_campaigns = relationship("Campaign", back_populates="dm") 

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    invite_code = Column(String, unique=True, index=True, default=lambda: secrets.token_hex(4))
    dm_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # New Campaign Data
    custom_setting = Column(Text, nullable=True)
    story_outline = Column(Text, nullable=True) 
    
    # Session Management
    is_session_active = Column(Boolean, default=False)
    last_active_time = Column(DateTime, default=datetime.datetime.utcnow)
    
    dm = relationship("User", back_populates="dm_campaigns")
    characters = relationship("Character", back_populates="campaign")
    messages = relationship("ChatMessage", back_populates="campaign")

class Character(Base):
    __tablename__ = "characters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    
    stats = Column(JSON) 
    backstory = Column(Text)
    
    owner = relationship("User", back_populates="characters")
    campaign = relationship("Campaign", back_populates="characters")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    sender_type = Column(String) 
    sender_name = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    campaign = relationship("Campaign", back_populates="messages")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
