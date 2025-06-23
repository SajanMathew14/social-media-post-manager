"""
Session management API routes for the Social Media Post Manager.

This module provides REST endpoints for session management
and quota tracking.
"""
import uuid
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models.session import Session
from app.models.user_request import UserRequest
from app.core.config import settings

router = APIRouter()


class CreateSessionRequest(BaseModel):
    """Request model for creating a new session."""
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")


class SessionResponse(BaseModel):
    """Response model for session operations."""
    sessionId: str = Field(..., description="Session identifier")
    createdAt: str = Field(..., description="Session creation timestamp")
    preferences: Dict[str, Any] = Field(..., description="User preferences")


class QuotaResponse(BaseModel):
    """Response model for quota information."""
    dailyUsed: int = Field(..., description="Daily requests used")
    dailyLimit: int = Field(..., description="Daily request limit")
    monthlyUsed: int = Field(..., description="Monthly requests used")
    monthlyLimit: int = Field(..., description="Monthly request limit")
    remaining: int = Field(..., description="Remaining requests today")
    quotaAvailable: bool = Field(..., description="Whether quota is available")


@router.post("/create", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """
    Create a new user session.
    
    Args:
        request: Session creation request
        db: Database session dependency
        
    Returns:
        Created session information
        
    Raises:
        HTTPException: When session creation fails
    """
    try:
        # Generate new session ID
        session_id = str(uuid.uuid4())
        
        # Create new session
        new_session = Session(
            id=session_id,
            preferences=request.preferences
        )
        
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        
        return SessionResponse(
            sessionId=str(new_session.id),
            createdAt=new_session.created_at.isoformat(),
            preferences=new_session.preferences
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "SessionCreationError",
                "message": "Failed to create session",
                "details": {"error_type": type(e).__name__}
            }
        )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """
    Get session information.
    
    Args:
        session_id: Session identifier
        db: Database session dependency
        
    Returns:
        Session information
        
    Raises:
        HTTPException: When session is not found
    """
    try:
        # Find session
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "SessionNotFound",
                    "message": f"Session {session_id} not found"
                }
            )
        
        # Update last active timestamp
        session.last_active = datetime.utcnow()
        await db.commit()
        
        return SessionResponse(
            sessionId=str(session.id),
            createdAt=session.created_at.isoformat(),
            preferences=session.preferences
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "SessionRetrievalError",
                "message": "Failed to retrieve session",
                "details": {"error_type": type(e).__name__}
            }
        )


@router.get("/{session_id}/quota", response_model=QuotaResponse)
async def get_session_quota(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> QuotaResponse:
    """
    Get quota information for a session.
    
    Args:
        session_id: Session identifier
        db: Database session dependency
        
    Returns:
        Quota information
        
    Raises:
        HTTPException: When session is not found or quota query fails
    """
    try:
        # Verify session exists
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "SessionNotFound",
                    "message": f"Session {session_id} not found"
                }
            )
        
        # Calculate quota usage
        today = datetime.utcnow().date()
        month_start = today.replace(day=1)
        
        # Get daily usage
        daily_result = await db.execute(
            select(func.count(UserRequest.id)).where(
                UserRequest.session_id == session_id,
                func.date(UserRequest.created_at) == today
            )
        )
        daily_used = daily_result.scalar() or 0
        
        # Get monthly usage
        monthly_result = await db.execute(
            select(func.count(UserRequest.id)).where(
                UserRequest.session_id == session_id,
                func.date(UserRequest.created_at) >= month_start
            )
        )
        monthly_used = monthly_result.scalar() or 0
        
        # Calculate remaining quota
        remaining = max(0, settings.DAILY_QUOTA_LIMIT - daily_used)
        quota_available = remaining > 0
        
        return QuotaResponse(
            dailyUsed=daily_used,
            dailyLimit=settings.DAILY_QUOTA_LIMIT,
            monthlyUsed=monthly_used,
            monthlyLimit=settings.MONTHLY_QUOTA_LIMIT,
            remaining=remaining,
            quotaAvailable=quota_available
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "QuotaRetrievalError",
                "message": "Failed to retrieve quota information",
                "details": {"error_type": type(e).__name__}
            }
        )


@router.put("/{session_id}/preferences")
async def update_session_preferences(
    session_id: str,
    preferences: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Update session preferences.
    
    Args:
        session_id: Session identifier
        preferences: New preferences to set
        db: Database session dependency
        
    Returns:
        Success message
        
    Raises:
        HTTPException: When session is not found or update fails
    """
    try:
        # Find session
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "SessionNotFound",
                    "message": f"Session {session_id} not found"
                }
            )
        
        # Update preferences
        session.preferences = preferences
        session.last_active = datetime.utcnow()
        
        await db.commit()
        
        return {"message": "Preferences updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "PreferencesUpdateError",
                "message": "Failed to update preferences",
                "details": {"error_type": type(e).__name__}
            }
        )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete a session and all associated data.
    
    Args:
        session_id: Session identifier
        db: Database session dependency
        
    Returns:
        Success message
        
    Raises:
        HTTPException: When session is not found or deletion fails
    """
    try:
        # Find session
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "SessionNotFound",
                    "message": f"Session {session_id} not found"
                }
            )
        
        # Delete session (cascade will handle related records)
        await db.delete(session)
        await db.commit()
        
        return {"message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "SessionDeletionError",
                "message": "Failed to delete session",
                "details": {"error_type": type(e).__name__}
            }
        )


@router.get("/{session_id}/history")
async def get_session_history(
    session_id: str,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get session request history.
    
    Args:
        session_id: Session identifier
        limit: Maximum number of records to return
        offset: Number of records to skip
        db: Database session dependency
        
    Returns:
        Session request history
        
    Raises:
        HTTPException: When session is not found or query fails
    """
    try:
        # Verify session exists
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "SessionNotFound",
                    "message": f"Session {session_id} not found"
                }
            )
        
        # Get request history
        history_result = await db.execute(
            select(UserRequest)
            .where(UserRequest.session_id == session_id)
            .order_by(UserRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        requests = history_result.scalars().all()
        
        # Get total count
        count_result = await db.execute(
            select(func.count(UserRequest.id))
            .where(UserRequest.session_id == session_id)
        )
        total_count = count_result.scalar() or 0
        
        # Format response
        history_items = []
        for req in requests:
            history_items.append({
                "id": req.id,
                "requestType": req.request_type,
                "topic": req.topic,
                "dateRequested": req.date_requested,
                "createdAt": req.created_at.isoformat()
            })
        
        return {
            "history": history_items,
            "totalCount": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "HistoryRetrievalError",
                "message": "Failed to retrieve session history",
                "details": {"error_type": type(e).__name__}
            }
        )
