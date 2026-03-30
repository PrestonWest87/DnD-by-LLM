from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import secrets

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
    # A user can be a DM for multiple campaigns
    dm_campaigns = relationship("Campaign", back_populates="dm") 

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    invite_code = Column(String, unique=True, index=True, default=lambda: secrets.token_hex(4))
    dm_id = Column(Integer, ForeignKey("users.id"))
    
    dm = relationship("User", back_populates="dm_campaigns")
    characters = relationship("Character", back_populates="campaign")
    messages = relationship("ChatMessage", back_populates="campaign")

class Character(Base):
    __tablename__ = "characters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    
    # Storing stats as JSON allows flexibility for different TTRPG rule systems
    stats = Column(JSON) 
    backstory = Column(Text)
    
    owner = relationship("User", back_populates="characters")
    campaign = relationship("Campaign", back_populates="characters")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    sender_type = Column(String) # 'player', 'system', 'ai_dm'
    sender_name = Column(String)
    content = Column(Text)
    
    campaign = relationship("Campaign", back_populates="messages")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
