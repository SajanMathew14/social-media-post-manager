# ValidationError Fix - Post Generation API

## Issue Fixed

**Error**: `ValidationError.__init__() got an unexpected keyword argument 'message'`

**Location**: `backend/app/api/routes/posts.py` line 102

## Root Cause

The `ValidationError` class in `backend/app/langgraph/utils/error_handlers.py` expects these parameters:
```python
def __init__(self, field: str, value: Any, reason: str):
```

But the posts.py file was calling it with incorrect parameters:
```python
# INCORRECT (was causing the error)
raise ValidationError(
    message="Invalid session ID",
    context={"session_id": request.sessionId}
)
```

## Fix Applied

Changed the ValidationError instantiation to use the correct parameters:

```python
# CORRECT (fixed)
raise ValidationError(
    field="sessionId",
    value=request.sessionId,
    reason="Session ID does not exist in database"
)
```

## Files Modified

- `backend/app/api/routes/posts.py` - Fixed ValidationError instantiation at line 102

## Testing

The ValidationError fix resolves the immediate 500 Internal Server Error. However, you may encounter additional issues related to:

1. **Session validation** - The session ID `550e8400-e29b-41d4-a716-446655440000` needs to exist in your database
2. **LLM provider configuration** - Ensure you have API keys configured for the requested model
3. **Database connectivity** - Ensure your database is accessible

## Updated Curl Command

For your deployed server, use this curl command (replace `YOUR_DEPLOYED_URL` with your actual server URL):

```bash
curl -X POST YOUR_DEPLOYED_URL/api/posts/generate \
  -H "Content-Type: application/json" \
  -d '{
    "articles": [
      {
        "title": "AI Breakthrough in Medical Diagnostics",
        "url": "https://techcrunch.com/ai-medical-breakthrough",
        "source": "TechCrunch",
        "summary": "New AI system achieves 95% accuracy in early cancer detection, potentially revolutionizing medical diagnostics and saving millions of lives.",
        "published_at": "2025-06-23T10:00:00Z",
        "relevance_score": 0.95
      },
      {
        "title": "Quantum Computing Reaches New Milestone",
        "url": "https://nature.com/quantum-computing-milestone",
        "source": "Nature",
        "summary": "Researchers demonstrate quantum supremacy with 1000-qubit processor, opening new possibilities for complex problem solving.",
        "published_at": "2025-06-23T09:30:00Z",
        "relevance_score": 0.88
      }
    ],
    "topic": "AI Technology",
    "llmModel": "claude-3-5-sonnet",
    "sessionId": "550e8400-e29b-41d4-a716-446655440000",
    "newsWorkflowId": "123e4567-e89b-12d3-a456-426614174000"
  }'
```

## Next Steps

1. **Deploy the fix** to your server
2. **Create a valid session** in your database if the session ID doesn't exist
3. **Verify LLM provider configuration** (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
4. **Test the endpoint** with the corrected curl command

## Expected Behavior After Fix

- ✅ No more ValidationError parameter errors
- ✅ Proper error messages for invalid session IDs
- ✅ Workflow can proceed to LLM provider validation and post generation

The fix ensures that validation errors are properly constructed and handled, allowing the API to provide meaningful error responses instead of crashing with parameter errors.
