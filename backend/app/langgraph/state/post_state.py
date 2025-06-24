"""
Typed state definitions for LangGraph post generation workflow
"""
from typing import TypedDict, List, Optional, Dict, Any, Annotated, Union
from datetime import datetime
from enum import Enum
from operator import add


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


def keep_first_value(left: str, right: str) -> str:
    """
    Custom reducer that keeps the first (original) value.
    Used for immutable fields like topic, session_id, etc.
    
    Args:
        left: Existing value
        right: New value (ignored)
        
    Returns:
        Original value
    """
    return left


def keep_first_float(left: float, right: float) -> float:
    """
    Custom reducer that keeps the first (original) float value.
    Used for immutable numeric fields like start_time.
    
    Args:
        left: Existing value
        right: New value (ignored)
        
    Returns:
        Original value
    """
    return left


def use_latest_value(left: Any, right: Any) -> Any:
    """
    Custom reducer that uses the latest (most recent) value.
    Used for fields that should be updated by the last node to run.
    
    Args:
        left: Existing value
        right: New value
        
    Returns:
        New value if not None, otherwise existing value
    """
    return right if right is not None else left


def use_latest_optional_str(left: Optional[str], right: Optional[str]) -> Optional[str]:
    """
    Custom reducer for optional string fields that uses the latest non-None value.
    
    Args:
        left: Existing value
        right: New value
        
    Returns:
        New value if not None, otherwise existing value
    """
    return right if right is not None else left


def use_latest_optional_float(left: Optional[float], right: Optional[float]) -> Optional[float]:
    """
    Custom reducer for optional float fields that uses the latest non-None value.
    
    Args:
        left: Existing value
        right: New value
        
    Returns:
        New value if not None, otherwise existing value
    """
    return right if right is not None else left


def use_latest_optional_content(left: Optional["GeneratedPostContent"], right: Optional["GeneratedPostContent"]) -> Optional["GeneratedPostContent"]:
    """
    Custom reducer for optional GeneratedPostContent that uses the latest non-None value.
    
    Args:
        left: Existing value
        right: New value
        
    Returns:
        New value if not None, otherwise existing value
    """
    return right if right is not None else left


def add_integers(left: int, right: int) -> int:
    """
    Custom reducer that adds integer values.
    Used for counters like retry_count.
    
    Args:
        left: Existing value
        right: Value to add
        
    Returns:
        Sum of both values
    """
    return left + right


def combine_string_lists(left: List[str], right: List[str]) -> List[str]:
    """
    Custom reducer that combines string lists.
    Used for accumulating lists like llm_providers_tried.
    
    Args:
        left: Existing list
        right: New items to add
        
    Returns:
        Combined list
    """
    return left + right


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
    
    IMPORTANT: Every field is annotated with an appropriate reducer to handle
    parallel processing safely. This prevents InvalidUpdateError when multiple
    nodes update state simultaneously.
    """
    
    # Input parameters (immutable throughout workflow)
    articles: Annotated[List[NewsArticleInput], keep_first_articles]  # Original articles list
    topic: Annotated[str, keep_first_value]  # News topic - immutable
    llm_model: Annotated[str, keep_first_value]  # Initial LLM model - immutable
    session_id: Annotated[str, keep_first_value]  # User session - immutable
    workflow_id: Annotated[str, keep_first_value]  # Workflow ID - immutable
    news_workflow_id: Annotated[str, keep_first_value]  # Link to news workflow - immutable
    
    # Processing metadata
    start_time: Annotated[float, keep_first_float]  # Workflow start time - immutable
    current_step: Annotated[str, use_latest_value]  # Current processing step - updates
    processing_steps: Annotated[List[PostProcessingStep], add_processing_steps]  # Accumulates steps
    
    # Generated content (each node updates its own)
    linkedin_post: Annotated[Optional[GeneratedPostContent], use_latest_optional_content]  # LinkedIn result
    x_post: Annotated[Optional[GeneratedPostContent], use_latest_optional_content]  # X/Twitter result
    
    # Processing results
    processing_time: Annotated[Optional[float], use_latest_optional_float]  # Total time - updates
    
    # Error handling
    error_message: Annotated[Optional[str], use_latest_optional_str]  # Latest error message
    failed_step: Annotated[Optional[str], use_latest_optional_str]  # Which step failed
    retry_count: Annotated[int, add_integers]  # Total retries across all nodes
    
    # LLM provider tracking
    llm_providers_tried: Annotated[List[str], combine_string_lists]  # All providers attempted
    current_llm_provider: Annotated[str, use_latest_value]  # Currently active provider


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
