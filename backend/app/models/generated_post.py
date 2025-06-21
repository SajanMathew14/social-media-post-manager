"""
Database model for storing generated LinkedIn and X posts.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class PostType(enum.Enum):
    """Enumeration for post types"""
    LINKEDIN = "linkedin"
    X = "x"


class GeneratedPost(Base):
    """
    Model for storing generated social media posts.
    
    This model tracks both LinkedIn and X (Twitter) posts generated
    from news articles, including any user edits.
    """
    __tablename__ = "generated_posts"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True)
    
    # Post details
    post_type = Column(Enum(PostType), nullable=False)
    content = Column(Text, nullable=False)
    char_count = Column(Integer, nullable=False)
    edited = Column(Boolean, default=False, nullable=False)
    edited_content = Column(Text, nullable=True)
    edited_char_count = Column(Integer, nullable=True)
    
    # Generation metadata
    model_used = Column(String, nullable=False)
    news_workflow_id = Column(String, nullable=False, index=True)
    articles_count = Column(Integer, nullable=False)
    topic = Column(String, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    session = relationship("Session", back_populates="generated_posts")
    
    def __repr__(self):
        return f"<GeneratedPost(id={self.id}, type={self.post_type.value}, session={self.session_id})>"
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            "id": self.id,
            "session_id": str(self.session_id),
            "post_type": self.post_type.value,
            "content": self.edited_content if self.edited else self.content,
            "original_content": self.content if self.edited else None,
            "char_count": self.edited_char_count if self.edited else self.char_count,
            "edited": self.edited,
            "model_used": self.model_used,
            "news_workflow_id": self.news_workflow_id,
            "articles_count": self.articles_count,
            "topic": self.topic,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
