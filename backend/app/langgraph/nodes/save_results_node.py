"""
Results saving node for news processing workflow.

This node follows LangGraph best practices:
- Single responsibility: Cache results and finalize processing
- Database operations with proper error handling
- Immutable state updates
- Comprehensive logging
"""
import time
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.langgraph.state.news_state import NewsState, NewsArticle, mark_step_completed, calculate_processing_time
from app.langgraph.utils.logging_config import StructuredLogger
from app.langgraph.utils.error_handlers import (
    DatabaseError,
    handle_node_error
)
from app.core.database import AsyncSessionLocal
from app.models.news_cache import NewsCache


class SaveResultsNode:
    """
    Saves processed results to cache and finalizes workflow.
    
    Responsibilities:
    - Cache processed articles in database
    - Calculate final processing metrics
    - Update state with final results
    - Clean up and finalize workflow
    
    This node ensures results are persisted for future
    use and provides final processing statistics.
    """
    
    def __init__(self):
        """Initialize results saving node with structured logger."""
        self.logger = StructuredLogger("save_results")
        self.node_name = "save_results"
    
    async def __call__(self, state: NewsState) -> NewsState:
        """
        Execute results saving and workflow finalization.
        
        Args:
            state: Current workflow state with summarized articles
            
        Returns:
            Updated state with final results and metrics
            
        Raises:
            DatabaseError: When database operations fail
        """
        start_time = time.time()
        
        # Log node entry
        self.logger.log_node_entry(
            session_id=state["session_id"],
            workflow_id=state["workflow_id"],
            step="save_results",
            extra_data={
                "articles_count": len(state["summarized_articles"] or [])
            }
        )
        
        try:
            # Update state to show current processing step
            new_state = state.copy()
            new_state["current_step"] = "Saving results and finalizing"
            
            # Get summarized articles
            summarized_articles = state.get("summarized_articles", [])
            
            if summarized_articles:
                # Save articles to cache
                await self._save_articles_to_cache(
                    articles=summarized_articles,
                    topic=state["topic"],
                    date=state["date"],
                    session_id=state["session_id"],
                    workflow_id=state["workflow_id"]
                )
                
                self.logger.log_processing_step(
                    session_id=state["session_id"],
                    workflow_id=state["workflow_id"],
                    step="articles_cached",
                    message=f"Cached {len(summarized_articles)} articles",
                    extra_data={"cached_count": len(summarized_articles)}
                )
            
            # Calculate final processing time
            final_state = calculate_processing_time(new_state)
            
            # Update final metrics
            final_state["current_step"] = "Processing complete"
            
            # Log final statistics
            self.logger.log_processing_step(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="workflow_complete",
                message="News processing workflow completed successfully",
                extra_data={
                    "total_articles": len(summarized_articles),
                    "processing_time": final_state.get("processing_time"),
                    "llm_providers_tried": final_state.get("llm_providers_tried", []),
                    "final_provider": final_state.get("current_llm_provider"),
                    "cache_hit": final_state.get("cache_hit", False)
                }
            )
            
            # Mark save as completed
            completed_state = mark_step_completed(
                final_state,
                "save_results",
                f"Workflow completed. Processed {len(summarized_articles)} articles in {final_state.get('processing_time', 0):.2f}s"
            )
            
            # Log successful completion
            duration = time.time() - start_time
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="save_results",
                success=True,
                duration=duration,
                extra_data={
                    "final_articles_count": len(summarized_articles),
                    "total_processing_time": completed_state.get("processing_time")
                }
            )
            
            return completed_state
            
        except DatabaseError:
            # Re-raise database errors as-is
            duration = time.time() - start_time
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="save_results",
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
                step="save_results"
            )
            
            # Log the error
            self.logger.log_error(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="save_results",
                error=custom_error
            )
            
            # Log node exit with failure
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="save_results",
                success=False,
                duration=duration
            )
            
            raise custom_error
    
    async def _save_articles_to_cache(
        self,
        articles: List[NewsArticle],
        topic: str,
        date: str,
        session_id: str,
        workflow_id: str
    ) -> None:
        """
        Save processed articles to database cache.
        
        Args:
            articles: List of processed articles to cache
            topic: Topic for the articles
            date: Date for the articles
            session_id: Session identifier for logging
            workflow_id: Workflow identifier for logging
            
        Raises:
            DatabaseError: When caching operations fail
        """
        try:
            async with AsyncSessionLocal() as db_session:
                cached_count = 0
                
                for article in articles:
                    try:
                        # Check if article already exists in cache
                        existing_cache = await self._check_existing_cache(
                            db_session,
                            article.get("content_hash", "")
                        )
                        
                        if existing_cache:
                            # Article already cached, skip
                            continue
                        
                        # Create new cache entry
                        cache_entry = NewsCache(
                            topic=topic,
                            date_fetched=date,
                            source=article.get("source", ""),
                            title=article.get("title", ""),
                            url=article.get("url", ""),
                            summary=article.get("summary", ""),
                            content_hash=article.get("content_hash", "")
                        )
                        
                        db_session.add(cache_entry)
                        cached_count += 1
                        
                    except Exception as e:
                        # Log individual article caching failure but continue
                        self.logger.log_processing_step(
                            session_id=session_id,
                            workflow_id=workflow_id,
                            step="article_cache_failed",
                            message=f"Failed to cache article: {str(e)}",
                            extra_data={
                                "article_title": article.get("title", "")[:50],
                                "error": str(e)
                            }
                        )
                        continue
                
                # Commit all cache entries
                await db_session.commit()
                
                self.logger.log_processing_step(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    step="cache_commit",
                    message=f"Successfully cached {cached_count} new articles",
                    extra_data={
                        "total_articles": len(articles),
                        "cached_articles": cached_count,
                        "skipped_articles": len(articles) - cached_count
                    }
                )
                
        except Exception as e:
            raise DatabaseError("article_caching", str(e))
    
    async def _check_existing_cache(
        self,
        db_session: AsyncSession,
        content_hash: str
    ) -> bool:
        """
        Check if article already exists in cache.
        
        Args:
            db_session: Database session
            content_hash: Content hash to check
            
        Returns:
            True if article exists in cache, False otherwise
        """
        if not content_hash:
            return False
        
        try:
            from sqlalchemy import select
            
            result = await db_session.execute(
                select(NewsCache).where(NewsCache.content_hash == content_hash)
            )
            existing = result.scalar_one_or_none()
            
            return existing is not None
            
        except Exception:
            # If check fails, assume article doesn't exist
            return False
