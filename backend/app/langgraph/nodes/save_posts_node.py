"""
Save posts node for LangGraph workflow.

This node saves generated LinkedIn and X posts to the database.
"""
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.langgraph.state.post_state import (
    PostState,
    PostGenerationStatus,
    mark_post_step_completed,
    mark_post_step_error,
    calculate_post_processing_time
)
from datetime import datetime
from app.langgraph.utils.logging_config import StructuredLogger
from app.langgraph.utils.error_handlers import DatabaseError
from app.core.database import AsyncSessionLocal
from app.models.generated_post import GeneratedPost, PostType
from app.models.session import Session


class SavePostsNode:
    """
    Node for saving generated posts to the database.
    
    This node:
    1. Saves LinkedIn and X posts to the database
    2. Links posts to the session and news workflow
    3. Tracks generation metadata
    """
    
    def __init__(self):
        """Initialize save posts node with logger."""
        self.logger = StructuredLogger("save_posts_node")
    
    async def _create_db_session(self) -> AsyncSession:
        """
        Create a new database session for workflow operations.
        
        Returns:
            AsyncSession: Database session
            
        Raises:
            DatabaseError: If session creation fails
        """
        try:
            # Create session using the async session factory
            session = AsyncSessionLocal()
            
            self.logger.log_processing_step(
                session_id="system",
                workflow_id="system",
                step="db_session_created",
                message="Database session created successfully"
            )
            
            return session
            
        except Exception as e:
            self.logger.log_error(
                session_id="system",
                workflow_id="system",
                step="db_session_creation_failed",
                error=e
            )
            raise DatabaseError(
                operation="session_creation",
                original_error=str(e)
            )
    
    async def _validate_session(self, db: AsyncSession, session_id: str) -> bool:
        """
        Validate that the session exists in the database.
        
        Args:
            db: Database session
            session_id: Session ID to validate
            
        Returns:
            True if session exists, False otherwise
        """
        try:
            # Convert string session_id to UUID
            session_uuid = uuid.UUID(session_id)
            
            # Check if session exists
            result = await db.execute(
                select(Session).where(Session.id == session_uuid)
            )
            session = result.scalar_one_or_none()
            
            return session is not None
            
        except (ValueError, TypeError) as e:
            self.logger.log_error(
                session_id=session_id,
                workflow_id="validation",
                step="session_validation",
                error=e,
                extra_data={"session_id": session_id}
            )
            return False
    
    async def _save_post(
        self,
        db: AsyncSession,
        state: PostState,
        post_type: PostType,
        content: str,
        char_count: int
    ) -> GeneratedPost:
        """
        Save a single post to the database.
        
        Args:
            db: Database session
            state: Current workflow state
            post_type: Type of post (LinkedIn or X)
            content: Post content
            char_count: Character count
            
        Returns:
            Created GeneratedPost instance
        """
        # Convert string session_id to UUID
        session_uuid = uuid.UUID(state["session_id"])
        
        # Create post record
        post = GeneratedPost(
            session_id=session_uuid,
            post_type=post_type,
            content=content,
            char_count=char_count,
            edited=False,
            model_used=state["llm_model"],
            news_workflow_id=state["news_workflow_id"],
            articles_count=len(state["articles"]),
            topic=state["topic"]
        )
        
        db.add(post)
        await db.flush()  # Flush to get the ID
        
        return post
    
    async def __call__(self, state: PostState) -> PostState:
        """
        Save generated posts to the database.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with save confirmation
        """
        db = None
        try:
            # Validate critical state fields first
            session_id = state.get("session_id", "")
            workflow_id = state.get("workflow_id", "")
            
            # Validate required fields
            if not session_id:
                error_msg = "Session ID is missing from workflow state"
                self.logger.log_error(
                    session_id="unknown",
                    workflow_id=workflow_id or "unknown",
                    step="save_posts_validation_failed",
                    error=error_msg,
                    extra_data={
                        "state_keys": list(state.keys()),
                        "has_linkedin_post": state.get("linkedin_post") is not None,
                        "has_x_post": state.get("x_post") is not None
                    }
                )
                raise ValueError(error_msg)
            
            if not workflow_id:
                error_msg = "Workflow ID is missing from workflow state"
                self.logger.log_error(
                    session_id=session_id,
                    workflow_id="unknown",
                    step="save_posts_validation_failed",
                    error=error_msg,
                    extra_data={"state_keys": list(state.keys())}
                )
                raise ValueError(error_msg)
            
            # Log start of save operation with detailed context
            self.logger.log_processing_step(
                session_id=session_id,
                workflow_id=workflow_id,
                step="save_posts_start",
                message="Starting database save operation for generated posts",
                extra_data={
                    "has_linkedin": state.get("linkedin_post") is not None,
                    "has_x": state.get("x_post") is not None,
                    "session_id": session_id,
                    "news_workflow_id": state.get("news_workflow_id", ""),
                    "topic": state.get("topic", ""),
                    "article_count": len(state.get("articles", []))
                }
            )
            
            # Validate that we have at least one post to save
            if not state.get("linkedin_post") and not state.get("x_post"):
                error_msg = "No posts generated to save - both LinkedIn and X posts are missing"
                self.logger.log_error(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    step="save_posts_validation_failed",
                    error=error_msg
                )
                raise ValueError(error_msg)
            
            # Create database session
            self.logger.log_processing_step(
                session_id=session_id,
                workflow_id=workflow_id,
                step="creating_db_session",
                message="Creating database session for post save operation"
            )
            
            db = await self._create_db_session()
            
            # Validate session exists
            self.logger.log_processing_step(
                session_id=session_id,
                workflow_id=workflow_id,
                step="validating_user_session",
                message=f"Validating user session: {session_id}"
            )
            
            if not await self._validate_session(db, session_id):
                error_msg = f"Invalid or non-existent session ID: {session_id}"
                self.logger.log_error(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    step="session_validation_failed",
                    error=error_msg
                )
                raise DatabaseError(
                    operation="session_validation",
                    original_error=error_msg
                )
            
            saved_posts = []
            
            # Save LinkedIn post if generated
            if state.get("linkedin_post"):
                self.logger.log_processing_step(
                    session_id=state["session_id"],
                    workflow_id=state["workflow_id"],
                    step="saving_linkedin_post",
                    message="Saving LinkedIn post to database",
                    extra_data={
                        "char_count": state["linkedin_post"]["char_count"],
                        "has_hashtags": bool(state["linkedin_post"].get("hashtags"))
                    }
                )
                
                linkedin_post = await self._save_post(
                    db,
                    state,
                    PostType.LINKEDIN,
                    state["linkedin_post"]["content"],
                    state["linkedin_post"]["char_count"]
                )
                saved_posts.append({
                    "type": "linkedin",
                    "id": linkedin_post.id,
                    "char_count": linkedin_post.char_count
                })
                
                self.logger.log_processing_step(
                    session_id=state["session_id"],
                    workflow_id=state["workflow_id"],
                    step="linkedin_post_saved",
                    message=f"Successfully saved LinkedIn post to database",
                    extra_data={
                        "post_id": linkedin_post.id,
                        "char_count": linkedin_post.char_count
                    }
                )
            
            # Save X post if generated
            if state.get("x_post"):
                self.logger.log_processing_step(
                    session_id=state["session_id"],
                    workflow_id=state["workflow_id"],
                    step="saving_x_post",
                    message="Saving X post to database",
                    extra_data={
                        "char_count": state["x_post"]["char_count"],
                        "has_hashtags": bool(state["x_post"].get("hashtags")),
                        "has_shortened_urls": bool(state["x_post"].get("shortened_urls"))
                    }
                )
                
                x_post = await self._save_post(
                    db,
                    state,
                    PostType.X,
                    state["x_post"]["content"],
                    state["x_post"]["char_count"]
                )
                saved_posts.append({
                    "type": "x",
                    "id": x_post.id,
                    "char_count": x_post.char_count
                })
                
                self.logger.log_processing_step(
                    session_id=state["session_id"],
                    workflow_id=state["workflow_id"],
                    step="x_post_saved",
                    message=f"Successfully saved X post to database",
                    extra_data={
                        "post_id": x_post.id,
                        "char_count": x_post.char_count
                    }
                )
            
            # Commit all changes
            self.logger.log_processing_step(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="committing_transaction",
                message="Committing database transaction"
            )
            
            await db.commit()
            
            # Calculate final processing time
            processing_time = None
            if state.get("start_time"):
                processing_time = datetime.utcnow().timestamp() - state["start_time"]
            
            # Log successful save with comprehensive details
            self.logger.log_processing_step(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="save_posts_complete",
                message=f"Successfully saved {len(saved_posts)} posts to database",
                extra_data={
                    "saved_posts": saved_posts,
                    "processing_time": processing_time,
                    "total_posts_saved": len(saved_posts),
                    "linkedin_saved": any(p["type"] == "linkedin" for p in saved_posts),
                    "x_saved": any(p["type"] == "x" for p in saved_posts)
                }
            )
            
            # With LangGraph 0.4.8, we can return partial state updates
            # The Annotated reducers will handle preserving immutable fields
            return {
                "current_step": "save_posts",
                "processing_time": processing_time,
                "processing_steps": [
                    {
                        "step": "save_posts",
                        "status": PostGenerationStatus.COMPLETED,
                        "message": f"Successfully saved {len(saved_posts)} posts to database",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
            
        except DatabaseError as e:
            # Handle database-specific errors
            if db:
                try:
                    await db.rollback()
                    self.logger.log_processing_step(
                        session_id=state["session_id"],
                        workflow_id=state["workflow_id"],
                        step="transaction_rollback",
                        message="Database transaction rolled back due to error"
                    )
                except Exception as rollback_error:
                    self.logger.log_error(
                        session_id=state["session_id"],
                        workflow_id=state["workflow_id"],
                        step="rollback_failed",
                        error=rollback_error
                    )
            
            self.logger.log_error(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="save_posts_database_error",
                error=e,
                extra_data={
                    "error_type": "DatabaseError",
                    "operation": e.context.get("operation", "unknown"),
                    "has_linkedin": state.get("linkedin_post") is not None,
                    "has_x": state.get("x_post") is not None
                }
            )
            
            # Create error state update maintaining all existing fields
            error_state = state.copy()
            error_state.update({
                "error_message": f"Database error during post save: {e.message}",
                "failed_step": "save_posts",
                "current_step": "save_posts",
                "processing_steps": [
                    {
                        "step": "save_posts",
                        "status": PostGenerationStatus.ERROR,
                        "message": f"Database error during post save: {e.message}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            })
            
            return error_state
            
        except Exception as e:
            # Handle unexpected errors
            if db:
                try:
                    await db.rollback()
                    self.logger.log_processing_step(
                        session_id=state["session_id"],
                        workflow_id=state["workflow_id"],
                        step="transaction_rollback",
                        message="Database transaction rolled back due to unexpected error"
                    )
                except Exception as rollback_error:
                    self.logger.log_error(
                        session_id=state["session_id"],
                        workflow_id=state["workflow_id"],
                        step="rollback_failed",
                        error=rollback_error
                    )
            
            self.logger.log_error(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="save_posts_unexpected_error",
                error=e,
                extra_data={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "has_linkedin": state.get("linkedin_post") is not None,
                    "has_x": state.get("x_post") is not None,
                    "session_id": state["session_id"],
                    "workflow_id": state["workflow_id"]
                }
            )
            
            # Create error state update maintaining all existing fields
            error_state = state.copy()
            error_state.update({
                "error_message": f"Unexpected error during post save: {str(e)} (Type: {type(e).__name__})",
                "failed_step": "save_posts",
                "current_step": "save_posts",
                "processing_steps": [
                    {
                        "step": "save_posts",
                        "status": PostGenerationStatus.ERROR,
                        "message": f"Unexpected error during post save: {str(e)} (Type: {type(e).__name__})",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            })
            
            return error_state
            
        finally:
            # Ensure database session is properly closed
            if db:
                try:
                    await db.close()
                    self.logger.log_processing_step(
                        session_id=state.get("session_id", "unknown"),
                        workflow_id=state.get("workflow_id", "unknown"),
                        step="db_session_closed",
                        message="Database session closed successfully"
                    )
                except Exception as close_error:
                    self.logger.log_error(
                        session_id=state.get("session_id", "unknown"),
                        workflow_id=state.get("workflow_id", "unknown"),
                        step="db_session_close_failed",
                        error=close_error
                    )
