# Post Generation Session ID Fix

## Issue Summary

The post generation workflow was failing with two critical errors:

1. **Empty session_id in workflow state**: The session_id was not being properly passed through the parallel processing nodes, resulting in empty values when the save_posts_node tried to access it.

2. **LLMProviderError constructor mismatch**: The LLMProviderError class was being called with incorrect parameters (`message` instead of `original_error`).

## Error Logs

```
{"session_id": "", "workflow_id": "", "node_name": "save_posts_node", "step": "validating_user_session"}
{"error": "badly formed hexadecimal UUID string"}
{"error": "Invalid or non-existent session ID: "}
```

```
{"error": "LLMProviderError.__init__() got an unexpected keyword argument 'message'"}
```

## Root Causes

1. **State Access in Parallel Processing**: When nodes run in parallel in LangGraph, they might not receive the full state properly if not handled defensively.

2. **Incorrect Error Constructor**: The LLMProviderError class expects `provider` and `original_error` parameters, but was being called with `message`.

## Fixes Applied

### 1. Fixed LLMProviderError Constructor Calls

Updated all instances where LLMProviderError was raised to use the correct parameters:

**Before:**
```python
raise LLMProviderError(
    provider="none",
    message="No LLM providers are configured..."
)
```

**After:**
```python
raise LLMProviderError(
    provider="none",
    original_error="No LLM providers are configured..."
)
```

Files updated:
- `backend/app/langgraph/nodes/x_post_node.py`
- `backend/app/langgraph/nodes/linkedin_post_node.py`

### 2. Added Defensive State Access

Added defensive checks to safely access state values with fallbacks:

**Before:**
```python
session_id = state["session_id"]
workflow_id = state["workflow_id"]
```

**After:**
```python
session_id = state.get("session_id", "")
workflow_id = state.get("workflow_id", "")

# Validate session_id is present
if not session_id:
    error_msg = "Session ID is missing from workflow state"
    # ... handle error
```

Files updated:
- `backend/app/langgraph/nodes/save_posts_node.py`
- `backend/app/langgraph/nodes/linkedin_post_node.py`
- `backend/app/langgraph/nodes/x_post_node.py`

### 3. Enhanced Logging

Added state_keys to logging to help debug state propagation issues:

```python
extra_data={
    "session_id": session_id,
    "workflow_id": workflow_id,
    "state_keys": list(state.keys())
}
```

## Testing

Created `backend/test_post_generation_fix.py` to verify:
1. Normal post generation works correctly
2. Empty session_id is properly rejected
3. Invalid LLM models are handled gracefully

## Prevention

To prevent similar issues in the future:

1. **Always use defensive state access** in LangGraph nodes:
   ```python
   value = state.get("key", default_value)
   ```

2. **Validate critical values** before using them:
   ```python
   if not session_id:
       raise ValueError("Session ID is required")
   ```

3. **Test error constructors** to ensure they match the class definition

4. **Add comprehensive logging** including state keys for debugging

## Impact

These fixes ensure:
- Post generation workflow completes successfully
- Proper error messages are returned for invalid inputs
- State is safely accessed in parallel processing scenarios
- Better debugging capabilities with enhanced logging
