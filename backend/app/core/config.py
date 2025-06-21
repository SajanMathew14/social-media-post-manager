"""
Application configuration settings
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Social Media Post Manager"
    
    # CORS Origins (full URLs with protocols)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000", 
        "http://127.0.0.1:3000", 
        "https://*.onrender.com",
        "https://*.vercel.app",
        "https://*.vercel.sh"
    ]
    
    # Trusted Hosts (domain names only, no protocols)
    TRUSTED_HOSTS: List[str] = ["localhost", "127.0.0.1", "*.onrender.com", "*.vercel.app", "*.vercel.sh"]
    
    # Database
    # DATABASE_URL: str = "postgresql://user:password@localhost/social_media_manager"
    DATABASE_URL: str = "postgresql://social_media_post_manager_db_user:hdagqO9zoJBaHkKKdLZUhTjCybRIqXsc@dpg-d15uhtqdbo4c73c8cpkg-a/social_media_post_manager_db"

    # External APIs
    SERPER_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    TINYURL_API_KEY: str = ""
    
    # Langfuse Configuration (LLM Observability)
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    
    # Quota Limits
    DAILY_QUOTA_LIMIT: int = 10
    MONTHLY_QUOTA_LIMIT: int = 300
    
    # LLM Configuration
    DEFAULT_LLM_MODEL: str = "claude-3-5-sonnet"
    LLM_MAX_TOKENS: int = 4000
    LLM_TEMPERATURE: float = 0.7
    
    # News Configuration
    MAX_NEWS_ARTICLES: int = 12
    DEFAULT_NEWS_ARTICLES: int = 5
    NEWS_CACHE_TTL: int = 3600  # 1 hour
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator("TRUSTED_HOSTS", pre=True)
    def assemble_trusted_hosts(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
