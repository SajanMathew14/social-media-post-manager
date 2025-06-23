"""
X (Twitter) post generation node for LangGraph workflow.

This node generates concise X posts from news articles,
including hashtags and shortened URLs.
"""
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.langgraph.state.post_state import (
    PostState,
    GeneratedPostContent,
    PostGenerationStatus,
    mark_post_step_completed,
    mark_post_step_error,
    format_article_for_prompt
)
from datetime import datetime
from app.langgraph.utils.logging_config import StructuredLogger
from app.langgraph.utils.error_handlers import LLMProviderError
from app.core.config import settings


class XPostNode:
    """
    Node for generating X (Twitter) posts from news articles.
    
    This node:
    1. Generates concise 250-character posts
    2. Includes relevant hashtags
    3. Shortens URLs using TinyURL API
    4. Supports multiple LLM providers
    """
    
    MAX_CHAR_LIMIT = 250
    TINYURL_API_URL = "https://api.tinyurl.com/create"
    
    def __init__(self):
        """Initialize X post node with logger."""
        self.logger = StructuredLogger("x_post_node")
        self.llm_providers = self._initialize_llm_providers()
    
    def _initialize_llm_providers(self) -> Dict[str, Any]:
        """Initialize available LLM providers."""
        providers = {}
        
        # Initialize Anthropic Claude (latest version)
        if settings.ANTHROPIC_API_KEY:
            providers["claude-3-5-sonnet"] = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                api_key=settings.ANTHROPIC_API_KEY,
                max_tokens=8192,
                temperature=0.7
            )
            # Add Claude 3.5 Haiku for faster responses
            providers["claude-3-5-haiku"] = ChatAnthropic(
                model="claude-3-5-haiku-20241022",
                api_key=settings.ANTHROPIC_API_KEY,
                max_tokens=8192,
                temperature=0.7
            )
        
        # Initialize OpenAI GPT
        if settings.OPENAI_API_KEY:
            providers["gpt-4-turbo"] = ChatOpenAI(
                model="gpt-4-turbo-preview",
                api_key=settings.OPENAI_API_KEY,
                max_tokens=1024,
                temperature=0.7
            )
        
        # Initialize Google Gemini
        if settings.GOOGLE_API_KEY:
            providers["gemini-pro"] = ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=settings.GOOGLE_API_KEY,
                max_output_tokens=1024,
                temperature=0.7
            )
        
        return providers
    
    async def _shorten_url(self, url: str) -> Optional[str]:
        """
        Shorten URL using TinyURL API.
        
        Args:
            url: Original URL to shorten
            
        Returns:
            Shortened URL or None if failed
        """
        if not settings.TINYURL_API_KEY:
            self.logger.log_processing_step(
                session_id="system",
                workflow_id="system",
                step="url_shortening_skipped",
                message="TinyURL API key not configured, using original URLs"
            )
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {settings.TINYURL_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "url": url,
                "domain": "tinyurl.com"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.TINYURL_API_URL,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("data", {}).get("tiny_url")
                    else:
                        self.logger.log_error(
                            session_id="system",
                            workflow_id="system",
                            step="url_shortening_failed",
                            error=f"TinyURL API returned status {response.status}",
                            extra_data={"url": url}
                        )
                        return None
                        
        except Exception as e:
            self.logger.log_error(
                session_id="system",
                workflow_id="system",
                step="url_shortening_error",
                error=e,
                extra_data={"url": url}
            )
            return None
    
    def _generate_hashtags(self, topic: str) -> List[str]:
        """
        Generate relevant hashtags based on topic.
        
        Args:
            topic: News topic
            
        Returns:
            List of 1-2 relevant hashtags
        """
        # Topic-specific hashtag mappings
        hashtag_map = {
            "AI": ["#AI", "#ArtificialIntelligence"],
            "Finance": ["#FinTech", "#Finance"],
            "Healthcare": ["#HealthTech", "#Healthcare"],
            "Technology": ["#Tech", "#Innovation"],
            "Business": ["#Business", "#Startups"],
            "Crypto": ["#Crypto", "#Blockchain"],
            "Climate": ["#ClimateChange", "#Sustainability"],
            "Education": ["#EdTech", "#Education"],
            "Security": ["#CyberSecurity", "#InfoSec"],
            "Data": ["#DataScience", "#BigData"]
        }
        
        # Find matching hashtags
        topic_lower = topic.lower()
        for key, hashtags in hashtag_map.items():
            if key.lower() in topic_lower:
                return hashtags[:2]  # Return max 2 hashtags
        
        # Default hashtags if no match
        return ["#Tech", "#News"]
    
    def _create_x_prompt(self, state: PostState) -> str:
        """
        Create the prompt for X post generation.
        
        Args:
            state: Current workflow state
            
        Returns:
            Formatted prompt for LLM
        """
        articles = state.get("articles", [])
        topic = state.get("topic", "Unknown Topic")
        article_count = len(articles)
        
        # Get most relevant articles (top 3 by relevance score if available)
        sorted_articles = sorted(
            articles,
            key=lambda x: x.get("relevance_score", 0),
            reverse=True
        )[:3]
        
        # Format articles for prompt
        articles_text = "\n\n".join([
            f"Article {i+1}:\n{format_article_for_prompt(article)}"
            for i, article in enumerate(sorted_articles)
        ])
        
        prompt = f"""Create a compelling Twitter/X post summarizing today's top {topic} news.

ARTICLES TO SUMMARIZE:
{articles_text}

REQUIREMENTS:
1. Maximum 250 characters INCLUDING spaces and punctuation
2. Focus on the most impactful or surprising insight
3. Create a hook that makes people want to learn more
4. Include 1-2 relevant hashtags at the end
5. Optionally include ONE shortened link to the most important article
6. Use clear, punchy language
7. Make it shareable and engaging

STYLE GUIDELINES:
- Start with a strong hook or surprising fact
- Use numbers/statistics if impactful
- Create urgency or highlight trends
- End with hashtags

Generate the X post now (remember: 250 characters MAX):"""
        
        return prompt
    
    async def __call__(self, state: PostState) -> PostState:
        """
        Generate X post from news articles.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with generated X post
        """
        try:
            # Validate critical state fields first
            session_id = state.get("session_id", "")
            workflow_id = state.get("workflow_id", "")
            llm_model = state.get("llm_model", "")
            
            # Validate required fields
            if not session_id:
                raise ValueError("session_id is missing from workflow state")
            if not workflow_id:
                raise ValueError("workflow_id is missing from workflow state")
            if not llm_model:
                raise ValueError("llm_model is missing from workflow state")
            
            # Log start of X post generation with comprehensive state info
            self.logger.log_processing_step(
                session_id=session_id,
                workflow_id=workflow_id,
                step="x_post_generation_start",
                message=f"Generating X post for {len(state.get('articles', []))} articles",
                extra_data={
                    "topic": state.get("topic", ""),
                    "article_count": len(state.get("articles", [])),
                    "llm_model": llm_model,
                    "session_id": session_id,
                    "workflow_id": workflow_id,
                    "state_keys": list(state.keys()),
                    "has_linkedin_post": state.get("linkedin_post") is not None
                }
            )
            
            # Check if any LLM providers are available
            if not self.llm_providers:
                raise LLMProviderError(
                    provider="none",
                    original_error="No LLM providers are configured. Please set at least one API key (ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY) in your environment variables."
                )
            
            # Get LLM provider with fallback logic
            llm = self.llm_providers.get(llm_model)
            if not llm:
                available_models = list(self.llm_providers.keys())
                # Try to use the first available provider as fallback
                if available_models:
                    fallback_model = available_models[0]
                    self.logger.log_processing_step(
                        session_id=session_id,
                        workflow_id=workflow_id,
                        step="llm_provider_fallback",
                        message=f"LLM provider {llm_model} not available, using fallback: {fallback_model}",
                        extra_data={
                            "requested_model": llm_model,
                            "fallback_model": fallback_model,
                            "available_models": available_models
                        }
                    )
                    llm = self.llm_providers[fallback_model]
                    llm_model = fallback_model  # Update the model name for state
                else:
                    raise LLMProviderError(
                        provider=llm_model,
                        original_error=f"LLM provider {llm_model} not available. Available providers: {', '.join(available_models)}"
                    )
            
            # Create prompt
            prompt = self._create_x_prompt(state)
            
            # Generate post
            messages = [
                SystemMessage(content="You are a social media expert specializing in creating viral, engaging Twitter/X posts about technology and business news."),
                HumanMessage(content=prompt)
            ]
            
            response = await llm.ainvoke(messages)
            generated_content = response.content.strip()
            
            # Extract URLs from content for shortening
            import re
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, generated_content)
            
            # Shorten URLs if found
            shortened_urls = {}
            if urls and settings.TINYURL_API_KEY:
                for url in urls[:1]:  # Only shorten first URL
                    shortened = await self._shorten_url(url)
                    if shortened:
                        shortened_urls[url] = shortened
                        generated_content = generated_content.replace(url, shortened)
            
            # Add hashtags if not present
            if '#' not in generated_content:
                hashtags = self._generate_hashtags(state.get("topic", "Tech"))
                hashtag_text = ' '.join(hashtags)
                
                # Check if adding hashtags would exceed limit
                if len(generated_content) + len(hashtag_text) + 1 <= self.MAX_CHAR_LIMIT:
                    generated_content += f" {hashtag_text}"
            
            # Validate character count
            char_count = len(generated_content)
            if char_count > self.MAX_CHAR_LIMIT:
                # Truncate intelligently (try to keep hashtags)
                hashtag_match = re.search(r'(\s#\w+)+$', generated_content)
                if hashtag_match:
                    hashtags = hashtag_match.group()
                    content_without_hashtags = generated_content[:hashtag_match.start()]
                    max_content_length = self.MAX_CHAR_LIMIT - len(hashtags) - 3  # -3 for "..."
                    generated_content = content_without_hashtags[:max_content_length] + "..." + hashtags
                else:
                    generated_content = generated_content[:self.MAX_CHAR_LIMIT - 3] + "..."
                char_count = len(generated_content)
            
            # Extract hashtags from final content
            hashtags = self._extract_hashtags(generated_content)
            
            # Create post content object
            x_post = GeneratedPostContent(
                content=generated_content,
                char_count=char_count,
                hashtags=hashtags,
                shortened_urls=shortened_urls if shortened_urls else None
            )
            
            # Log successful generation
            self.logger.log_processing_step(
                session_id=session_id or "unknown",
                workflow_id=workflow_id or "unknown",
                step="x_post_generation_complete",
                message=f"Successfully generated X post ({char_count} chars)",
                extra_data={
                    "char_count": char_count,
                    "hashtag_count": len(hashtags),
                    "urls_shortened": len(shortened_urls)
                }
            )
            
            # With LangGraph 0.4.8, we can return partial state updates
            # The Annotated reducers will handle preserving immutable fields
            return {
                "x_post": x_post,
                "current_step": "x_post_generation",
                "current_llm_provider": llm_model,
                "processing_steps": [
                    {
                        "step": "x_post_generation",
                        "status": PostGenerationStatus.COMPLETED,
                        "message": f"Generated X post with {char_count} characters",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
            
        except Exception as e:
            # Log error
            self.logger.log_error(
                session_id=state.get("session_id", "unknown"),
                workflow_id=state.get("workflow_id", "unknown"),
                step="x_post_generation_error",
                error=e,
                extra_data={
                    "topic": state.get("topic", ""),
                    "article_count": len(state.get("articles", []))
                }
            )
            
            # Create error state update maintaining all existing fields
            error_state = state.copy()
            error_state.update({
                "error_message": f"Failed to generate X post: {str(e)}",
                "failed_step": "x_post_generation",
                "current_step": "x_post_generation",
                "processing_steps": [
                    {
                        "step": "x_post_generation",
                        "status": PostGenerationStatus.ERROR,
                        "message": f"Failed to generate X post: {str(e)}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            })
            
            return error_state
    
    def _extract_hashtags(self, content: str) -> List[str]:
        """
        Extract hashtags from generated content.
        
        Args:
            content: Generated post content
            
        Returns:
            List of hashtags found in content
        """
        import re
        hashtag_pattern = r'#\w+'
        hashtags = re.findall(hashtag_pattern, content)
        return list(set(hashtags))  # Remove duplicates
