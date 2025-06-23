"""
Session model for user session management
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Session(Base):
    """Session model for tracking user sessions"""
    
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active = Column(DateTime, default=datetime.utcnow, nullable=False)
    preferences = Column(JSON, default=dict)
    
    # Relationships
    generated_posts = relationship("GeneratedPost", back_populates="session")
    
    def __repr__(self):
        return f"<Session(id={self.id}, created_at={self.created_at})>"
