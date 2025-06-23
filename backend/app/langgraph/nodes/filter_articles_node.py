"""
Article filtering node for news processing workflow.

This node follows LangGraph best practices:
- Single responsibility: Filter and rank articles by relevance
- Domain-aware filtering using topic configurations
- Comprehensive logging and error handling
- Immutable state updates
"""
import time
import hashlib
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.langgraph.state.news_state import NewsState, NewsArticle, mark_step_completed, mark_step_error
from app.langgraph.utils.logging_config import StructuredLogger
from app.langgraph.utils.error_handlers import (
    ContentFilteringError,
    TopicConfigError,
    DatabaseError,
    handle_node_error
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.topic_config import TopicConfig


class FilterArticlesNode:
    """
    Filters and ranks articles based on topic relevance and source priority.
    
    Responsibilities:
    - Load topic configuration from database
    - Filter articles by trusted sources
    - Calculate relevance scores based on keywords
    - Remove duplicates and low-quality content
    - Rank articles by relevance and source priority
    - Convert to standardized NewsArticle format
    
    This node implements domain-aware filtering to ensure
    high-quality, relevant articles are selected.
    """
    
    def __init__(self):
        """Initialize article filtering node with structured logger."""
        self.logger = StructuredLogger("filter_articles")
        self.node_name = "filter_articles"
        self.min_title_length = 10
        self.min_snippet_length = 20
    
    async def __call__(self, state: NewsState) -> NewsState:
        """
        Execute article filtering and ranking.
        
        Args:
            state: Current workflow state with raw articles
            
        Returns:
            Updated state with filtered articles
            
        Raises:
            ContentFilteringError: When filtering fails
            TopicConfigError: When topic configuration is invalid
        """
        start_time = time.time()
        
        # Log node entry
        self.logger.log_node_entry(
            session_id=state["session_id"],
            workflow_id=state["workflow_id"],
            step="filter_articles",
            extra_data={
                "topic": state["topic"],
                "raw_articles_count": len(state["raw_articles"] or [])
            }
        )
        
        try:
            # Update state to show current processing step
            new_state = state.copy()
            new_state["current_step"] = "Filtering articles by relevance and source"
            
            # Check if we have articles to filter
            raw_articles = state.get("raw_articles", [])
            if not raw_articles:
                self.logger.log_processing_step(
                    session_id=state["session_id"],
                    workflow_id=state["workflow_id"],
                    step="no_articles",
                    message="No articles to filter"
                )
                
                new_state["filtered_articles"] = []
                return mark_step_completed(
                    new_state,
                    "filter_articles",
                    "No articles to filter"
                )
            
            # Load topic configuration
            topic_config = await self._load_topic_config(
                state["topic"],
                state["session_id"],
                state["workflow_id"]
            )
            
            # Filter articles by quality
            quality_filtered = self._filter_by_quality(
                raw_articles,
                state["session_id"],
                state["workflow_id"]
            )
            
            # Remove duplicates
            deduplicated = self._remove_duplicates(
                quality_filtered,
                state["session_id"],
                state["workflow_id"]
            )
            
            # Calculate relevance scores
            scored_articles = self._calculate_relevance_scores(
                deduplicated,
                topic_config,
                state["session_id"],
                state["workflow_id"]
            )
            
            # Apply source priority filtering
            source_filtered = self._filter_by_source_priority(
                scored_articles,
                topic_config,
                state["session_id"],
                state["workflow_id"]
            )
            
            # Sort by relevance and limit to requested number
            final_articles = self._rank_and_limit_articles(
                source_filtered,
                state["top_n"],
                state["session_id"],
                state["workflow_id"]
            )
            
            # Convert to NewsArticle format
            filtered_articles = self._convert_to_news_articles(
                final_articles,
                state["session_id"],
                state["workflow_id"]
            )
            
            # Update state with filtered articles
            new_state["filtered_articles"] = filtered_articles
            
            self.logger.log_processing_step(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="filtering_complete",
                message=f"Filtered {len(raw_articles)} articles down to {len(filtered_articles)}",
                extra_data={
                    "original_count": len(raw_articles),
                    "filtered_count": len(filtered_articles),
                    "topic_config": topic_config["topicName"] if topic_config else None
                }
            )
            
            # Mark filtering as completed
            completed_state = mark_step_completed(
                new_state,
                "filter_articles",
                f"Filtered and ranked {len(filtered_articles)} relevant articles"
            )
            
            # Log successful completion
            duration = time.time() - start_time
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="filter_articles",
                success=True,
                duration=duration,
                extra_data={"filtered_articles_count": len(filtered_articles)}
            )
            
            return completed_state
            
        except (ContentFilteringError, TopicConfigError):
            # Re-raise filtering errors as-is
            duration = time.time() - start_time
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="filter_articles",
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
                step="filter_articles"
            )
            
            # Log the error
            self.logger.log_error(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="filter_articles",
                error=custom_error
            )
            
            # Log node exit with failure
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="filter_articles",
                success=False,
                duration=duration
            )
            
            raise custom_error
    
    async def _load_topic_config(
        self,
        topic: str,
        session_id: str,
        workflow_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load topic configuration from database or use defaults.
        
        Args:
            topic: Topic name to load configuration for
            session_id: Session identifier for logging
            workflow_id: Workflow identifier for logging
            
        Returns:
            Topic configuration dictionary or None
        """
        try:
            async with AsyncSessionLocal() as db_session:
                # Try to find exact match first
                result = await db_session.execute(
                    select(TopicConfig).where(TopicConfig.topic_name == topic.lower())
                )
                topic_config = result.scalar_one_or_none()
                
                if topic_config:
                    return {
                        "topicName": topic_config.topic_name,
                        "keywords": topic_config.keywords,
                        "trustedSources": topic_config.trusted_sources,
                        "priorityWeight": topic_config.priority_weight
                    }
                
                # Try partial matches for common topics
                common_topics = ["ai", "finance", "healthcare", "technology", "business"]
                for common_topic in common_topics:
                    if common_topic in topic.lower():
                        result = await db_session.execute(
                            select(TopicConfig).where(TopicConfig.topic_name == common_topic)
                        )
                        topic_config = result.scalar_one_or_none()
                        
                        if topic_config:
                            self.logger.log_processing_step(
                                session_id=session_id,
                                workflow_id=workflow_id,
                                step="topic_config_fallback",
                                message=f"Using {common_topic} config for topic '{topic}'"
                            )
                            
                            return {
                                "topicName": topic_config.topic_name,
                                "keywords": topic_config.keywords,
                                "trustedSources": topic_config.trusted_sources,
                                "priorityWeight": topic_config.priority_weight
                            }
                
                # No configuration found, use generic approach
                self.logger.log_processing_step(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    step="no_topic_config",
                    message=f"No specific configuration found for topic '{topic}', using generic filtering"
                )
                
                return None
                
        except Exception as e:
            raise DatabaseError("topic_config_load", str(e))
    
    def _filter_by_quality(
        self,
        articles: List[Dict[str, Any]],
        session_id: str,
        workflow_id: str
    ) -> List[Dict[str, Any]]:
        """
        Filter articles by basic quality criteria.
        
        Args:
            articles: List of raw articles
            session_id: Session identifier for logging
            workflow_id: Workflow identifier for logging
            
        Returns:
            List of quality-filtered articles
        """
        filtered = []
        
        for article in articles:
            # Check required fields
            if not article.get("title") or not article.get("url"):
                continue
            
            # Check minimum content length
            title = article.get("title", "")
            snippet = article.get("snippet", "")
            
            if len(title) < self.min_title_length:
                continue
            
            if len(snippet) < self.min_snippet_length:
                continue
            
            # Check for valid URL
            try:
                parsed_url = urlparse(article["url"])
                if not parsed_url.netloc:
                    continue
            except:
                continue
            
            filtered.append(article)
        
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="quality_filtering",
            message=f"Quality filter: {len(articles)} -> {len(filtered)} articles",
            extra_data={
                "original_count": len(articles),
                "filtered_count": len(filtered)
            }
        )
        
        return filtered
    
    def _remove_duplicates(
        self,
        articles: List[Dict[str, Any]],
        session_id: str,
        workflow_id: str
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate articles based on URL and title similarity.
        
        Args:
            articles: List of articles to deduplicate
            session_id: Session identifier for logging
            workflow_id: Workflow identifier for logging
            
        Returns:
            List of deduplicated articles
        """
        seen_urls = set()
        seen_titles = set()
        deduplicated = []
        
        for article in articles:
            url = article.get("url", "")
            title = article.get("title", "").lower().strip()
            
            # Check URL duplicates
            if url in seen_urls:
                continue
            
            # Check title similarity (simple approach)
            title_hash = hashlib.md5(title.encode()).hexdigest()
            if title_hash in seen_titles:
                continue
            
            seen_urls.add(url)
            seen_titles.add(title_hash)
            deduplicated.append(article)
        
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="deduplication",
            message=f"Deduplication: {len(articles)} -> {len(deduplicated)} articles",
            extra_data={
                "original_count": len(articles),
                "deduplicated_count": len(deduplicated)
            }
        )
        
        return deduplicated
    
    def _calculate_relevance_scores(
        self,
        articles: List[Dict[str, Any]],
        topic_config: Optional[Dict[str, Any]],
        session_id: str,
        workflow_id: str
    ) -> List[Dict[str, Any]]:
        """
        Calculate relevance scores for articles based on topic keywords.
        
        Args:
            articles: List of articles to score
            topic_config: Topic configuration with keywords
            session_id: Session identifier for logging
            workflow_id: Workflow identifier for logging
            
        Returns:
            List of articles with relevance scores
        """
        if not topic_config:
            # Without topic config, assign equal scores
            for article in articles:
                article["relevance_score"] = 0.5
            return articles
        
        keywords = topic_config.get("keywords", [])
        if not keywords:
            for article in articles:
                article["relevance_score"] = 0.5
            return articles
        
        # Calculate scores based on keyword matches
        for article in articles:
            title = article.get("title", "").lower()
            snippet = article.get("snippet", "").lower()
            source = article.get("source", "").lower()
            
            score = 0.0
            total_keywords = len(keywords)
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                
                # Title matches are weighted more heavily
                if keyword_lower in title:
                    score += 0.4
                
                # Snippet matches
                if keyword_lower in snippet:
                    score += 0.2
                
                # Source matches
                if keyword_lower in source:
                    score += 0.1
            
            # Normalize score
            article["relevance_score"] = min(score / total_keywords, 1.0)
        
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="relevance_scoring",
            message=f"Calculated relevance scores for {len(articles)} articles",
            extra_data={
                "keywords_used": len(keywords),
                "articles_scored": len(articles)
            }
        )
        
        return articles
    
    def _filter_by_source_priority(
        self,
        articles: List[Dict[str, Any]],
        topic_config: Optional[Dict[str, Any]],
        session_id: str,
        workflow_id: str
    ) -> List[Dict[str, Any]]:
        """
        Apply source priority filtering and boost trusted sources.
        
        Args:
            articles: List of articles with relevance scores
            topic_config: Topic configuration with trusted sources
            session_id: Session identifier for logging
            workflow_id: Workflow identifier for logging
            
        Returns:
            List of articles with source priority applied
        """
        if not topic_config:
            return articles
        
        trusted_sources = topic_config.get("trustedSources", [])
        priority_weight = topic_config.get("priorityWeight", 1.0)
        
        if not trusted_sources:
            return articles
        
        # Boost scores for trusted sources
        boosted_count = 0
        for article in articles:
            article_url = article.get("url", "")
            
            try:
                domain = urlparse(article_url).netloc.lower()
                domain = domain.replace("www.", "")
                
                # Check if domain is in trusted sources
                for trusted_source in trusted_sources:
                    if trusted_source.lower() in domain:
                        original_score = article.get("relevance_score", 0.0)
                        boosted_score = min(original_score * priority_weight, 1.0)
                        article["relevance_score"] = boosted_score
                        article["trusted_source"] = True
                        boosted_count += 1
                        break
                else:
                    article["trusted_source"] = False
                    
            except:
                article["trusted_source"] = False
                continue
        
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="source_priority",
            message=f"Applied source priority boost to {boosted_count} articles",
            extra_data={
                "trusted_sources_count": len(trusted_sources),
                "boosted_articles": boosted_count
            }
        )
        
        return articles
    
    def _rank_and_limit_articles(
        self,
        articles: List[Dict[str, Any]],
        limit: int,
        session_id: str,
        workflow_id: str
    ) -> List[Dict[str, Any]]:
        """
        Rank articles by relevance score and limit to requested number.
        
        Args:
            articles: List of scored articles
            limit: Maximum number of articles to return
            session_id: Session identifier for logging
            workflow_id: Workflow identifier for logging
            
        Returns:
            List of top-ranked articles
        """
        # Sort by relevance score (descending) and trusted source status
        sorted_articles = sorted(
            articles,
            key=lambda x: (
                x.get("relevance_score", 0.0),
                x.get("trusted_source", False),
                -x.get("position", 999)  # Prefer earlier positions from search
            ),
            reverse=True
        )
        
        # Limit to requested number
        limited_articles = sorted_articles[:limit]
        
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="ranking_and_limiting",
            message=f"Ranked and limited to top {len(limited_articles)} articles",
            extra_data={
                "total_articles": len(articles),
                "returned_articles": len(limited_articles),
                "limit": limit
            }
        )
        
        return limited_articles
    
    def _convert_to_news_articles(
        self,
        articles: List[Dict[str, Any]],
        session_id: str,
        workflow_id: str
    ) -> List[NewsArticle]:
        """
        Convert filtered articles to NewsArticle format.
        
        Args:
            articles: List of filtered and scored articles
            session_id: Session identifier for logging
            workflow_id: Workflow identifier for logging
            
        Returns:
            List of NewsArticle objects
        """
        news_articles = []
        
        for article in articles:
            try:
                # Generate content hash
                content_for_hash = f"{article.get('title', '')}{article.get('url', '')}"
                content_hash = hashlib.md5(content_for_hash.encode()).hexdigest()
                
                # Extract domain for source
                try:
                    domain = urlparse(article.get("url", "")).netloc
                    source = domain.replace("www.", "") if domain else article.get("source", "")
                except:
                    source = article.get("source", "")
                
                news_article = NewsArticle(
                    title=article.get("title", ""),
                    url=article.get("url", ""),
                    source=source,
                    summary=article.get("snippet", ""),
                    published_at=article.get("date"),
                    relevance_score=article.get("relevance_score", 0.0),
                    content_hash=content_hash
                )
                
                news_articles.append(news_article)
                
            except Exception as e:
                self.logger.logger.warning(
                    f"Failed to convert article to NewsArticle format: {str(e)}",
                    extra={"article": article}
                )
                continue
        
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="format_conversion",
            message=f"Converted {len(news_articles)} articles to NewsArticle format"
        )
        
        return news_articles
