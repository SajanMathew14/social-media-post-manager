"""
FastAPI main application for Social Media Post Manager
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.database import engine
from app.core.db_status import set_database_status, get_database_status
from app.models import Base
from app.api.routes import news, sessions
from app.langgraph.utils.logging_config import setup_logging

# Setup structured logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    
    # Startup
    logger.info("Starting Social Media Post Manager API")
    
    # Try to create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        set_database_status(True)
        logger.info("Database tables created successfully")
    except Exception as e:
        set_database_status(False)
        logger.error(f"Failed to connect to database: {str(e)}")
        logger.warning("Application starting without database connection")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Social Media Post Manager API")


# Create FastAPI application
app = FastAPI(
    title="Social Media Post Manager API",
    description="AI-powered LinkedIn content manager with news aggregation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Include routers
app.include_router(
    news.router,
    prefix="/api/news",
    tags=["news"]
)

app.include_router(
    sessions.router,
    prefix="/api/sessions",
    tags=["sessions"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Social Media Post Manager API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Try to check database connection
    db_status = "disconnected"
    db_error = None
    
    if get_database_status():
        try:
            # Attempt a simple query to verify connection
            from sqlalchemy import text
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            db_status = "error"
            db_error = str(e)
    
    response = {
        "status": "healthy" if get_database_status() else "degraded",
        "database": db_status,
        "services": {
            "api": "running",
            "database": get_database_status()
        }
    }
    
    if db_error:
        response["database_error"] = db_error
    
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
