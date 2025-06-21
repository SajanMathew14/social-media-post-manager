"""
Typed state definitions for LangGraph post generation workflow
"""
from typing import TypedDict, List, Optional, Dict, Any, Annotated
from datetime import datetime
from enum import Enum
from langgraph.graph import add_messages


class PostGenerationStatus(Enum):
    """Post generation status enumeration"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    ERROR = "error"


class PostProcessingStep(TypedDict):
    """Individual post processing step"""
    step: str
    status: PostGenerationStatus
    message: Optional[str]
    timestamp: str


def add_processing_steps(left: List[PostProcessingStep], right: List[PostProcessingStep]) -> List[PostProcessingStep]:
    """
    Custom reducer for processing steps that handles parallel updates.
    
    Args:
        left: Existing processing steps
        right: New processing steps to add
        
    Returns:
        Combined list of processing steps
    """
    return left + right


def keep_first_articles(left: List["NewsArticleInput"], right: List["NewsArticleInput"]) -> List["NewsArticleInput"]:
    """
    Custom reducer for articles that keeps the first (original) value.
    
    Args:
        left: Existing articles
        right: New articles (ignored)
        
    Returns:
        Original articles list
    """
    return left


class NewsArticleInput(TypedDict):
    """Simplified news article for post generation"""
    title: str
    url: str
    source: str
    summary: str
    published_at: Optional[str]
    relevance_score: Optional[float]


class GeneratedPostContent(TypedDict):
    """Generated post content with metadata"""
    content: str
    char_count: int
    hashtags: Optional[List[str]]
    shortened_urls: Optional[Dict[str, str]]  # original -> shortened


class PostState(TypedDict):
    """
    Comprehensive state for post generation workflow.
    
    This state manages the generation of LinkedIn and X posts
    from news articles, following immutable update patterns.
    """
    
    # Input parameters (immutable throughout workflow)
    articles: Annotated[List[NewsArticleInput], keep_first_articles]
    topic: str
    llm_model: str
    session_id: str
    workflow_id: str
    news_workflow_id: str  # Link to original news workflow
    
    # Processing metadata
    start_time: float
    current_step: str
    processing_steps: Annotated[List[PostProcessingStep], add_processing_steps]
    
    # Generated content
    linkedin_post: Optional[GeneratedPostContent]
    x_post: Optional[GeneratedPostContent]
    
    # Processing results
    processing_time: Optional[float]
    
    # Error handling
    error_message: Optional[str]
    failed_step: Optional[str]
    retry_count: int
    
    # LLM provider tracking
    llm_providers_tried: List[str]
    current_llm_provider: str


def create_initial_post_state(
    articles: List[Dict[str, Any]],
    topic: str,
    llm_model: str,
    session_id: str,
    workflow_id: str,
    news_workflow_id: str
) -> PostState:
    """
    Create initial state for post generation workflow.
    
    Args:
        articles: List of news articles to generate posts from
        topic: News topic
        llm_model: LLM model to use for generation
        session_id: User session identifier
        workflow_id: Unique workflow execution identifier
        news_workflow_id: ID of the news workflow that produced these articles
        
    Returns:
        Initial PostState with all required fields
    """
    # Convert articles to simplified format
    article_inputs = []
    for article in articles:
        article_inputs.append(NewsArticleInput(
            title=article.get("title", ""),
            url=article.get("url", ""),
            source=article.get("source", ""),
            summary=article.get("summary", ""),
            published_at=article.get("published_at"),
            relevance_score=article.get("relevance_score")
        ))
    
    return PostState(
        # Input parameters
        articles=article_inputs,
        topic=topic,
        llm_model=llm_model,
        session_id=session_id,
        workflow_id=workflow_id,
        news_workflow_id=news_workflow_id,
        
        # Processing metadata
        start_time=datetime.utcnow().timestamp(),
        current_step="Initializing post generation",
        processing_steps=[],
        
        # Generated content
        linkedin_post=None,
        x_post=None,
        
        # Results
        processing_time=None,
        
        # Error handling
        error_message=None,
        failed_step=None,
        retry_count=0,
        
        # LLM tracking
        llm_providers_tried=[],
        current_llm_provider=llm_model
    )


def update_post_processing_step(
    state: PostState,
    step_name: str,
    status: PostGenerationStatus,
    message: Optional[str] = None
) -> PostState:
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
    new_step = PostProcessingStep(
        step=step_name,
        status=status,
        message=message,
        timestamp=datetime.utcnow().isoformat()
    )
    
    # For Annotated types with reducers, we only return the new steps to be added
    new_state["processing_steps"] = [new_step]
    
    return new_state


def mark_post_step_completed(
    state: PostState,
    step_name: str,
    message: Optional[str] = None
) -> PostState:
    """Mark a processing step as completed"""
    return update_post_processing_step(state, step_name, PostGenerationStatus.COMPLETED, message)


def mark_post_step_error(
    state: PostState,
    step_name: str,
    error_message: str
) -> PostState:
    """Mark a processing step as failed with error"""
    new_state = update_post_processing_step(state, step_name, PostGenerationStatus.ERROR, error_message)
    new_state["error_message"] = error_message
    new_state["failed_step"] = step_name
    return new_state


def calculate_post_processing_time(state: PostState) -> PostState:
    """Calculate and update processing time"""
    new_state = state.copy()
    if state["start_time"]:
        new_state["processing_time"] = datetime.utcnow().timestamp() - state["start_time"]
    return new_state


def format_article_for_prompt(article: NewsArticleInput) -> str:
    """Format a single article for LLM prompt"""
    parts = [
        f"Title: {article['title']}",
        f"Source: {article['source']}",
        f"Summary: {article['summary']}",
        f"URL: {article['url']}"
    ]
    
    if article.get('published_at'):
        parts.append(f"Published: {article['published_at']}")
    
    if article.get('relevance_score'):
        parts.append(f"Relevance: {article['relevance_score']:.2f}")
    
    return "\n".join(parts)
