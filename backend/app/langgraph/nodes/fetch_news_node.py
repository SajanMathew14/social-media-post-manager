"""
News fetching node for news processing workflow.

This node follows LangGraph best practices:
- Single responsibility: Fetch news from Serper API
- Retry mechanisms with exponential backoff
- Comprehensive logging and error handling
- Immutable state updates
"""
import time
import asyncio
from typing import List, Dict, Any, Optional
import httpx
from datetime import datetime

from app.langgraph.state.news_state import NewsState, mark_step_completed, mark_step_error
from app.langgraph.utils.logging_config import StructuredLogger
from app.langgraph.utils.error_handlers import (
    SerperAPIError,
    RetryableError,
    handle_node_error
)
from app.core.config import settings


class FetchNewsNode:
    """
    Fetches news articles from Serper API based on topic and date.
    
    Responsibilities:
    - Construct search queries with topic and date filters
    - Call Serper API with retry logic
    - Parse and normalize API responses
    - Handle rate limiting and API errors
    - Update state with raw articles
    
    This node implements robust API integration with
    proper error handling and retry mechanisms.
    """
    
    def __init__(self):
        """Initialize news fetching node with structured logger."""
        self.logger = StructuredLogger("fetch_news")
        self.node_name = "fetch_news"
        self.base_url = "https://google.serper.dev/news"
        self.timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 1.0
    
    async def __call__(self, state: NewsState) -> NewsState:
        """
        Execute news fetching from Serper API.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with raw articles
            
        Raises:
            SerperAPIError: When API calls fail after retries
        """
        start_time = time.time()
        
        # Log node entry
        self.logger.log_node_entry(
            session_id=state["session_id"],
            workflow_id=state["workflow_id"],
            step="fetch_news",
            extra_data={
                "topic": state["topic"],
                "date": state["date"],
                "top_n": state["top_n"]
            }
        )
        
        try:
            # Update state to show current processing step
            new_state = state.copy()
            new_state["current_step"] = "Fetching news from Serper API"
            
            # Construct search query
            search_query = self._build_search_query(state["topic"], state["date"])
            
            self.logger.log_processing_step(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="query_construction",
                message=f"Built search query: {search_query}"
            )
            
            # Fetch articles with retry mechanism
            raw_articles = await self._fetch_with_retry(
                query=search_query,
                num_results=state["top_n"],
                session_id=state["session_id"],
                workflow_id=state["workflow_id"]
            )
            
            # Update state with fetched articles
            new_state["raw_articles"] = raw_articles
            new_state["total_found"] = len(raw_articles)
            
            self.logger.log_processing_step(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="articles_fetched",
                message=f"Successfully fetched {len(raw_articles)} articles",
                extra_data={"articles_count": len(raw_articles)}
            )
            
            # Mark fetch as completed
            completed_state = mark_step_completed(
                new_state,
                "fetch_news",
                f"Fetched {len(raw_articles)} articles from Serper API"
            )
            
            # Log successful completion
            duration = time.time() - start_time
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="fetch_news",
                success=True,
                duration=duration,
                extra_data={"articles_fetched": len(raw_articles)}
            )
            
            return completed_state
            
        except SerperAPIError:
            # Re-raise API errors as-is
            duration = time.time() - start_time
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="fetch_news",
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
                step="fetch_news"
            )
            
            # Log the error
            self.logger.log_error(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="fetch_news",
                error=custom_error
            )
            
            # Log node exit with failure
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="fetch_news",
                success=False,
                duration=duration
            )
            
            raise custom_error
    
    def _build_search_query(self, topic: str, date: str) -> str:
        """
        Build search query for Serper API.
        
        Args:
            topic: News topic to search for
            date: Date in YYYY-MM-DD format
            
        Returns:
            Formatted search query string
        """
        # Clean and format topic
        clean_topic = topic.strip()
        
        # Add date filter to query
        # Serper supports date filtering with after: parameter
        query = f"{clean_topic} after:{date}"
        
        return query
    
    async def _fetch_with_retry(
        self,
        query: str,
        num_results: int,
        session_id: str,
        workflow_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch news with retry logic and exponential backoff.
        
        Args:
            query: Search query string
            num_results: Number of results to fetch
            session_id: Session identifier for logging
            workflow_id: Workflow identifier for logging
            
        Returns:
            List of raw article dictionaries
            
        Raises:
            SerperAPIError: When all retry attempts fail
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await self._make_api_call(
                    query=query,
                    num_results=num_results,
                    session_id=session_id,
                    workflow_id=workflow_id
                )
                
            except Exception as e:
                last_error = e
                
                if attempt < self.max_retries:
                    # Calculate delay with exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    
                    self.logger.log_processing_step(
                        session_id=session_id,
                        workflow_id=workflow_id,
                        step="retry_attempt",
                        message=f"API call failed (attempt {attempt + 1}/{self.max_retries + 1}), retrying in {delay}s",
                        extra_data={
                            "attempt": attempt + 1,
                            "max_attempts": self.max_retries + 1,
                            "delay": delay,
                            "error": str(e)
                        }
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    # All retries exhausted
                    self.logger.log_error(
                        session_id=session_id,
                        workflow_id=workflow_id,
                        step="api_retry_exhausted",
                        error=SerperAPIError(f"All retry attempts failed: {str(e)}")
                    )
        
        # Raise the last error if all retries failed
        if isinstance(last_error, SerperAPIError):
            raise last_error
        else:
            raise SerperAPIError(f"API call failed after {self.max_retries} retries: {str(last_error)}")
    
    async def _make_api_call(
        self,
        query: str,
        num_results: int,
        session_id: str,
        workflow_id: str
    ) -> List[Dict[str, Any]]:
        """
        Make actual API call to Serper.
        
        Args:
            query: Search query string
            num_results: Number of results to fetch
            session_id: Session identifier for logging
            workflow_id: Workflow identifier for logging
            
        Returns:
            List of raw article dictionaries
            
        Raises:
            SerperAPIError: When API call fails
        """
        if not settings.SERPER_API_KEY:
            raise SerperAPIError("Serper API key not configured")
        
        # Prepare request payload
        payload = {
            "q": query,
            "num": min(num_results, 20),  # Serper max is typically 20
            "hl": "en",
            "gl": "us"
        }
        
        headers = {
            "X-API-KEY": settings.SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        
        api_start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Log API call
                self.logger.log_api_call(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    api_name="Serper",
                    method="POST",
                    url=self.base_url,
                    extra_data={"query": query, "num_results": num_results}
                )
                
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers
                )
                
                api_duration = time.time() - api_start_time
                
                # Log API response
                self.logger.log_api_call(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    api_name="Serper",
                    method="POST",
                    url=self.base_url,
                    status_code=response.status_code,
                    duration=api_duration
                )
                
                # Check response status
                if response.status_code != 200:
                    error_body = response.text
                    raise SerperAPIError(
                        f"API returned status {response.status_code}",
                        status_code=response.status_code,
                        response_body=error_body
                    )
                
                # Parse response
                response_data = response.json()
                
                # Extract articles from response
                articles = self._parse_serper_response(response_data)
                
                return articles
                
        except httpx.TimeoutException:
            raise SerperAPIError(f"API call timed out after {self.timeout}s")
        except httpx.RequestError as e:
            raise SerperAPIError(f"Request error: {str(e)}")
        except Exception as e:
            raise SerperAPIError(f"Unexpected error during API call: {str(e)}")
    
    def _parse_serper_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse Serper API response and extract articles.
        
        Args:
            response_data: Raw API response data
            
        Returns:
            List of normalized article dictionaries
        """
        articles = []
        
        # Serper returns news in 'news' field
        news_items = response_data.get("news", [])
        
        for item in news_items:
            try:
                article = {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "source": item.get("source", ""),
                    "snippet": item.get("snippet", ""),
                    "date": item.get("date", ""),
                    "imageUrl": item.get("imageUrl", ""),
                    "position": item.get("position", 0)
                }
                
                # Only add articles with required fields
                if article["title"] and article["url"]:
                    articles.append(article)
                    
            except Exception as e:
                # Log parsing error but continue with other articles
                self.logger.logger.warning(
                    f"Failed to parse article: {str(e)}",
                    extra={"raw_item": item}
                )
                continue
        
        return articles
