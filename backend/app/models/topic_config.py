"""
Topic configuration model for storing topic-to-source mappings
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, ARRAY, Float, DateTime

from app.core.database import Base


class TopicConfig(Base):
    """Topic configuration model for domain-aware news filtering"""
    
    __tablename__ = "topic_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_name = Column(String(100), unique=True, nullable=False)
    keywords = Column(ARRAY(String), nullable=False)
    trusted_sources = Column(ARRAY(String), nullable=False)
    priority_weight = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<TopicConfig(id={self.id}, topic_name={self.topic_name}, priority_weight={self.priority_weight})>"
