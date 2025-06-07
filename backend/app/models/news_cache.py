"""
News cache model for storing fetched articles
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

from app.core.database import Base


class NewsCache(Base):
    """News cache model for storing fetched and processed articles"""
    
    __tablename__ = "news_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String(100), nullable=False)
    date_fetched = Column(String(10), nullable=False)  # YYYY-MM-DD format
    source = Column(String(100), nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)  # For deduplication
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<NewsCache(id={self.id}, topic={self.topic}, title={self.title[:50]}...)>"
