"""
State access helpers for LangGraph workflows.

These utilities provide robust state access patterns that work
with both full and partial state updates, addressing reducer
compatibility issues.
"""
from typing import Dict, Any, Optional, TypeVar, Union
from app.langgraph.state.post_state import PostState
from app.langgraph.state.news_state import NewsState

StateType = TypeVar('StateType', PostState, NewsState, Dict[str, Any])


class StateAccessError(Exception):
    """Raised when required state fields cannot be accessed."""
    pass


class StateAccessHelper:
    """
    Helper class for robust state field access in LangGraph workflows.
    
    This helper addresses the issue where LangGraph reducers may not work
    as expected, causing nodes to receive partial state updates instead
    of the full accumulated state.
    """
    
    @staticmethod
    def get_required_field(
        state: StateType,
        field_name: str,
        field_type: str = "string",
        context: str = "workflow"
    ) -> Any:
        """
        Get a required field from state with robust error handling.
        
        Args:
            state: The workflow state (full or partial)
            field_name: Name of the field to retrieve
            field_type: Type of field for error messages
            context: Context for error messages
            
        Returns:
            The field value
            
        Raises:
            StateAccessError: If field is missing or invalid
        """
        try:
            # Try direct access first
            value = state[field_name]
            
            # Validate the value is not empty
            if value is None:
                raise StateAccessError(
                    f"{field_name} is None in {context} state"
                )
            
            # For string fields, check for empty strings
            if field_type == "string" and isinstance(value, str):
                if not value.strip():
                    raise StateAccessError(
                        f"{field_name} is empty in {context} state"
                    )
            
            return value
            
        except KeyError:
            raise StateAccessError(
                f"{field_name} is missing from {context} state. "
                f"Available keys: {list(state.keys())}"
            )
        except Exception as e:
            raise StateAccessError(
                f"Error accessing {field_name} from {context} state: {str(e)}"
            )
    
    @staticmethod
    def get_optional_field(
        state: StateType,
        field_name: str,
        default: Any = None
    ) -> Any:
        """
        Get an optional field from state with safe fallback.
        
        Args:
            state: The workflow state
            field_name: Name of the field to retrieve
            default: Default value if field is missing
            
        Returns:
            The field value or default
        """
        return state.get(field_name, default)
    
    @staticmethod
    def validate_post_workflow_state(state: StateType) -> Dict[str, str]:
        """
        Validate and extract required fields for post workflow nodes.
        
        Args:
            state: The workflow state
            
        Returns:
            Dictionary with validated required fields
            
        Raises:
            StateAccessError: If any required field is missing or invalid
        """
        try:
            session_id = StateAccessHelper.get_required_field(
                state, "session_id", "string", "post workflow"
            )
            
            workflow_id = StateAccessHelper.get_required_field(
                state, "workflow_id", "string", "post workflow"
            )
            
            llm_model = StateAccessHelper.get_required_field(
                state, "llm_model", "string", "post workflow"
            )
            
            return {
                "session_id": session_id,
                "workflow_id": workflow_id,
                "llm_model": llm_model
            }
            
        except StateAccessError as e:
            # Add additional context about the state access issue
            error_msg = str(e)
            if "missing from" in error_msg:
                error_msg += (
                    "\n\nThis error suggests that LangGraph reducers are not working correctly. "
                    "The node is receiving a partial state update instead of the full accumulated state. "
                    "This is a known issue with certain LangGraph versions or configurations."
                )
            raise StateAccessError(error_msg)
    
    @staticmethod
    def validate_news_workflow_state(state: StateType) -> Dict[str, str]:
        """
        Validate and extract required fields for news workflow nodes.
        
        Args:
            state: The workflow state
            
        Returns:
            Dictionary with validated required fields
            
        Raises:
            StateAccessError: If any required field is missing or invalid
        """
        try:
            session_id = StateAccessHelper.get_required_field(
                state, "session_id", "string", "news workflow"
            )
            
            workflow_id = StateAccessHelper.get_required_field(
                state, "workflow_id", "string", "news workflow"
            )
            
            return {
                "session_id": session_id,
                "workflow_id": workflow_id
            }
            
        except StateAccessError as e:
            # Add additional context about the state access issue
            error_msg = str(e)
            if "missing from" in error_msg:
                error_msg += (
                    "\n\nThis error suggests that LangGraph reducers are not working correctly. "
                    "The node is receiving a partial state update instead of the full accumulated state. "
                    "This is a known issue with certain LangGraph versions or configurations."
                )
            raise StateAccessError(error_msg)
    
    @staticmethod
    def create_debug_state_info(state: StateType) -> Dict[str, Any]:
        """
        Create debug information about the current state.
        
        Args:
            state: The workflow state
            
        Returns:
            Dictionary with debug information
        """
        return {
            "state_keys": list(state.keys()) if hasattr(state, 'keys') else [],
            "state_type": type(state).__name__,
            "has_session_id": "session_id" in state if hasattr(state, '__contains__') else False,
            "has_workflow_id": "workflow_id" in state if hasattr(state, '__contains__') else False,
            "session_id_value": repr(state.get("session_id", "NOT_FOUND")) if hasattr(state, 'get') else "NO_GET_METHOD",
            "workflow_id_value": repr(state.get("workflow_id", "NOT_FOUND")) if hasattr(state, 'get') else "NO_GET_METHOD",
        }


# Convenience functions for common use cases
def get_post_workflow_fields(state: StateType) -> Dict[str, str]:
    """
    Convenience function to get required post workflow fields.
    
    Args:
        state: The workflow state
        
    Returns:
        Dictionary with session_id, workflow_id, and llm_model
        
    Raises:
        StateAccessError: If any required field is missing or invalid
    """
    return StateAccessHelper.validate_post_workflow_state(state)


def get_news_workflow_fields(state: StateType) -> Dict[str, str]:
    """
    Convenience function to get required news workflow fields.
    
    Args:
        state: The workflow state
        
    Returns:
        Dictionary with session_id and workflow_id
        
    Raises:
        StateAccessError: If any required field is missing or invalid
    """
    return StateAccessHelper.validate_news_workflow_state(state)


def safe_get_field(state: StateType, field_name: str, default: Any = None) -> Any:
    """
    Safely get a field from state with fallback.
    
    Args:
        state: The workflow state
        field_name: Name of the field to retrieve
        default: Default value if field is missing
        
    Returns:
        The field value or default
    """
    return StateAccessHelper.get_optional_field(state, field_name, default)
