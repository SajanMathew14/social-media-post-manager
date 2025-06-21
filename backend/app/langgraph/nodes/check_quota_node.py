"""
Quota checking node for news processing workflow.

This node follows LangGraph best practices:
- Single responsibility: Quota validation and tracking
- Database operations with proper error handling
- Immutable state updates
- Comprehensive logging
"""
import time
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.langgraph.state.news_state import NewsState, QuotaInfo, mark_step_completed, mark_step_error
from app.langgraph.utils.logging_config import StructuredLogger
from app.langgraph.utils.error_handlers import (
    QuotaExceededError,
    DuplicateRequestError,
    DatabaseError,
    handle_node_error
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user_request import UserRequest
from app.models.session import Session


class CheckQuotaNode:
    """
    Checks user quota and prevents duplicate requests.
    
    Responsibilities:
    - Verify daily and monthly quota limits
    - Check for duplicate requests using hash
    - Create session if it doesn't exist
    - Track request in database
    - Update quota information in state
    
    This node ensures users don't exceed their allocated
    quotas and prevents duplicate processing.
    """
    
    def __init__(self):
        """Initialize quota checking node with structured logger."""
        self.logger = StructuredLogger("check_quota")
        self.node_name = "check_quota"
    
    async def __call__(self, state: NewsState) -> NewsState:
        """
        Execute quota checking and request tracking.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with quota information
            
        Raises:
            QuotaExceededError: When quota limits are exceeded
            DuplicateRequestError: When duplicate request is detected
            DatabaseError: When database operations fail
        """
        start_time = time.time()
        
        # Log node entry
        self.logger.log_node_entry(
            session_id=state["session_id"],
            workflow_id=state["workflow_id"],
            step="quota_check",
            extra_data={
                "topic": state["topic"],
                "date": state["date"]
            }
        )
        
        try:
            # Update state to show current processing step
            new_state = state.copy()
            new_state["current_step"] = "Checking quota and duplicate requests"
            
            async with AsyncSessionLocal() as db_session:
                # Ensure session exists
                await self._ensure_session_exists(db_session, state["session_id"])
                
                # Generate request hash for duplicate detection
                request_hash = self._generate_request_hash(state["topic"], state["date"], state["session_id"])
                
                # Check for duplicate requests
                await self._check_duplicate_request(
                    db_session, 
                    state["session_id"], 
                    request_hash,
                    state["workflow_id"]
                )
                
                # Get current quota usage
                quota_info = await self._get_quota_info(db_session, state["session_id"])
                
                # Check quota limits
                self._validate_quota_limits(quota_info, state["workflow_id"])
                
                # Record this request
                await self._record_request(
                    db_session,
                    state["session_id"],
                    state["topic"],
                    state["date"],
                    request_hash
                )
                
                # Update quota info after recording request
                quota_info["daily_used"] += 1
                quota_info["monthly_used"] += 1
                quota_info["remaining"] = quota_info["daily_limit"] - quota_info["daily_used"]
                quota_info["quota_available"] = quota_info["remaining"] > 0
                
                # Commit the transaction
                await db_session.commit()
            
            # Update state with quota information
            new_state["quota_info"] = quota_info
            
            self.logger.log_processing_step(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="quota_check",
                message=f"Quota check passed. Daily: {quota_info['daily_used']}/{quota_info['daily_limit']}, Monthly: {quota_info['monthly_used']}/{quota_info['monthly_limit']}",
                extra_data=quota_info
            )
            
            # Mark quota check as completed
            completed_state = mark_step_completed(
                new_state,
                "quota_check",
                f"Quota validated. Remaining: {quota_info['remaining']} requests today"
            )
            
            # Log successful completion
            duration = time.time() - start_time
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="quota_check",
                success=True,
                duration=duration,
                extra_data=quota_info
            )
            
            return completed_state
            
        except (QuotaExceededError, DuplicateRequestError):
            # Re-raise quota and duplicate errors as-is
            duration = time.time() - start_time
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="quota_check",
                success=False,
                duration=duration
            )
            raise
        except Exception as e:
            # Handle unexpected errors
            duration = time.time() - start_time
            
            # Convert to custom error with context
            custom_error = handle_node_error(
                error=e,
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                node_name=self.node_name,
                step="quota_check"
            )
            
            # Log the error
            self.logger.log_error(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="quota_check",
                error=custom_error
            )
            
            # Log node exit with failure
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="quota_check",
                success=False,
                duration=duration
            )
            
            raise custom_error
    
    async def _ensure_session_exists(self, db_session: AsyncSession, session_id: str) -> None:
        """
        Ensure session exists in database, create if not found.
        
        Args:
            db_session: Database session
            session_id: Session identifier
            
        Raises:
            DatabaseError: When session operations fail
        """
        try:
            # Check if session exists
            result = await db_session.execute(
                select(Session).where(Session.id == session_id)
            )
            existing_session = result.scalar_one_or_none()
            
            if not existing_session:
                # Create new session
                new_session = Session(
                    id=session_id,
                    preferences={}
                )
                db_session.add(new_session)
                await db_session.flush()  # Ensure session is created
                
                self.logger.log_processing_step(
                    session_id=session_id,
                    workflow_id="",
                    step="session_creation",
                    message="Created new user session"
                )
            else:
                # Update last active timestamp
                existing_session.last_active = datetime.utcnow()
                
        except Exception as e:
            raise DatabaseError("session_management", str(e))
    
    def _generate_request_hash(self, topic: str, date: str, session_id: str) -> str:
        """
        Generate hash for duplicate request detection.
        
        Args:
            topic: News topic
            date: Request date
            session_id: User session identifier
            
        Returns:
            Request hash string
        """
        import hashlib
        
        # Normalize inputs for consistent hashing
        normalized_topic = topic.lower().strip()
        hash_input = f"{session_id}-{normalized_topic}-{date}"
        
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    async def _check_duplicate_request(
        self, 
        db_session: AsyncSession, 
        session_id: str, 
        request_hash: str,
        workflow_id: str
    ) -> None:
        """
        Check for duplicate requests within recent timeframe.
        
        Args:
            db_session: Database session
            session_id: Session identifier
            request_hash: Request hash for duplicate detection
            workflow_id: Workflow identifier for logging
            
        Raises:
            DuplicateRequestError: When duplicate request is found
            DatabaseError: When database query fails
        """
        try:
            # Check for duplicate requests in the last hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            result = await db_session.execute(
                select(UserRequest).where(
                    UserRequest.session_id == session_id,
                    UserRequest.request_hash == request_hash,
                    UserRequest.created_at >= one_hour_ago
                )
            )
            duplicate_request = result.scalar_one_or_none()
            
            if duplicate_request:
                self.logger.log_error(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    step="duplicate_check",
                    error=DuplicateRequestError(
                        request_hash, 
                        duplicate_request.created_at.isoformat()
                    )
                )
                
                raise DuplicateRequestError(
                    request_hash,
                    duplicate_request.created_at.isoformat()
                )
                
        except DuplicateRequestError:
            raise
        except Exception as e:
            raise DatabaseError("duplicate_check", str(e))
    
    async def _get_quota_info(self, db_session: AsyncSession, session_id: str) -> QuotaInfo:
        """
        Get current quota usage for the session.
        
        Args:
            db_session: Database session
            session_id: Session identifier
            
        Returns:
            Current quota information
            
        Raises:
            DatabaseError: When quota query fails
        """
        try:
            today = datetime.utcnow().date()
            month_start = today.replace(day=1)
            
            # Get daily usage
            daily_result = await db_session.execute(
                select(func.count(UserRequest.id)).where(
                    UserRequest.session_id == session_id,
                    func.date(UserRequest.created_at) == today
                )
            )
            daily_used = daily_result.scalar() or 0
            
            # Get monthly usage
            monthly_result = await db_session.execute(
                select(func.count(UserRequest.id)).where(
                    UserRequest.session_id == session_id,
                    func.date(UserRequest.created_at) >= month_start
                )
            )
            monthly_used = monthly_result.scalar() or 0
            
            return QuotaInfo(
                daily_used=daily_used,
                daily_limit=settings.DAILY_QUOTA_LIMIT,
                monthly_used=monthly_used,
                monthly_limit=settings.MONTHLY_QUOTA_LIMIT,
                remaining=settings.DAILY_QUOTA_LIMIT - daily_used,
                quota_available=(daily_used < settings.DAILY_QUOTA_LIMIT)
            )
            
        except Exception as e:
            raise DatabaseError("quota_query", str(e))
    
    def _validate_quota_limits(self, quota_info: QuotaInfo, workflow_id: str) -> None:
        """
        Validate that quota limits are not exceeded.
        
        Args:
            quota_info: Current quota information
            workflow_id: Workflow identifier for logging
            
        Raises:
            QuotaExceededError: When quota limits are exceeded
        """
        # Check daily quota
        if quota_info["daily_used"] >= quota_info["daily_limit"]:
            raise QuotaExceededError(
                "daily",
                quota_info["daily_used"],
                quota_info["daily_limit"]
            )
        
        # Check monthly quota
        if quota_info["monthly_used"] >= quota_info["monthly_limit"]:
            raise QuotaExceededError(
                "monthly",
                quota_info["monthly_used"],
                quota_info["monthly_limit"]
            )
    
    async def _record_request(
        self,
        db_session: AsyncSession,
        session_id: str,
        topic: str,
        date: str,
        request_hash: str
    ) -> None:
        """
        Record the current request in the database.
        
        Args:
            db_session: Database session
            session_id: Session identifier
            topic: News topic
            date: Request date
            request_hash: Request hash
            
        Raises:
            DatabaseError: When request recording fails
        """
        try:
            new_request = UserRequest(
                session_id=session_id,
                request_type="news_fetch",
                topic=topic,
                date_requested=date,
                request_hash=request_hash
            )
            
            db_session.add(new_request)
            await db_session.flush()  # Ensure request is recorded
            
        except Exception as e:
            raise DatabaseError("request_recording", str(e))
