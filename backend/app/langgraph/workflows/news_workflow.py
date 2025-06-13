"""
News processing workflow composition using LangGraph.

This workflow follows LangGraph best practices:
- Clear entry and exit points (START/END)
- Conditional edges for flow control
- Proper error handling and state management
- Modular node composition
"""
import uuid
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END

from app.langgraph.state.news_state import NewsState, create_initial_state
from app.langgraph.nodes.validate_input_node import ValidateInputNode
from app.langgraph.nodes.check_quota_node import CheckQuotaNode
from app.langgraph.nodes.fetch_news_node import FetchNewsNode
from app.langgraph.nodes.filter_articles_node import FilterArticlesNode
from app.langgraph.nodes.summarize_content_node import SummarizeContentNode
from app.langgraph.nodes.save_results_node import SaveResultsNode
from app.langgraph.utils.logging_config import StructuredLogger


class NewsWorkflow:
    """
    Complete news processing workflow using LangGraph.
    
    Workflow Steps:
    1. START -> validate_input: Validate all input parameters
    2. validate_input -> check_quota: Check user quotas and duplicates
    3. check_quota -> fetch_news (if quota available) or END (if quota exceeded)
    4. fetch_news -> filter_articles: Filter and rank articles
    5. filter_articles -> summarize_content: Generate AI summaries
    6. summarize_content -> save_results: Cache results and finalize
    7. save_results -> END: Complete workflow
    
    This workflow implements proper error handling, conditional
    flow control, and comprehensive state management.
    """
    
    def __init__(self):
        """Initialize news workflow with structured logger."""
        self.logger = StructuredLogger("news_workflow")
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """
        Create and configure the LangGraph workflow.
        
        Returns:
            Compiled StateGraph workflow
        """
        # Create workflow with NewsState
        workflow = StateGraph(NewsState)
        
        # Add all nodes
        workflow.add_node("validate_input", ValidateInputNode())
        workflow.add_node("check_quota", CheckQuotaNode())
        workflow.add_node("fetch_news", FetchNewsNode())
        workflow.add_node("filter_articles", FilterArticlesNode())
        workflow.add_node("summarize_content", SummarizeContentNode())
        workflow.add_node("save_results", SaveResultsNode())
        
        # Define workflow edges
        self._add_workflow_edges(workflow)
        
        # Set entry point
        workflow.set_entry_point("validate_input")
        
        # Compile and return workflow
        return workflow.compile()
    
    def _add_workflow_edges(self, workflow: StateGraph) -> None:
        """
        Add edges to define workflow flow control.
        
        Args:
            workflow: StateGraph to add edges to
        """
        # Linear flow for most steps
        workflow.add_edge(START, "validate_input")
        workflow.add_edge("validate_input", "check_quota")
        
        # Conditional edge after quota check
        workflow.add_conditional_edges(
            "check_quota",
            self._should_continue_after_quota,
            {
                "continue": "fetch_news",
                "end": END
            }
        )
        
        # Continue linear flow
        workflow.add_edge("fetch_news", "filter_articles")
        workflow.add_edge("filter_articles", "summarize_content")
        workflow.add_edge("summarize_content", "save_results")
        workflow.add_edge("save_results", END)
    
    def _should_continue_after_quota(self, state: NewsState) -> str:
        """
        Determine if workflow should continue after quota check.
        
        Args:
            state: Current workflow state
            
        Returns:
            "continue" if quota is available, "end" if quota exceeded
        """
        quota_info = state.get("quota_info")
        
        if not quota_info:
            # No quota info means quota check failed
            return "end"
        
        if quota_info.get("quota_available", False):
            return "continue"
        else:
            return "end"
    
    async def execute(
        self,
        topic: str,
        date: str,
        top_n: int,
        llm_model: str,
        session_id: str
    ) -> NewsState:
        """
        Execute the complete news processing workflow.
        
        Args:
            topic: News topic to search for
            date: Date in YYYY-MM-DD format
            top_n: Number of articles to fetch (1-12)
            llm_model: LLM model to use for summarization
            session_id: User session identifier
            
        Returns:
            Final workflow state with results
            
        Raises:
            Various workflow errors depending on failure point
        """
        # Generate unique workflow ID
        workflow_id = str(uuid.uuid4())
        
        # Log workflow start
        self.logger.log_processing_step(
            session_id=session_id,
            workflow_id=workflow_id,
            step="workflow_start",
            message="Starting news processing workflow",
            extra_data={
                "topic": topic,
                "date": date,
                "top_n": top_n,
                "llm_model": llm_model
            }
        )
        
        try:
            # Create initial state
            initial_state = create_initial_state(
                topic=topic,
                date=date,
                top_n=top_n,
                llm_model=llm_model,
                session_id=session_id,
                workflow_id=workflow_id
            )
            
            # Execute workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Log workflow completion
            self.logger.log_processing_step(
                session_id=session_id,
                workflow_id=workflow_id,
                step="workflow_complete",
                message="News processing workflow completed successfully",
                extra_data={
                    "processing_time": final_state.get("processing_time"),
                    "articles_processed": len(final_state.get("summarized_articles", [])),
                    "final_step": final_state.get("current_step")
                }
            )
            
            return final_state
            
        except Exception as e:
            # Log workflow failure
            self.logger.log_error(
                session_id=session_id,
                workflow_id=workflow_id,
                step="workflow_error",
                error=e,
                extra_data={
                    "topic": topic,
                    "date": date,
                    "top_n": top_n,
                    "llm_model": llm_model
                }
            )
            
            raise


# Global workflow instance
_workflow_instance = None


def get_news_workflow() -> NewsWorkflow:
    """
    Get singleton instance of news workflow.
    
    Returns:
        NewsWorkflow instance
    """
    global _workflow_instance
    
    if _workflow_instance is None:
        _workflow_instance = NewsWorkflow()
    
    return _workflow_instance


async def execute_news_workflow(
    topic: str,
    date: str,
    top_n: int,
    llm_model: str,
    session_id: str
) -> Dict[str, Any]:
    """
    Execute news processing workflow and return formatted results.
    
    Args:
        topic: News topic to search for
        date: Date in YYYY-MM-DD format
        top_n: Number of articles to fetch (1-12)
        llm_model: LLM model to use for summarization
        session_id: User session identifier
        
    Returns:
        Formatted workflow results
        
    Raises:
        Various workflow errors depending on failure point
    """
    # Get workflow instance
    workflow = get_news_workflow()
    
    # Execute workflow
    final_state = await workflow.execute(
        topic=topic,
        date=date,
        top_n=top_n,
        llm_model=llm_model,
        session_id=session_id
    )
    
    # Format results for API response
    summarized_articles = final_state.get("summarized_articles", [])
    quota_info = final_state.get("quota_info", {})
    
    return {
        "articles": summarized_articles,
        "total_found": final_state.get("total_found", len(summarized_articles)),
        "processing_time": final_state.get("processing_time", 0.0),
        "quota_remaining": quota_info.get("remaining", 0),
        "workflow_id": final_state.get("workflow_id"),
        "llm_provider_used": final_state.get("current_llm_provider"),
        "cache_hit": final_state.get("cache_hit", False)
    }
