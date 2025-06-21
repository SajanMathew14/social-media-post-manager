"""
Core dependencies for the application
"""
from fastapi import HTTPException, status
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.db_status import get_database_status


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database dependency that handles connection errors gracefully
    """
    if not get_database_status():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Database connection unavailable",
                "message": "The service is currently running without database access. Please try again later.",
                "status": "degraded"
            }
        )
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Database operation failed",
                    "message": str(e)
                }
            )
        finally:
            await session.close()


def check_database_connection():
    """
    Dependency to check if database is connected
    """
    if not get_database_status():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Database connection unavailable",
                "message": "This endpoint requires database access which is currently unavailable.",
                "status": "degraded"
            }
        )
    return True
