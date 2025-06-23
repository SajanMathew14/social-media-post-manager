"""
LangGraph state definitions
"""
from .news_state import (
    NewsState,
    ProcessingStatus,
    ProcessingStep,
    QuotaInfo,
    NewsArticle,
    create_initial_state,
    update_processing_step,
    mark_step_completed,
    mark_step_error,
    calculate_processing_time
)

from .post_state import (
    PostState,
    PostGenerationStatus,
    PostProcessingStep,
    NewsArticleInput,
    GeneratedPostContent,
    create_initial_post_state,
    update_post_processing_step,
    mark_post_step_completed,
    mark_post_step_error,
    calculate_post_processing_time,
    format_article_for_prompt
)

__all__ = [
    # News state exports
    "NewsState",
    "ProcessingStatus",
    "ProcessingStep",
    "QuotaInfo",
    "NewsArticle",
    "create_initial_state",
    "update_processing_step",
    "mark_step_completed",
    "mark_step_error",
    "calculate_processing_time",
    
    # Post state exports
    "PostState",
    "PostGenerationStatus",
    "PostProcessingStep",
    "NewsArticleInput",
    "GeneratedPostContent",
    "create_initial_post_state",
    "update_post_processing_step",
    "mark_post_step_completed",
    "mark_post_step_error",
    "calculate_post_processing_time",
    "format_article_for_prompt"
]
