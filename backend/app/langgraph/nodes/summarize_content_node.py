"""
Content summarization node for news processing workflow.

This node follows LangGraph best practices:
- Single responsibility: Generate AI summaries for articles
- Multi-LLM provider support with fallback mechanisms
- Retry logic with exponential backoff
- Comprehensive logging and error handling
- Immutable state updates
"""
import time
import asyncio
from typing import List, Dict, Any, Optional
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from app.langgraph.state.news_state import NewsState, NewsArticle, mark_step_completed, mark_step_error
from app.langgraph.utils.logging_config import StructuredLogger
from app.langgraph.utils.error_handlers import (
    LLMProviderError,
    RetryableError,
    handle_node_error
)
from app.core.config import settings


class SummarizeContentNode:
    """
    Generates AI-powered summaries for filtered articles.
    
    Responsibilities:
    - Initialize LLM providers (Claude, OpenAI, Gemini)
    - Generate concise summaries for each article
    - Implement fallback mechanisms between providers
    - Handle rate limiting and API errors
    - Update articles with generated summaries
    
    This node implements robust LLM integration with
    proper error handling and provider fallbacks.
    """
    
    def __init__(self):
        """Initialize content summarization node with structured logger."""
        self.logger = StructuredLogger("summarize_content")
        self.node_name = "summarize_content"
        self.max_retries = 2
        self.retry_delay = 2.0
        self.summary_max_length = 200
        
        # LLM provider order for fallbacks
        self.provider_order = ["claude-3-5-sonnet", "gpt-4-turbo", "gemini-pro"]
    
    async def __call__(self, state: NewsState) -> NewsState:
        """
        Execute content summarization with LLM providers.
        
        Args:
            state: Current workflow state with filtered articles
            
        Returns:
            Updated state with summarized articles
            
        Raises:
            LLMProviderError: When all LLM providers fail
        """
        start_time = time.time()
        
        # Log node entry
        self.logger.log_node_entry(
            session_id=state["session_id"],
            workflow_id=state["workflow_id"],
            step="summarize_content",
            extra_data={
                "llm_model": state["llm_model"],
                "articles_count": len(state["filtered_articles"] or [])
            }
        )
        
        try:
            # Update state to show current processing step
            new_state = state.copy()
            new_state["current_step"] = "Generating AI summaries for articles"
            
            # Check if we have articles to summarize
            filtered_articles = state.get("filtered_articles", [])
            if not filtered_articles:
                self.logger.log_processing_step(
                    session_id=state["session_id"],
                    workflow_id=state["workflow_id"],
                    step="no_articles",
                    message="No articles to summarize"
                )
                
                new_state["summarized_articles"] = []
                return mark_step_completed(
                    new_state,
                    "summarize_content",
                    "No articles to summarize"
                )
            
            # Determine LLM provider order starting with user's preference
            provider_order = self._get_provider_order(state["llm_model"])
            
            # Track which providers we've tried
            providers_tried = []
            
            # Attempt summarization with provider fallbacks
            summarized_articles = await self._summarize_with_fallback(
                articles=filtered_articles,
                provider_order=provider_order,
                providers_tried=providers_tried,
                session_id=state["session_id"],
                workflow_id=state["workflow_id"]
            )
            
            # Update state with summarized articles and provider tracking
            new_state["summarized_articles"] = summarized_articles
            new_state["llm_providers_tried"] = providers_tried
            new_state["current_llm_provider"] = providers_tried[-1] if providers_tried else state["llm_model"]
            
            self.logger.log_processing_step(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="summarization_complete",
                message=f"Generated summaries for {len(summarized_articles)} articles",
                extra_data={
                    "articles_summarized": len(summarized_articles),
                    "providers_tried": providers_tried,
                    "final_provider": providers_tried[-1] if providers_tried else None
                }
            )
            
            # Mark summarization as completed
            completed_state = mark_step_completed(
                new_state,
                "summarize_content",
                f"Generated AI summaries for {len(summarized_articles)} articles"
            )
            
            # Log successful completion
            duration = time.time() - start_time
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="summarize_content",
                success=True,
                duration=duration,
                extra_data={
                    "summarized_articles_count": len(summarized_articles),
                    "providers_used": providers_tried
                }
            )
            
            return completed_state
            
        except LLMProviderError:
            # Re-raise LLM errors as-is
            duration = time.time() - start_time
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="summarize_content",
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
                step="summarize_content"
            )
            
            # Log the error
            self.logger.log_error(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="summarize_content",
                error=custom_error
            )
            
            # Log node exit with failure
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="summarize_content",
                success=False,
                duration=duration
            )
            
            raise custom_error
    
    def _get_provider_order(self, preferred_model: str) -> List[str]:
        """
        Get LLM provider order starting with user's preference.
        
        Args:
            preferred_model: User's preferred LLM model
            
        Returns:
            List of provider names in order of preference
        """
        # Start with user's preferred model
        order = [preferred_model]
        
        # Add other providers as fallbacks
        for provider in self.provider_order:
            if provider != preferred_model:
                order.append(provider)
        
        return order
    
    async def _summarize_with_fallback(
        self,
        articles: List[NewsArticle],
        provider_order: List[str],
        providers_tried: List[str],
        session_id: str,
        workflow_id: str
    ) -> List[NewsArticle]:
        """
        Attempt summarization with provider fallbacks.
        
        Args:
            articles: List of articles to summarize
            provider_order: Order of providers to try
            providers_tried: List to track which providers were attempted
            session_id: Session identifier for logging
            workflow_id: Workflow identifier for logging
            
        Returns:
            List of articles with generated summaries
            
        Raises:
            LLMProviderError: When all providers fail
        """
        last_error = None
        
        for provider in provider_order:
            try:
                providers_tried.append(provider)
                
                self.logger.log_processing_step(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    step="trying_provider",
                    message=f"Attempting summarization with {provider}",
                    extra_data={"provider": provider}
                )
                
                # Initialize LLM client
                llm_client = self._initialize_llm_client(provider)
                
                # Generate summaries for all articles
                summarized_articles = await self._generate_summaries(
                    articles=articles,
                    llm_client=llm_client,
                    provider=provider,
                    session_id=session_id,
                    workflow_id=workflow_id
                )
                
                self.logger.log_processing_step(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    step="provider_success",
                    message=f"Successfully used {provider} for summarization",
                    extra_data={"provider": provider, "articles_count": len(summarized_articles)}
                )
                
                return summarized_articles
                
            except Exception as e:
                last_error = e
                
                self.logger.log_processing_step(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    step="provider_failed",
                    message=f"Provider {provider} failed: {str(e)}",
                    extra_data={"provider": provider, "error": str(e)}
                )
                
                # Continue to next provider
                continue
        
        # All providers failed
        error_message = f"All LLM providers failed. Last error: {str(last_error)}"
        self.logger.log_error(
            session_id=session_id,
            workflow_id=workflow_id,
            step="all_providers_failed",
            error=LLMProviderError("all_providers", error_message)
        )
        
        raise LLMProviderError("all_providers", error_message)
    
    def _initialize_llm_client(self, provider: str):
        """
        Initialize LLM client for the specified provider.
        
        Args:
            provider: LLM provider name
            
        Returns:
            Initialized LLM client
            
        Raises:
            LLMProviderError: When provider initialization fails
        """
        try:
            if provider == "claude-3-5-sonnet":
                if not settings.ANTHROPIC_API_KEY:
                    raise LLMProviderError(provider, "Anthropic API key not configured")
                
                return ChatAnthropic(
                    model="claude-3-5-sonnet-20241022",
                    api_key=settings.ANTHROPIC_API_KEY,
                    max_tokens=settings.LLM_MAX_TOKENS,
                    temperature=settings.LLM_TEMPERATURE
                )
            
            elif provider == "gpt-4-turbo":
                if not settings.OPENAI_API_KEY:
                    raise LLMProviderError(provider, "OpenAI API key not configured")
                
                return ChatOpenAI(
                    model="gpt-4-turbo-preview",
                    api_key=settings.OPENAI_API_KEY,
                    max_tokens=settings.LLM_MAX_TOKENS,
                    temperature=settings.LLM_TEMPERATURE
                )
            
            elif provider == "gemini-pro":
                if not settings.GOOGLE_API_KEY:
                    raise LLMProviderError(provider, "Google API key not configured")
                
                return ChatGoogleGenerativeAI(
                    model="gemini-pro",
                    google_api_key=settings.GOOGLE_API_KEY,
                    max_output_tokens=settings.LLM_MAX_TOKENS,
                    temperature=settings.LLM_TEMPERATURE
                )
            
            else:
                raise LLMProviderError(provider, f"Unknown provider: {provider}")
                
        except Exception as e:
            raise LLMProviderError(provider, f"Failed to initialize: {str(e)}")
    
    async def _generate_summaries(
        self,
        articles: List[NewsArticle],
        llm_client,
        provider: str,
        session_id: str,
        workflow_id: str
    ) -> List[NewsArticle]:
        """
        Generate summaries for all articles using the LLM client.
        
        Args:
            articles: List of articles to summarize
            llm_client: Initialized LLM client
            provider: Provider name for logging
            session_id: Session identifier for logging
            workflow_id: Workflow identifier for logging
            
        Returns:
            List of articles with generated summaries
            
        Raises:
            LLMProviderError: When summarization fails
        """
        summarized_articles = []
        
        for i, article in enumerate(articles):
            try:
                # Generate summary for individual article
                summary = await self._generate_single_summary(
                    article=article,
                    llm_client=llm_client,
                    provider=provider,
                    session_id=session_id,
                    workflow_id=workflow_id
                )
                
                # Create new article with generated summary
                summarized_article = article.copy()
                summarized_article["summary"] = summary
                summarized_articles.append(summarized_article)
                
                # Log progress
                if (i + 1) % 3 == 0 or (i + 1) == len(articles):
                    self.logger.log_processing_step(
                        session_id=session_id,
                        workflow_id=workflow_id,
                        step="summary_progress",
                        message=f"Generated {i + 1}/{len(articles)} summaries",
                        extra_data={"progress": f"{i + 1}/{len(articles)}"}
                    )
                
            except Exception as e:
                # Log individual article failure but continue
                self.logger.log_processing_step(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    step="article_summary_failed",
                    message=f"Failed to summarize article {i + 1}: {str(e)}",
                    extra_data={"article_index": i + 1, "error": str(e)}
                )
                
                # Use original snippet as fallback
                fallback_article = article.copy()
                fallback_article["summary"] = article.get("summary", "")[:self.summary_max_length]
                summarized_articles.append(fallback_article)
        
        if not summarized_articles:
            raise LLMProviderError(provider, "Failed to summarize any articles")
        
        return summarized_articles
    
    async def _generate_single_summary(
        self,
        article: NewsArticle,
        llm_client,
        provider: str,
        session_id: str,
        workflow_id: str
    ) -> str:
        """
        Generate summary for a single article with retry logic.
        
        Args:
            article: Article to summarize
            llm_client: Initialized LLM client
            provider: Provider name for logging
            session_id: Session identifier for logging
            workflow_id: Workflow identifier for logging
            
        Returns:
            Generated summary text
            
        Raises:
            LLMProviderError: When summary generation fails
        """
        # Construct prompt for summarization
        prompt = self._build_summarization_prompt(article)
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Make LLM API call
                api_start_time = time.time()
                
                message = HumanMessage(content=prompt)
                response = await llm_client.ainvoke([message])
                
                api_duration = time.time() - api_start_time
                
                # Log API call
                self.logger.log_api_call(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    api_name=provider,
                    method="POST",
                    url="llm_api",
                    duration=api_duration,
                    extra_data={"article_title": article["title"][:50]}
                )
                
                # Extract and validate summary
                summary = response.content.strip()
                
                if not summary:
                    raise LLMProviderError(provider, "Empty summary returned")
                
                # Truncate if too long
                if len(summary) > self.summary_max_length:
                    summary = summary[:self.summary_max_length - 3] + "..."
                
                return summary
                
            except Exception as e:
                last_error = e
                
                if attempt < self.max_retries:
                    # Calculate delay with exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    
                    self.logger.log_processing_step(
                        session_id=session_id,
                        workflow_id=workflow_id,
                        step="summary_retry",
                        message=f"Summary generation failed (attempt {attempt + 1}/{self.max_retries + 1}), retrying in {delay}s",
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
                    break
        
        # All retries failed
        raise LLMProviderError(provider, f"Summary generation failed after {self.max_retries} retries: {str(last_error)}")
    
    def _build_summarization_prompt(self, article: NewsArticle) -> str:
        """
        Build prompt for article summarization.
        
        Args:
            article: Article to summarize
            
        Returns:
            Formatted prompt string
        """
        title = article.get("title", "")
        original_summary = article.get("summary", "")
        source = article.get("source", "")
        
        prompt = f"""Please create a concise, professional summary of this news article for LinkedIn sharing.

Title: {title}
Source: {source}
Original Content: {original_summary}

Requirements:
- Maximum {self.summary_max_length} characters
- Professional tone suitable for LinkedIn
- Focus on key insights and implications
- Include relevant context for business professionals
- Avoid promotional language

Summary:"""
        
        return prompt
