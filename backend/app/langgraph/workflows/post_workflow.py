"""
Post generation workflow composition using LangGraph.

This workflow generates LinkedIn and X posts from news articles
using serial processing to ensure proper state propagation.
"""
import uuid
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END

from app.langgraph.state.post_state import PostState, create_initial_post_state
from app.langgraph.nodes.linkedin_post_node import LinkedInPostNode
from app.langgraph.nodes.x_post_node import XPostNode
from app.langgraph.nodes.save_posts_node import SavePostsNode
from app.langgraph.utils.logging_config import StructuredLogger
from app.langgraph.utils.error_handlers import NewsProcessingError


class PostWorkflow:
    """
    Complete post generation workflow using LangGraph.
    
    Workflow Steps (SERIAL EXECUTION):
    1. START -> generate_linkedin_post: Generate LinkedIn post
    2. generate_linkedin_post -> generate_x_post: Generate X (Twitter) post
    3. generate_x_post -> save_posts: Save both posts to database
    4. save_posts -> END: Complete workflow
    
    This workflow implements serial processing to ensure proper state
    propagation, error handling, and comprehensive state management.
    """
    
    def __init__(self):
        """Initialize post workflow with structured logger."""
        self.logger = StructuredLogger("post_workflow")
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """
        Create and configure the LangGraph workflow.
        
        Returns:
            Compiled StateGraph workflow
        """
        # Create workflow with PostState
        workflow = StateGraph(PostState)
        
        # Add all nodes
        workflow.add_node("generate_linkedin_post", LinkedInPostNode())
        workflow.add_node("generate_x_post", XPostNode())
        workflow.add_node("save_posts", SavePostsNode())
        
        # Define workflow edges - SERIAL execution to ensure state propagation
        # Start with LinkedIn post generation
        workflow.add_edge(START, "generate_linkedin_post")
        
        # Then generate X post
        workflow.add_edge("generate_linkedin_post", "generate_x_post")
        
        # Finally save both posts
        workflow.add_edge("generate_x_post", "save_posts")
        
        # Save posts to END
        workflow.add_edge("save_posts", END)
        
        # Compile and return workflow
        return workflow.compile()
    
    async def execute(
        self,
        articles: List[Dict[str, Any]],
        topic: str,
        llm_model: str,
        session_id: str,
        news_workflow_id: str
    ) -> PostState:
        """
        Execute the complete post generation workflow.
        
        Args:
            articles: List of news articles to generate posts from
            topic: News topic
            llm_model: LLM model to use for generation
            session_id: User session identifier
            news_workflow_id: ID of the news workflow that produced these articles
            
        Returns:
            Final workflow state with results
            
        Raises:
            Various workflow errors depending on failure point
        """
        # Generate unique workflow ID
        workflow_id = str(uuid.uuid4())
        
        # Log workflow start with comprehensive details
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="post_workflow_start",
            message="Starting post generation workflow",
            extra_data={
                "topic": topic,
                "article_count": len(articles),
                "llm_model": llm_model,
                "news_workflow_id": news_workflow_id,
                "session_id": session_id
            }
        )
        
        try:
            # Validate input parameters
            if not articles:
                raise ValueError("No articles provided for post generation")
            
            if not topic or not topic.strip():
                raise ValueError("Topic is required for post generation")
            
            if not llm_model or not llm_model.strip():
                raise ValueError("LLM model is required for post generation")
            
            # Log input validation success
            self.logger.log_processing_step(
                session_id=session_id,
                workflow_id=workflow_id,
                step="input_validation_complete",
                message="Input validation completed successfully",
                extra_data={
                    "articles_validated": len(articles),
                    "topic_length": len(topic),
                    "llm_model": llm_model
                }
            )
            
            # Create initial state
            self.logger.log_processing_step(
                session_id=session_id,
                workflow_id=workflow_id,
                step="creating_initial_state",
                message="Creating initial workflow state"
            )
            
            initial_state = create_initial_post_state(
                articles=articles,
                topic=topic,
                llm_model=llm_model,
                session_id=session_id,
                workflow_id=workflow_id,
                news_workflow_id=news_workflow_id
            )
            
            # Log workflow execution start
            self.logger.log_processing_step(
                session_id=session_id,
                workflow_id=workflow_id,
                step="executing_workflow",
                message="Executing LangGraph workflow"
            )
            
            # Execute workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Validate final state
            if not final_state:
                raise NewsProcessingError(
                    message="Workflow execution returned empty state",
                    context={"workflow_id": workflow_id, "session_id": session_id}
                )
            
            # Check if workflow completed successfully
            has_error = final_state.get("error_message") is not None
            if has_error:
                self.logger.log_error(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    step="workflow_completed_with_error",
                    error=final_state.get("error_message", "Unknown workflow error"),
                    extra_data={
                        "failed_step": final_state.get("failed_step"),
                        "current_step": final_state.get("current_step")
                    }
                )
                raise NewsProcessingError(
                    message=f"Workflow failed at step '{final_state.get('failed_step', 'unknown')}': {final_state.get('error_message', 'Unknown error')}",
                    context={
                        "workflow_id": workflow_id,
                        "session_id": session_id,
                        "failed_step": final_state.get("failed_step"),
                        "error_message": final_state.get("error_message")
                    }
                )
            
            # Log successful workflow completion
            self.logger.log_processing_step(
                session_id=session_id,
                workflow_id=workflow_id,
                step="post_workflow_complete",
                message="Post generation workflow completed successfully",
                extra_data={
                    "processing_time": final_state.get("processing_time"),
                    "has_linkedin": final_state.get("linkedin_post") is not None,
                    "has_x": final_state.get("x_post") is not None,
                    "final_step": final_state.get("current_step"),
                    "total_processing_steps": len(final_state.get("processing_steps", []))
                }
            )
            
            return final_state
            
        except NewsProcessingError:
            # Re-raise custom errors without wrapping
            raise
            
        except Exception as e:
            # Log and wrap unexpected errors
            self.logger.log_error(
                session_id=session_id,
                workflow_id=workflow_id,
                step="post_workflow_unexpected_error",
                error=e,
                extra_data={
                    "error_type": type(e).__name__,
                    "topic": topic,
                    "article_count": len(articles) if articles else 0,
                    "llm_model": llm_model
                }
            )
            
            raise NewsProcessingError(
                message=f"Unexpected error in post generation workflow: {str(e)}",
                context={
                    "workflow_id": workflow_id,
                    "session_id": session_id,
                    "error_type": type(e).__name__,
                    "original_error": str(e)
                }
            )


# Global workflow instance
_post_workflow_instance = None


def get_post_workflow() -> PostWorkflow:
    """
    Get singleton instance of post workflow.
    
    Returns:
        PostWorkflow instance
    """
    global _post_workflow_instance
    
    if _post_workflow_instance is None:
        _post_workflow_instance = PostWorkflow()
    
    return _post_workflow_instance


async def execute_post_workflow(
    articles: List[Dict[str, Any]],
    topic: str,
    llm_model: str,
    session_id: str,
    news_workflow_id: str
) -> Dict[str, Any]:
    """
    Execute post generation workflow and return formatted results.
    
    Args:
        articles: List of news articles to generate posts from
        topic: News topic
        llm_model: LLM model to use for generation
        session_id: User session identifier
        news_workflow_id: ID of the news workflow that produced these articles
        
    Returns:
        Formatted workflow results
        
    Raises:
        Various workflow errors depending on failure point
    """
    # Get workflow instance
    workflow = get_post_workflow()
    
    # Execute workflow
    final_state = await workflow.execute(
        articles=articles,
        topic=topic,
        llm_model=llm_model,
        session_id=session_id,
        news_workflow_id=news_workflow_id
    )
    
    # Format results for API response
    result = {
        "workflow_id": final_state.get("workflow_id"),
        "processing_time": final_state.get("processing_time", 0.0),
        "llm_model_used": final_state.get("current_llm_provider"),
        "posts": {}
    }
    
    # Add LinkedIn post if generated
    if final_state.get("linkedin_post"):
        linkedin_post = final_state["linkedin_post"]
        result["posts"]["linkedin"] = {
            "content": linkedin_post["content"],
            "char_count": linkedin_post["char_count"],
            "hashtags": linkedin_post.get("hashtags", [])
        }
    
    # Add X post if generated
    if final_state.get("x_post"):
        x_post = final_state["x_post"]
        result["posts"]["x"] = {
            "content": x_post["content"],
            "char_count": x_post["char_count"],
            "hashtags": x_post.get("hashtags", []),
            "shortened_urls": x_post.get("shortened_urls", {})
        }
    
    return result
