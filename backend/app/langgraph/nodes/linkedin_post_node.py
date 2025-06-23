"""
LinkedIn post generation node for LangGraph workflow.

This node generates professional LinkedIn posts from news articles,
dynamically adjusting content based on the number of articles.
"""
import asyncio
from typing import Dict, Any, List
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


class LinkedInPostNode:
    """
    Node for generating LinkedIn posts from news articles.
    
    This node:
    1. Dynamically adjusts content length based on article count
    2. Formats posts with headlines, summaries, and CTAs
    3. Enforces 3000 character limit
    4. Supports multiple LLM providers
    """
    
    MAX_CHAR_LIMIT = 3000
    
    def __init__(self):
        """Initialize LinkedIn post node with logger."""
        self.logger = StructuredLogger("linkedin_post_node")
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
                max_tokens=4096,
                temperature=0.7
            )
        
        # Initialize Google Gemini
        if settings.GOOGLE_API_KEY:
            providers["gemini-pro"] = ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=settings.GOOGLE_API_KEY,
                max_output_tokens=4096,
                temperature=0.7
            )
        
        return providers
    
    def _calculate_content_distribution(self, article_count: int) -> Dict[str, int]:
        """
        Calculate character distribution based on article count.
        
        Args:
            article_count: Number of articles to include
            
        Returns:
            Dictionary with character limits for different sections
        """
        # Reserve characters for structure and CTA
        structure_chars = 200  # Opening, transitions, CTA
        available_chars = self.MAX_CHAR_LIMIT - structure_chars
        
        # Calculate per-article allocation
        chars_per_article = available_chars // article_count
        
        # Adjust for readability
        if article_count <= 3:
            # Fewer articles = richer content
            headline_chars = 100
            summary_chars = chars_per_article - headline_chars - 50  # 50 for formatting
        elif article_count <= 6:
            # Medium count = balanced content
            headline_chars = 80
            summary_chars = chars_per_article - headline_chars - 40
        else:
            # Many articles = concise content
            headline_chars = 60
            summary_chars = chars_per_article - headline_chars - 30
        
        return {
            "headline_chars": headline_chars,
            "summary_chars": summary_chars,
            "chars_per_article": chars_per_article
        }
    
    def _create_linkedin_prompt(self, state: PostState) -> str:
        """
        Create the prompt for LinkedIn post generation.
        
        Args:
            state: Current workflow state
            
        Returns:
            Formatted prompt for LLM
        """
        articles = state["articles"]
        topic = state["topic"]
        article_count = len(articles)
        
        # Get content distribution
        distribution = self._calculate_content_distribution(article_count)
        
        # Format articles for prompt
        articles_text = "\n\n".join([
            f"Article {i+1}:\n{format_article_for_prompt(article)}"
            for i, article in enumerate(articles)
        ])
        
        prompt = f"""You are writing a professional LinkedIn post summarizing {article_count} key news items about {topic} for an audience of tech leaders, startup founders, and innovation-driven professionals.

CONTENT DISTRIBUTION:
- Total character limit: {self.MAX_CHAR_LIMIT} characters
- Per article allocation: ~{distribution['chars_per_article']} characters
- Headline per article: ~{distribution['headline_chars']} characters
- Summary per article: ~{distribution['summary_chars']} characters

ARTICLES TO SUMMARIZE:
{articles_text}

FORMATTING REQUIREMENTS:
1. Start with an engaging opening line that captures attention
2. For each news item:
   - Write a strong, attention-grabbing headline (use emoji if appropriate)
   - Write a summary that prioritizes the most important/critical points
   - Include the source in parentheses
   - Add the original link at the end
3. Use clear formatting with line breaks between items
4. End with a thought-provoking question or call-to-action
5. Keep the total post under {self.MAX_CHAR_LIMIT} characters

TONE AND STYLE:
- Professional yet conversational
- Focus on insights and implications
- Highlight innovation and trends
- Make it shareable and discussion-worthy

Generate the LinkedIn post now:"""
        
        return prompt
    
    async def __call__(self, state: PostState) -> PostState:
        """
        Generate LinkedIn post from news articles.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with generated LinkedIn post
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
            
            # Log start of LinkedIn post generation with comprehensive state info
            self.logger.log_processing_step(
                session_id=session_id,
                workflow_id=workflow_id,
                step="linkedin_post_generation_start",
                message=f"Generating LinkedIn post for {len(state.get('articles', []))} articles",
                extra_data={
                    "topic": state.get("topic", ""),
                    "article_count": len(state.get("articles", [])),
                    "llm_model": llm_model,
                    "session_id": session_id,
                    "workflow_id": workflow_id,
                    "state_keys": list(state.keys())
                }
            )
            
            # Check if there are no articles
            articles = state.get("articles", [])
            topic = state.get("topic", "Unknown Topic")
            
            if not articles or len(articles) == 0:
                # Create a generic post about the topic
                generic_content = f"📢 Stay tuned for the latest updates on {topic}! 🚀\n\nNo specific news items available at the moment, but exciting developments are always happening in this space.\n\n#{''.join(topic.split())} #TechNews #Innovation"
                
                linkedin_post = GeneratedPostContent(
                    content=generic_content,
                    char_count=len(generic_content),
                    hashtags=self._extract_hashtags(generic_content),
                    shortened_urls=None
                )
                
                # Create updated state maintaining all existing fields
                updated_state = state.copy()
                updated_state.update({
                    "linkedin_post": linkedin_post,
                    "current_step": "linkedin_post_generation",
                    "current_llm_provider": llm_model,
                    "processing_steps": [
                        {
                            "step": "linkedin_post_generation",
                            "status": PostGenerationStatus.COMPLETED,
                            "message": "Generated generic LinkedIn post (no articles available)",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    ]
                })
                
                return updated_state
            
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
            prompt = self._create_linkedin_prompt(state)
            
            # Generate post
            messages = [
                SystemMessage(content="You are a professional social media content creator specializing in LinkedIn posts for the tech industry."),
                HumanMessage(content=prompt)
            ]
            
            response = await llm.ainvoke(messages)
            generated_content = response.content.strip()
            
            # Validate character count
            char_count = len(generated_content)
            if char_count > self.MAX_CHAR_LIMIT:
                # Truncate and add ellipsis
                generated_content = generated_content[:self.MAX_CHAR_LIMIT - 3] + "..."
                char_count = self.MAX_CHAR_LIMIT
            
            # Create post content object
            linkedin_post = GeneratedPostContent(
                content=generated_content,
                char_count=char_count,
                hashtags=self._extract_hashtags(generated_content),
                shortened_urls=None  # URLs not shortened for LinkedIn
            )
            
            # Log successful generation
            self.logger.log_processing_step(
                session_id=session_id or "unknown",
                workflow_id=workflow_id or "unknown",
                step="linkedin_post_generation_complete",
                message=f"Successfully generated LinkedIn post ({char_count} chars)",
                extra_data={
                    "char_count": char_count,
                    "hashtag_count": len(linkedin_post["hashtags"] or [])
                }
            )
            
            # With LangGraph 0.4.8, we can return partial state updates
            # The Annotated reducers will handle preserving immutable fields
            return {
                "linkedin_post": linkedin_post,
                "current_step": "linkedin_post_generation",
                "current_llm_provider": llm_model,
                "processing_steps": [
                    {
                        "step": "linkedin_post_generation",
                        "status": PostGenerationStatus.COMPLETED,
                        "message": f"Generated LinkedIn post with {char_count} characters",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
            
        except Exception as e:
            # Log error
            self.logger.log_error(
                session_id=state.get("session_id", "unknown"),
                workflow_id=state.get("workflow_id", "unknown"),
                step="linkedin_post_generation_error",
                error=e,
                extra_data={
                    "topic": state.get("topic", ""),
                    "article_count": len(state.get("articles", []))
                }
            )
            
            # Create error state update maintaining all existing fields
            error_state = state.copy()
            error_state.update({
                "error_message": f"Failed to generate LinkedIn post: {str(e)}",
                "failed_step": "linkedin_post_generation",
                "current_step": "linkedin_post_generation",
                "processing_steps": [
                    {
                        "step": "linkedin_post_generation",
                        "status": PostGenerationStatus.ERROR,
                        "message": f"Failed to generate LinkedIn post: {str(e)}",
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
