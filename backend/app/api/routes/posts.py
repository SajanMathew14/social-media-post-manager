"""
Post generation API routes for the Social Media Post Manager.

This module provides REST endpoints for generating and managing
LinkedIn and X posts from news articles.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid

from app.langgraph.workflows.post_workflow import execute_post_workflow
from app.langgraph.workflows.stateless_post_workflow import get_stateless_post_workflow
from app.langgraph.utils.error_handlers import (
    ValidationError,
    LLMProviderError,
    DatabaseError,
    NewsProcessingError
)
from app.core.dependencies import get_db
from app.models.generated_post import GeneratedPost, PostType
from app.models.session import Session

router = APIRouter()


class PostGenerationRequest(BaseModel):
    """Request model for post generation."""
    articles: List[Dict[str, Any]] = Field(..., min_items=1, max_items=12, description="News articles to generate posts from")
    topic: str = Field(..., min_length=2, max_length=100, description="News topic")
    llmModel: str = Field(..., description="LLM model to use for generation")
    sessionId: str = Field(..., description="User session identifier")
    newsWorkflowId: str = Field(..., description="ID of the news workflow that produced these articles")


class PostGenerationResponse(BaseModel):
    """Response model for post generation."""
    workflowId: str = Field(..., description="Unique workflow execution ID")
    processingTime: float = Field(..., description="Processing time in seconds")
    llmModelUsed: str = Field(..., description="LLM model that was used")
    posts: Dict[str, Dict[str, Any]] = Field(..., description="Generated posts by platform")


class PostUpdateRequest(BaseModel):
    """Request model for updating a post."""
    content: str = Field(..., min_length=1, description="Updated post content")


class PostResponse(BaseModel):
    """Response model for a single post."""
    id: int = Field(..., description="Post ID")
    sessionId: str = Field(..., description="Session ID")
    postType: str = Field(..., description="Post type (linkedin or x)")
    content: str = Field(..., description="Post content")
    originalContent: Optional[str] = Field(None, description="Original content if edited")
    charCount: int = Field(..., description="Character count")
    edited: bool = Field(..., description="Whether the post has been edited")
    modelUsed: str = Field(..., description="LLM model used")
    newsWorkflowId: str = Field(..., description="Related news workflow ID")
    articlesCount: int = Field(..., description="Number of articles used")
    topic: str = Field(..., description="Topic")
    createdAt: str = Field(..., description="Creation timestamp")
    updatedAt: str = Field(..., description="Last update timestamp")


@router.post("/generate", response_model=PostGenerationResponse)
async def generate_posts(
    request: PostGenerationRequest,
    db: AsyncSession = Depends(get_db)
) -> PostGenerationResponse:
    """
    Generate LinkedIn and X posts from news articles using the stateless workflow.
    
    This endpoint executes the post generation pipeline:
    1. Validates input articles
    2. Generates LinkedIn post (up to 3000 chars)
    3. Generates X post (up to 250 chars)
    4. Saves posts to database
    
    Args:
        request: Post generation request parameters
        db: Database session dependency
        
    Returns:
        Generated posts with metadata
        
    Raises:
        HTTPException: Various HTTP errors based on failure type
    """
    try:
        # Validate session exists
        session_uuid = uuid.UUID(request.sessionId)
        result = await db.execute(
            select(Session).where(Session.id == session_uuid)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise ValidationError(
                field="sessionId",
                value=request.sessionId,
                reason="Session ID does not exist in database"
            )
        
        # Execute stateless post generation workflow (NEW APPROACH)
        stateless_workflow = get_stateless_post_workflow()
        results = await stateless_workflow.execute(
            articles=request.articles,
            topic=request.topic,
            llm_model=request.llmModel,
            session_id=request.sessionId,
            news_workflow_id=request.newsWorkflowId
        )
        
        # Return successful response
        return PostGenerationResponse(
            workflowId=results["workflow_id"],
            processingTime=results["processing_time"],
            llmModelUsed=results["llm_model_used"],
            posts=results["posts"]
        )
        
    except ValidationError as e:
        # Input validation errors (400 Bad Request)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": e.message,
                "details": e.context
            }
        )
    
    except LLMProviderError as e:
        # LLM provider errors (502 Bad Gateway)
        raise HTTPException(
            status_code=502,
            detail={
                "error": "LLMProviderError",
                "message": f"AI service temporarily unavailable: {e.message}",
                "details": e.context
            }
        )
    
    except DatabaseError as e:
        # Database errors (500 Internal Server Error)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DatabaseError",
                "message": "Internal database error occurred",
                "details": {"operation": e.context.get("operation", "unknown")}
            }
        )
    
    except NewsProcessingError as e:
        # General processing errors (500 Internal Server Error)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ProcessingError",
                "message": e.message,
                "details": e.context
            }
        )
    
    except Exception as e:
        # Log the unexpected error with full details
        import traceback
        error_traceback = traceback.format_exc()
        
        # Log to application logger (this will appear in your backend logs)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            f"Unexpected error in post generation: {str(e)}\n"
            f"Error type: {type(e).__name__}\n"
            f"Session ID: {request.sessionId}\n"
            f"Topic: {request.topic}\n"
            f"LLM Model: {request.llmModel}\n"
            f"Article count: {len(request.articles)}\n"
            f"Traceback:\n{error_traceback}"
        )
        
        # Unexpected errors (500 Internal Server Error)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "UnexpectedError",
                "message": f"An unexpected error occurred during post generation: {str(e)}",
                "details": {
                    "error_type": type(e).__name__,
                    "session_id": request.sessionId,
                    "topic": request.topic,
                    "llm_model": request.llmModel,
                    "article_count": len(request.articles),
                    "error_message": str(e)
                }
            }
        )


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    request: PostUpdateRequest,
    db: AsyncSession = Depends(get_db)
) -> PostResponse:
    """
    Update the content of a generated post.
    
    Args:
        post_id: ID of the post to update
        request: Update request with new content
        db: Database session dependency
        
    Returns:
        Updated post details
        
    Raises:
        HTTPException: 404 if post not found, 400 for validation errors
    """
    try:
        # Fetch the post
        result = await db.execute(
            select(GeneratedPost).where(GeneratedPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"Post with ID {post_id} not found"
                }
            )
        
        # Validate character limits
        char_count = len(request.content)
        max_chars = 3000 if post.post_type == PostType.LINKEDIN else 250
        
        if char_count > max_chars:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": f"Content exceeds {max_chars} character limit",
                    "details": {
                        "char_count": char_count,
                        "max_chars": max_chars,
                        "post_type": post.post_type.value
                    }
                }
            )
        
        # Update the post
        if not post.edited:
            # First edit - save original content
            post.edited = True
            post.edited_content = request.content
            post.edited_char_count = char_count
        else:
            # Subsequent edit - update edited content
            post.edited_content = request.content
            post.edited_char_count = char_count
        
        post.updated_at = datetime.utcnow()
        
        # Commit changes
        await db.commit()
        await db.refresh(post)
        
        # Return updated post
        return PostResponse(**post.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DatabaseError",
                "message": "Failed to update post",
                "details": {"error_type": type(e).__name__}
            }
        )


@router.get("/session/{session_id}", response_model=List[PostResponse])
async def get_session_posts(
    session_id: str,
    post_type: Optional[str] = Query(None, description="Filter by post type (linkedin or x)"),
    db: AsyncSession = Depends(get_db)
) -> List[PostResponse]:
    """
    Get all posts for a session.
    
    Args:
        session_id: Session ID to fetch posts for
        post_type: Optional filter by post type
        db: Database session dependency
        
    Returns:
        List of posts for the session
        
    Raises:
        HTTPException: 400 for invalid parameters
    """
    try:
        # Validate session ID format
        session_uuid = uuid.UUID(session_id)
        
        # Build query
        query = select(GeneratedPost).where(GeneratedPost.session_id == session_uuid)
        
        # Apply post type filter if provided
        if post_type:
            if post_type not in ["linkedin", "x"]:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": "Invalid post type",
                        "details": {"valid_types": ["linkedin", "x"]}
                    }
                )
            post_type_enum = PostType.LINKEDIN if post_type == "linkedin" else PostType.X
            query = query.where(GeneratedPost.post_type == post_type_enum)
        
        # Order by creation date (newest first)
        query = query.order_by(GeneratedPost.created_at.desc())
        
        # Execute query
        result = await db.execute(query)
        posts = result.scalars().all()
        
        # Convert to response models
        return [PostResponse(**post.to_dict()) for post in posts]
        
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Invalid session ID format"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DatabaseError",
                "message": "Failed to fetch posts",
                "details": {"error_type": type(e).__name__}
            }
        )


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    db: AsyncSession = Depends(get_db)
) -> PostResponse:
    """
    Get a specific post by ID.
    
    Args:
        post_id: ID of the post to fetch
        db: Database session dependency
        
    Returns:
        Post details
        
    Raises:
        HTTPException: 404 if post not found
    """
    try:
        # Fetch the post
        result = await db.execute(
            select(GeneratedPost).where(GeneratedPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"Post with ID {post_id} not found"
                }
            )
        
        return PostResponse(**post.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DatabaseError",
                "message": "Failed to fetch post",
                "details": {"error_type": type(e).__name__}
            }
        )


@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete a generated post.
    
    Args:
        post_id: ID of the post to delete
        db: Database session dependency
        
    Returns:
        Deletion confirmation
        
    Raises:
        HTTPException: 404 if post not found
    """
    try:
        # Fetch the post
        result = await db.execute(
            select(GeneratedPost).where(GeneratedPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"Post with ID {post_id} not found"
                }
            )
        
        # Delete the post
        await db.delete(post)
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Post {post_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DatabaseError",
                "message": "Failed to delete post",
                "details": {"error_type": type(e).__name__}
            }
        )
