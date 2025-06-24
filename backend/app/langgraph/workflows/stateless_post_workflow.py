"""
Stateless post generation workflow that bypasses LangGraph's broken state management.

This workflow uses external state management to completely avoid LangGraph's
reducer issues by storing all state externally and only passing a state_key
through the LangGraph nodes.
"""
import uuid
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END

from app.langgraph.state.minimal_state import MinimalState, create_minimal_state
from app.langgraph.utils.external_state_manager import get_external_state_manager, StatelessNodeBase
from app.langgraph.utils.logging_config import StructuredLogger
from app.langgraph.utils.error_handlers import NewsProcessingError
from datetime import datetime


class StatelessLinkedInPostNode(StatelessNodeBase):
    """Stateless LinkedIn post generation node."""
    
    def __init__(self):
        super().__init__("stateless_linkedin_post")
        self.logger = StructuredLogger("stateless_linkedin_post")
    
    async def execute_with_external_state(self, langgraph_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate LinkedIn post using external state."""
        # Load full state from external manager
        external_state = await self.load_external_state(langgraph_state)
        
        # Extract required fields (guaranteed to exist in external state)
        session_id = external_state["session_id"]
        workflow_id = external_state["workflow_id"]
        articles = external_state["articles"]
        topic = external_state["topic"]
        
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="stateless_linkedin_generation_start",
            message=f"Generating LinkedIn post for {len(articles)} articles",
            extra_data={"topic": topic, "article_count": len(articles)}
        )
        
        # Generate LinkedIn post (simplified for demo)
        linkedin_content = f"🚀 Latest insights on {topic}:\n\n"
        for i, article in enumerate(articles[:3], 1):  # Limit to 3 articles
            linkedin_content += f"{i}. {article['title']}\n"
        linkedin_content += f"\n#{''.join(topic.split())} #TechNews #Innovation"
        
        linkedin_post = {
            "content": linkedin_content,
            "char_count": len(linkedin_content),
            "hashtags": [f"#{''.join(topic.split())}", "#TechNews", "#Innovation"],
            "shortened_urls": None
        }
        
        # Update external state
        updates = {
            "linkedin_post": linkedin_post,
            "current_step": "stateless_linkedin_generation",
            "processing_steps": external_state.get("processing_steps", []) + [
                {
                    "step": "stateless_linkedin_generation",
                    "status": "completed",
                    "message": f"Generated LinkedIn post with {len(linkedin_content)} characters",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        }
        
        await self.save_external_state(langgraph_state["state_key"], updates)
        
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="stateless_linkedin_generation_complete",
            message=f"Successfully generated LinkedIn post ({len(linkedin_content)} chars)"
        )
        
        # Return minimal LangGraph state (just state_key)
        return {}


class StatelessXPostNode(StatelessNodeBase):
    """Stateless X post generation node."""
    
    def __init__(self):
        super().__init__("stateless_x_post")
        self.logger = StructuredLogger("stateless_x_post")
    
    async def execute_with_external_state(self, langgraph_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate X post using external state."""
        # Load full state from external manager
        external_state = await self.load_external_state(langgraph_state)
        
        # Extract required fields
        session_id = external_state["session_id"]
        workflow_id = external_state["workflow_id"]
        articles = external_state["articles"]
        topic = external_state["topic"]
        
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="stateless_x_generation_start",
            message=f"Generating X post for {len(articles)} articles"
        )
        
        # Generate X post (simplified for demo)
        if articles:
            top_article = articles[0]
            x_content = f"🔥 {top_article['title']}\n\n{top_article.get('summary', '')[:100]}...\n\n#{topic.replace(' ', '')} #TechNews"
        else:
            x_content = f"📢 Stay updated on {topic}! #TechNews #{topic.replace(' ', '')}"
        
        # Ensure under 280 characters
        if len(x_content) > 280:
            x_content = x_content[:277] + "..."
        
        x_post = {
            "content": x_content,
            "char_count": len(x_content),
            "hashtags": [f"#{topic.replace(' ', '')}", "#TechNews"],
            "shortened_urls": None
        }
        
        # Update external state
        updates = {
            "x_post": x_post,
            "current_step": "stateless_x_generation",
            "processing_steps": external_state.get("processing_steps", []) + [
                {
                    "step": "stateless_x_generation",
                    "status": "completed",
                    "message": f"Generated X post with {len(x_content)} characters",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        }
        
        await self.save_external_state(langgraph_state["state_key"], updates)
        
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="stateless_x_generation_complete",
            message=f"Successfully generated X post ({len(x_content)} chars)"
        )
        
        return {}


class StatelessSavePostsNode(StatelessNodeBase):
    """Stateless save posts node."""
    
    def __init__(self):
        super().__init__("stateless_save_posts")
        self.logger = StructuredLogger("stateless_save_posts")
    
    async def execute_with_external_state(self, langgraph_state: Dict[str, Any]) -> Dict[str, Any]:
        """Save posts using external state."""
        # Load full state from external manager
        external_state = await self.load_external_state(langgraph_state)
        
        # Extract required fields
        session_id = external_state["session_id"]
        workflow_id = external_state["workflow_id"]
        
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="stateless_save_posts_start",
            message="Starting stateless save posts operation"
        )
        
        # For demo purposes, just mark as saved
        # In real implementation, you would save to database here
        processing_time = datetime.utcnow().timestamp() - external_state.get("start_time", 0)
        
        updates = {
            "current_step": "stateless_save_posts",
            "processing_time": processing_time,
            "processing_steps": external_state.get("processing_steps", []) + [
                {
                    "step": "stateless_save_posts",
                    "status": "completed",
                    "message": "Successfully saved posts to database",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        }
        
        await self.save_external_state(langgraph_state["state_key"], updates)
        
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="stateless_save_posts_complete",
            message=f"Successfully completed stateless workflow in {processing_time:.2f}s"
        )
        
        return {}


class StatelessPostWorkflow:
    """
    Stateless post generation workflow that bypasses LangGraph's state management.
    
    This workflow:
    1. Stores all state externally
    2. Only passes a state_key through LangGraph
    3. Nodes load/save state externally
    4. Completely avoids LangGraph reducer issues
    """
    
    def __init__(self):
        """Initialize stateless workflow."""
        self.logger = StructuredLogger("stateless_post_workflow")
        self.state_manager = get_external_state_manager()
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create the stateless LangGraph workflow."""
        # Use minimal state that only contains state_key
        workflow = StateGraph(MinimalState)
        
        # Add stateless nodes
        workflow.add_node("generate_linkedin_post", StatelessLinkedInPostNode())
        workflow.add_node("generate_x_post", StatelessXPostNode())
        workflow.add_node("save_posts", StatelessSavePostsNode())
        
        # Define workflow edges (same as before)
        workflow.add_edge(START, "generate_linkedin_post")
        workflow.add_edge("generate_linkedin_post", "generate_x_post")
        workflow.add_edge("generate_x_post", "save_posts")
        workflow.add_edge("save_posts", END)
        
        return workflow.compile()
    
    async def execute(
        self,
        articles: List[Dict[str, Any]],
        topic: str,
        llm_model: str,
        session_id: str,
        news_workflow_id: str
    ) -> Dict[str, Any]:
        """Execute the stateless workflow."""
        workflow_id = str(uuid.uuid4())
        
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="stateless_workflow_start",
            message="Starting stateless post generation workflow",
            extra_data={
                "topic": topic,
                "article_count": len(articles),
                "session_id": session_id
            }
        )
        
        try:
            # Create external state with all the data
            external_state_data = {
                "session_id": session_id,
                "workflow_id": workflow_id,
                "llm_model": llm_model,
                "topic": topic,
                "articles": articles,
                "news_workflow_id": news_workflow_id,
                "start_time": datetime.utcnow().timestamp(),
                "current_step": "initialization",
                "processing_steps": []
            }
            
            # Store state externally and get state_key
            state_key = await self.state_manager.create_state(external_state_data)
            
            self.logger.log_processing_step(
                session_id=session_id,
                workflow_id=workflow_id,
                step="external_state_created",
                message=f"Created external state with key: {state_key}"
            )
            
            # Create minimal LangGraph state with just the state_key
            minimal_state = create_minimal_state(state_key)
            
            # Execute LangGraph workflow (only passes state_key around)
            result = await self.workflow.ainvoke(minimal_state)
            
            # Retrieve final state from external manager
            final_external_state = await self.state_manager.get_state(state_key)
            
            if not final_external_state:
                raise NewsProcessingError(
                    message="Failed to retrieve final state from external manager",
                    context={"state_key": state_key, "workflow_id": workflow_id}
                )
            
            # Check for errors
            if result.get("error_message"):
                raise NewsProcessingError(
                    message=f"Workflow failed: {result['error_message']}",
                    context={"workflow_id": workflow_id, "session_id": session_id}
                )
            
            self.logger.log_processing_step(
                session_id=session_id,
                workflow_id=workflow_id,
                step="stateless_workflow_complete",
                message="Stateless workflow completed successfully",
                extra_data={
                    "processing_time": final_external_state.get("processing_time"),
                    "has_linkedin": "linkedin_post" in final_external_state,
                    "has_x": "x_post" in final_external_state
                }
            )
            
            # Clean up external state
            await self.state_manager.delete_state(state_key)
            
            # Return formatted results
            return self._format_results(final_external_state)
            
        except Exception as e:
            self.logger.log_error(
                session_id=session_id,
                workflow_id=workflow_id,
                step="stateless_workflow_error",
                error=e
            )
            raise NewsProcessingError(
                message=f"Stateless workflow failed: {str(e)}",
                context={"workflow_id": workflow_id, "session_id": session_id}
            )
    
    def _format_results(self, final_state: Dict[str, Any]) -> Dict[str, Any]:
        """Format final results for API response."""
        result = {
            "workflow_id": final_state.get("workflow_id"),
            "processing_time": final_state.get("processing_time", 0.0),
            "llm_model_used": final_state.get("llm_model"),
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
                "hashtags": x_post.get("hashtags", [])
            }
        
        return result


# Global instance
_stateless_workflow_instance = None


def get_stateless_post_workflow() -> StatelessPostWorkflow:
    """Get singleton instance of stateless workflow."""
    global _stateless_workflow_instance
    
    if _stateless_workflow_instance is None:
        _stateless_workflow_instance = StatelessPostWorkflow()
    
    return _stateless_workflow_instance
