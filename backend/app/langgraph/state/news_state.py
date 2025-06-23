"""
Typed state definitions for LangGraph news processing workflow
"""
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ProcessingStatus(Enum):
    """Processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class ProcessingStep(TypedDict):
    """Individual processing step"""
    step: str
    status: ProcessingStatus
    message: Optional[str]
    timestamp: str


class QuotaInfo(TypedDict):
    """Quota information"""
    daily_used: int
    daily_limit: int
    monthly_used: int
    monthly_limit: int
    remaining: int
    quota_available: bool


class NewsArticle(TypedDict):
    """News article structure"""
    title: str
    url: str
    source: str
    summary: str
    published_at: Optional[str]
    relevance_score: Optional[float]
    content_hash: str


class NewsState(TypedDict):
    """
    Comprehensive state for news processing workflow.
    
    This state follows immutable update patterns - each node should
    return a new state object with updates rather than modifying
    the existing state in place.
    """
    
    # Input parameters (immutable throughout workflow)
    topic: str
    date: str
    top_n: int
    llm_model: str
    session_id: str
    
    # Processing metadata
    workflow_id: str
    start_time: float
    current_step: str
    processing_steps: List[ProcessingStep]
    
    # Quota and validation
    quota_info: Optional[QuotaInfo]
    validation_errors: List[str]
    
    # Data flow through nodes (minimal state principle)
    raw_articles: Optional[List[Dict[str, Any]]]
    filtered_articles: Optional[List[NewsArticle]]
    summarized_articles: Optional[List[NewsArticle]]
    
    # Results and metadata
    total_found: int
    processing_time: Optional[float]
    cache_hit: bool
    
    # Error handling
    error_message: Optional[str]
    failed_step: Optional[str]
    retry_count: int
    
    # LLM provider fallback tracking
    llm_providers_tried: List[str]
    current_llm_provider: str


def create_initial_state(
    topic: str,
    date: str,
    top_n: int,
    llm_model: str,
    session_id: str,
    workflow_id: str
) -> NewsState:
    """
    Create initial state for news processing workflow.
    
    Args:
        topic: News topic to search for
        date: Date in YYYY-MM-DD format
        top_n: Number of articles to fetch (1-12)
        llm_model: LLM model to use for summarization
        session_id: User session identifier
        workflow_id: Unique workflow execution identifier
        
    Returns:
        Initial NewsState with all required fields
    """
    return NewsState(
        # Input parameters
        topic=topic,
        date=date,
        top_n=top_n,
        llm_model=llm_model,
        session_id=session_id,
        
        # Processing metadata
        workflow_id=workflow_id,
        start_time=datetime.utcnow().timestamp(),
        current_step="Initializing workflow",
        processing_steps=[],
        
        # Quota and validation
        quota_info=None,
        validation_errors=[],
        
        # Data flow
        raw_articles=None,
        filtered_articles=None,
        summarized_articles=None,
        
        # Results
        total_found=0,
        processing_time=None,
        cache_hit=False,
        
        # Error handling
        error_message=None,
        failed_step=None,
        retry_count=0,
        
        # LLM tracking
        llm_providers_tried=[],
        current_llm_provider=llm_model
    )


def update_processing_step(
    state: NewsState,
    step_name: str,
    status: ProcessingStatus,
    message: Optional[str] = None
) -> NewsState:
    """
    Immutably update processing steps in state.
    
    Args:
        state: Current state
        step_name: Name of the processing step
        status: Current status of the step
        message: Optional message for the step
        
    Returns:
        New state with updated processing steps
    """
    new_state = state.copy()
    new_state["current_step"] = step_name
    
    # Create new processing step
    new_step = ProcessingStep(
        step=step_name,
        status=status,
        message=message,
        timestamp=datetime.utcnow().isoformat()
    )
    
    # Immutably update processing steps
    new_state["processing_steps"] = state["processing_steps"] + [new_step]
    
    return new_state


def mark_step_completed(
    state: NewsState,
    step_name: str,
    message: Optional[str] = None
) -> NewsState:
    """Mark a processing step as completed"""
    return update_processing_step(state, step_name, ProcessingStatus.COMPLETED, message)


def mark_step_error(
    state: NewsState,
    step_name: str,
    error_message: str
) -> NewsState:
    """Mark a processing step as failed with error"""
    new_state = update_processing_step(state, step_name, ProcessingStatus.ERROR, error_message)
    new_state["error_message"] = error_message
    new_state["failed_step"] = step_name
    return new_state


def calculate_processing_time(state: NewsState) -> NewsState:
    """Calculate and update processing time"""
    new_state = state.copy()
    if state["start_time"]:
        new_state["processing_time"] = datetime.utcnow().timestamp() - state["start_time"]
    return new_state
