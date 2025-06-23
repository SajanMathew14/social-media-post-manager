"""
User request model for quota tracking
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRequest(Base):
    """User request model for tracking API usage and quotas"""
    
    __tablename__ = "user_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    request_type = Column(String(50), nullable=False)  # 'news_fetch'
    topic = Column(String(100), nullable=False)
    date_requested = Column(String(10), nullable=False)  # YYYY-MM-DD format
    request_hash = Column(String(64), nullable=False)  # For duplicate detection
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    session = relationship("Session", backref="requests")
    
    def __repr__(self):
        return f"<UserRequest(id={self.id}, session_id={self.session_id}, topic={self.topic})>"
