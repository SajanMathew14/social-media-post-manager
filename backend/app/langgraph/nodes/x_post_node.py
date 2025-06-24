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
from app.langgraph.utils.state_helpers import get_post_workflow_fields, StateAccessError, StateAccessHelper
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
    
    def _handle_url_gracefully(self, content: str, articles: List[Dict[str, Any]]) -> str:
        """
        Handle URL embedding gracefully with fallback strategies.
        
        Args:
            content: Generated post content
            articles: List of articles with URLs
            
        Returns:
            Content with URLs handled gracefully
        """
        if not articles:
            return content
        
        # Try to find the most important article (first one or highest relevance)
        primary_article = articles[0]
        primary_url = primary_article.get("url", "")
        
        if not primary_url:
            return content
        
        # Contextual phrases for embedding URLs
        embed_phrases = [
            ("Details", "Details"),
            ("Full story", "story"),
            ("Read more", "more"),
            ("Source", "Source"),
            ("Analysis", "Analysis"),
            ("Report", "Report"),
            ("Data", "Data"),
            ("Study", "Study")
        ]
        
        # Try to embed URL in existing contextual words
        for full_phrase, embed_word in embed_phrases:
            if embed_word.lower() in content.lower():
                # Replace the word with a markdown-style link
                import re
                pattern = re.compile(re.escape(embed_word), re.IGNORECASE)
                content = pattern.sub(f"[{embed_word}]({primary_url})", content, count=1)
                return content
        
        # If no contextual word found, try to add a contextual phrase
        # Check if we have space to add " Details: URL"
        test_addition = f" Details: {primary_url}"
        if len(content) + len(test_addition) <= self.MAX_CHAR_LIMIT:
            return content + test_addition
        
        # If no space for full URL, try shortened version or just add URL at end
        if len(content) + len(primary_url) + 1 <= self.MAX_CHAR_LIMIT:
            return content + f" {primary_url}"
        
        # Last resort: truncate content to fit URL
        available_space = self.MAX_CHAR_LIMIT - len(primary_url) - 4  # 4 for " ..."
        if available_space > 50:  # Only if we have reasonable space left
            return content[:available_space] + f"... {primary_url}"
        
        # If all else fails, return original content without URL
        return content
    
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
        
        # Use ALL articles, not just top 3
        # Format articles for prompt
        articles_text = "\n\n".join([
            f"Article {i+1}:\n{format_article_for_prompt(article)}"
            for i, article in enumerate(articles)
        ])
        
        prompt = f"""Create a compelling Twitter/X post summarizing ALL {article_count} key {topic} news items in exactly 250 characters.

CRITICAL REQUIREMENTS:
- You MUST reference insights from ALL {article_count} articles
- EXACTLY 250 characters (including spaces, punctuation, hashtags)
- Include at least one embedded link using contextual words

ALL {article_count} ARTICLES TO SUMMARIZE:
{articles_text}

EXACT FORMAT STRATEGY:
🚨 {topic} Update: [Key insight combining multiple articles]

Key developments:
• [Point from Article 1]
• [Point from Article 2] 
• [Point from Article 3+]

[Embedded link] #hashtags

EMBEDDING LINK STRATEGY:
- Try to embed ONE key article link in contextual phrases:
  * "Details here" → "Details"
  * "Full report" → "report" 
  * "Read analysis" → "analysis"
  * "Source data" → "data"
- If embedding fails, use original URL
- NEVER fail due to URL issues

REQUIREMENTS:
1. EXACTLY 250 characters total
2. Reference ALL {article_count} articles through key insights
3. Start with emoji hook
4. Use bullet points for multiple insights
5. Embed ONE link contextually
6. End with 1-2 hashtags
7. Make it viral and shareable

CRITICAL: Must cover insights from ALL {article_count} articles, not just a subset.

Generate the X post now (EXACTLY 250 characters):"""
        
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
            # Use robust state access helper to handle reducer issues
            try:
                required_fields = get_post_workflow_fields(state)
                session_id = required_fields["session_id"]
                workflow_id = required_fields["workflow_id"]
                llm_model = required_fields["llm_model"]
            except StateAccessError as e:
                # Log detailed state information for debugging
                debug_info = StateAccessHelper.create_debug_state_info(state)
                self.logger.log_error(
                    session_id="unknown",
                    workflow_id="unknown",
                    step="x_post_state_access_error",
                    error=str(e),
                    extra_data=debug_info
                )
                raise ValueError(str(e))
            
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
            if urls:
                for url in urls[:1]:  # Only shorten first URL
                    if settings.TINYURL_API_KEY:
                        shortened = await self._shorten_url(url)
                        if shortened:
                            shortened_urls[url] = shortened
                            generated_content = generated_content.replace(url, shortened)
            
            # If no URLs were embedded by LLM, try to add them gracefully
            if not urls:
                articles = state.get("articles", [])
                generated_content = self._handle_url_gracefully(generated_content, articles)
            
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
