"""
External state manager that bypasses LangGraph's broken state management.

This approach stores workflow state externally and passes only the state ID
through LangGraph, completely avoiding the reducer issues.
"""
import uuid
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json


class ExternalStateManager:
    """
    External state manager that stores workflow state outside of LangGraph.
    
    This completely bypasses LangGraph's broken reducer system by:
    1. Storing all state externally in memory/cache
    2. Passing only a state_key through LangGraph nodes
    3. Nodes retrieve full state using the state_key
    4. Nodes update state externally and return minimal updates
    """
    
    def __init__(self):
        """Initialize the external state manager."""
        self._states: Dict[str, Dict[str, Any]] = {}
        self._state_locks: Dict[str, asyncio.Lock] = {}
        self._cleanup_interval = 3600  # 1 hour cleanup interval
        self._state_ttl = 7200  # 2 hour TTL for states
    
    async def create_state(self, initial_data: Dict[str, Any]) -> str:
        """
        Create a new external state and return its key.
        
        Args:
            initial_data: Initial state data
            
        Returns:
            State key for accessing the state
        """
        state_key = str(uuid.uuid4())
        
        # Add metadata
        state_data = {
            **initial_data,
            "_created_at": datetime.utcnow().timestamp(),
            "_last_accessed": datetime.utcnow().timestamp(),
            "_version": 1
        }
        
        # Store state and create lock
        self._states[state_key] = state_data
        self._state_locks[state_key] = asyncio.Lock()
        
        return state_key
    
    async def get_state(self, state_key: str) -> Optional[Dict[str, Any]]:
        """
        Get state by key.
        
        Args:
            state_key: State key
            
        Returns:
            State data or None if not found
        """
        if state_key not in self._states:
            return None
        
        # Update last accessed time
        self._states[state_key]["_last_accessed"] = datetime.utcnow().timestamp()
        
        # Return copy to prevent external modifications
        return self._states[state_key].copy()
    
    async def update_state(self, state_key: str, updates: Dict[str, Any]) -> bool:
        """
        Update state with new data.
        
        Args:
            state_key: State key
            updates: Updates to apply
            
        Returns:
            True if successful, False if state not found
        """
        if state_key not in self._states:
            return False
        
        async with self._state_locks[state_key]:
            # Apply updates
            self._states[state_key].update(updates)
            self._states[state_key]["_last_accessed"] = datetime.utcnow().timestamp()
            self._states[state_key]["_version"] += 1
        
        return True
    
    async def delete_state(self, state_key: str) -> bool:
        """
        Delete state by key.
        
        Args:
            state_key: State key
            
        Returns:
            True if deleted, False if not found
        """
        if state_key not in self._states:
            return False
        
        del self._states[state_key]
        if state_key in self._state_locks:
            del self._state_locks[state_key]
        
        return True
    
    async def cleanup_expired_states(self):
        """Clean up expired states."""
        current_time = datetime.utcnow().timestamp()
        expired_keys = []
        
        for state_key, state_data in self._states.items():
            last_accessed = state_data.get("_last_accessed", 0)
            if current_time - last_accessed > self._state_ttl:
                expired_keys.append(state_key)
        
        for key in expired_keys:
            await self.delete_state(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            "total_states": len(self._states),
            "active_locks": len(self._state_locks),
            "oldest_state": min(
                (state["_created_at"] for state in self._states.values()),
                default=None
            ),
            "newest_state": max(
                (state["_created_at"] for state in self._states.values()),
                default=None
            )
        }


# Global instance
_external_state_manager = None


def get_external_state_manager() -> ExternalStateManager:
    """Get singleton instance of external state manager."""
    global _external_state_manager
    
    if _external_state_manager is None:
        _external_state_manager = ExternalStateManager()
    
    return _external_state_manager


class StatelessNodeBase:
    """
    Base class for stateless nodes that use external state management.
    
    This completely bypasses LangGraph's state system by:
    1. Receiving only a state_key from LangGraph
    2. Loading full state from external manager
    3. Performing operations with guaranteed state integrity
    4. Updating external state
    5. Returning minimal LangGraph state with just the state_key
    """
    
    def __init__(self, node_name: str):
        """Initialize stateless node."""
        self.node_name = node_name
        self.state_manager = get_external_state_manager()
    
    async def load_external_state(self, langgraph_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load full state from external manager.
        
        Args:
            langgraph_state: Minimal state from LangGraph (contains state_key)
            
        Returns:
            Full external state
            
        Raises:
            ValueError: If state cannot be loaded
        """
        state_key = langgraph_state.get("state_key")
        if not state_key:
            raise ValueError(f"No state_key found in LangGraph state for {self.node_name}")
        
        external_state = await self.state_manager.get_state(state_key)
        if external_state is None:
            raise ValueError(f"External state not found for key {state_key} in {self.node_name}")
        
        return external_state
    
    async def save_external_state(self, state_key: str, updates: Dict[str, Any]) -> bool:
        """
        Save updates to external state.
        
        Args:
            state_key: State key
            updates: Updates to apply
            
        Returns:
            True if successful
        """
        success = await self.state_manager.update_state(state_key, updates)
        if not success:
            raise ValueError(f"Failed to update external state for key {state_key} in {self.node_name}")
        
        return success
    
    async def execute_with_external_state(self, langgraph_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute node logic with external state management.
        
        This method should be implemented by subclasses.
        
        Args:
            langgraph_state: Minimal LangGraph state
            
        Returns:
            Minimal LangGraph state update (just state_key)
        """
        raise NotImplementedError("Subclasses must implement execute_with_external_state")
    
    async def __call__(self, langgraph_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point that handles external state management.
        
        Args:
            langgraph_state: LangGraph state (minimal, just contains state_key)
            
        Returns:
            Minimal LangGraph state update
        """
        try:
            # Execute with external state management
            result = await self.execute_with_external_state(langgraph_state)
            
            # Always return minimal state with state_key preserved
            return {
                "state_key": langgraph_state.get("state_key"),
                **result
            }
            
        except Exception as e:
            # Log error and return error state
            print(f"Error in {self.node_name}: {e}")
            return {
                "state_key": langgraph_state.get("state_key"),
                "error_message": f"Error in {self.node_name}: {str(e)}",
                "failed_step": self.node_name
            }
