"""
Minimal LangGraph state that only carries a state key.

This completely bypasses LangGraph's broken reducer system by storing
all actual state externally and only passing a state_key through LangGraph.
"""
from typing import Dict, Any, Annotated
from typing_extensions import TypedDict


def keep_state_key(existing: str, new: str) -> str:
    """Reducer that always keeps the existing state_key."""
    return existing if existing else new


class MinimalState(TypedDict):
    """
    Minimal state that only contains a state_key.
    
    This bypasses all LangGraph reducer issues by storing the actual
    workflow state externally and only passing a reference through LangGraph.
    """
    
    # The only field that goes through LangGraph - a reference to external state
    state_key: Annotated[str, keep_state_key]
    
    # Optional fields for error handling (these can be lost, we don't care)
    error_message: str
    failed_step: str


def create_minimal_state(state_key: str) -> MinimalState:
    """
    Create a minimal LangGraph state with just the state key.
    
    Args:
        state_key: External state key
        
    Returns:
        Minimal state for LangGraph
    """
    return MinimalState(
        state_key=state_key,
        error_message="",
        failed_step=""
    )
