"""
News API routes for the Social Media Post Manager.

This module provides REST endpoints for news processing
using the LangGraph workflow system.
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime

from app.langgraph.workflows.news_workflow import execute_news_workflow
from app.langgraph.utils.error_handlers import (
    ValidationError,
    QuotaExceededError,
    DuplicateRequestError,
    SerperAPIError,
    LLMProviderError,
    DatabaseError,
    NewsProcessingError
)
from app.core.dependencies import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class NewsRequest(BaseModel):
    """Request model for news fetching."""
    topic: str = Field(..., min_length=2, max_length=100, description="News topic to search for")
    date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="Date in YYYY-MM-DD format")
    topN: int = Field(..., ge=1, le=12, description="Number of articles to fetch (1-12)")
    llmModel: str = Field(..., description="LLM model to use for summarization")
    sessionId: str = Field(..., description="User session identifier")


class NewsResponse(BaseModel):
    """Response model for news fetching."""
    articles: list = Field(..., description="List of processed news articles")
    totalFound: int = Field(..., description="Total number of articles found")
    processingTime: float = Field(..., description="Processing time in seconds")
    quotaRemaining: int = Field(..., description="Remaining quota for today")
    workflowId: str = Field(..., description="Unique workflow execution ID")
    llmProviderUsed: str = Field(..., description="LLM provider that was used")
    cacheHit: bool = Field(..., description="Whether results were cached")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")


@router.post("/fetch", response_model=NewsResponse)
async def fetch_news(
    request: NewsRequest,
    db: AsyncSession = Depends(get_db)
) -> NewsResponse:
    """
    Fetch and process news articles using LangGraph workflow.
    
    This endpoint executes the complete news processing pipeline:
    1. Validates input parameters
    2. Checks user quotas and prevents duplicates
    3. Fetches news from Serper API
    4. Filters articles by relevance and source priority
    5. Generates AI summaries using selected LLM
    6. Caches results for future use
    
    Args:
        request: News request parameters
        db: Database session dependency
        
    Returns:
        Processed news articles with metadata
        
    Raises:
        HTTPException: Various HTTP errors based on failure type
    """
    try:
        # Execute LangGraph workflow
        results = await execute_news_workflow(
            topic=request.topic,
            date=request.date,
            top_n=request.topN,
            llm_model=request.llmModel,
            session_id=request.sessionId
        )
        
        # Return successful response
        return NewsResponse(
            articles=results["articles"],
            totalFound=results["total_found"],
            processingTime=results["processing_time"],
            quotaRemaining=results["quota_remaining"],
            workflowId=results["workflow_id"],
            llmProviderUsed=results["llm_provider_used"],
            cacheHit=results["cache_hit"]
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
    
    except QuotaExceededError as e:
        # Quota exceeded errors (429 Too Many Requests)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "QuotaExceeded",
                "message": e.message,
                "details": e.context
            }
        )
    
    except DuplicateRequestError as e:
        # Duplicate request errors (409 Conflict)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "DuplicateRequest",
                "message": e.message,
                "details": e.context
            }
        )
    
    except SerperAPIError as e:
        # External API errors (502 Bad Gateway)
        raise HTTPException(
            status_code=502,
            detail={
                "error": "ExternalAPIError",
                "message": f"News service temporarily unavailable: {e.message}",
                "details": {"provider": "Serper", "context": e.context}
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
        # Unexpected errors (500 Internal Server Error)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "UnexpectedError",
                "message": "An unexpected error occurred",
                "details": {"error_type": type(e).__name__}
            }
        )


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for news service.
    
    Returns:
        Service health status
    """
    return {
        "status": "healthy",
        "service": "news",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/models")
async def get_available_models() -> Dict[str, Any]:
    """
    Get list of available LLM models.
    
    Returns:
        Available LLM models with descriptions
    """
    return {
        "models": [
            {
                "id": "claude-3-5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "provider": "Anthropic",
                "description": "Advanced reasoning and analysis capabilities",
                "recommended": True
            },
            {
                "id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "provider": "OpenAI",
                "description": "Fast and efficient with strong performance",
                "recommended": True
            },
            {
                "id": "gemini-pro",
                "name": "Gemini Pro",
                "provider": "Google",
                "description": "Multimodal capabilities and reasoning",
                "recommended": False
            }
        ]
    }


@router.get("/topics")
async def get_topic_suggestions() -> Dict[str, Any]:
    """
    Get suggested topics with their configurations.
    
    Returns:
        List of suggested topics
    """
    return {
        "topics": [
            {
                "name": "AI",
                "description": "Artificial Intelligence and Machine Learning",
                "keywords": ["AI", "artificial intelligence", "machine learning", "deep learning"],
                "category": "Technology"
            },
            {
                "name": "Finance",
                "description": "Financial markets and fintech",
                "keywords": ["finance", "fintech", "markets", "banking", "cryptocurrency"],
                "category": "Business"
            },
            {
                "name": "Healthcare",
                "description": "Healthcare and medical technology",
                "keywords": ["healthcare", "medical", "biotech", "pharmaceuticals"],
                "category": "Healthcare"
            },
            {
                "name": "Technology",
                "description": "General technology and innovation",
                "keywords": ["technology", "innovation", "startup", "software"],
                "category": "Technology"
            },
            {
                "name": "Business",
                "description": "Business news and corporate updates",
                "keywords": ["business", "corporate", "enterprise", "economy"],
                "category": "Business"
            }
        ]
    }
