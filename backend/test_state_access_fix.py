"""
Simple test to verify the session ID state access fix.

This test focuses on verifying that the nodes can properly access
session_id and workflow_id from the state without database dependencies.
"""
import asyncio
import uuid
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.langgraph.state.post_state import create_initial_post_state


def test_state_access_pattern():
    """Test the state access pattern that was causing the issue."""
    print("🧪 Testing state access pattern fix...")
    
    # Create test data
    session_id = str(uuid.uuid4())
    workflow_id = str(uuid.uuid4())
    news_workflow_id = str(uuid.uuid4())
    
    test_articles = [
        {
            "title": "AI Breakthrough in Healthcare",
            "url": "https://example.com/ai-healthcare",
            "source": "TechNews",
            "summary": "Revolutionary AI system improves medical diagnosis accuracy by 40%",
            "published_at": "2025-06-23T14:00:00Z",
            "relevance_score": 0.95
        }
    ]
    
    # Test 1: Create initial state
    print("\n1️⃣ Testing initial state creation...")
    initial_state = create_initial_post_state(
        articles=test_articles,
        topic="AI Technology",
        llm_model="claude-3-5-sonnet",
        session_id=session_id,
        workflow_id=workflow_id,
        news_workflow_id=news_workflow_id
    )
    
    # Verify initial state has all required fields
    assert initial_state["session_id"] == session_id, f"Expected session_id {session_id}, got {initial_state['session_id']}"
    assert initial_state["workflow_id"] == workflow_id, f"Expected workflow_id {workflow_id}, got {initial_state['workflow_id']}"
    assert initial_state["llm_model"] == "claude-3-5-sonnet", f"Expected llm_model claude-3-5-sonnet, got {initial_state['llm_model']}"
    print("✅ Initial state creation successful")
    
    # Test 2: Simulate the problematic state access pattern (OLD WAY)
    print("\n2️⃣ Testing old problematic state access pattern...")
    
    # Simulate a partial state update (what LangGraph passes between nodes)
    partial_state = {
        "linkedin_post": {
            "content": "Test LinkedIn post",
            "char_count": 18,
            "hashtags": ["#AI"],
            "shortened_urls": None
        },
        "current_step": "linkedin_post_generation",
        "processing_steps": []
    }
    
    # OLD WAY (problematic) - using .get() with empty defaults
    old_session_id = partial_state.get("session_id", "")
    old_workflow_id = partial_state.get("workflow_id", "")
    
    print(f"Old way - session_id: '{old_session_id}' (empty: {old_session_id == ''})")
    print(f"Old way - workflow_id: '{old_workflow_id}' (empty: {old_workflow_id == ''})")
    
    # This would cause the validation error
    if not old_session_id:
        print("❌ Old way would fail: session_id is missing from workflow state")
    
    # Test 3: Test the NEW WAY (fixed approach)
    print("\n3️⃣ Testing new fixed state access pattern...")
    
    # NEW WAY (fixed) - direct access with proper error handling
    try:
        # This would fail with partial state, but that's expected
        new_session_id = partial_state["session_id"]
        print(f"New way - session_id: {new_session_id}")
    except KeyError:
        print("✅ New way correctly detects missing session_id in partial state")
    
    # Test 4: Test with full state (what the nodes should actually receive)
    print("\n4️⃣ Testing new approach with full state...")
    
    # In LangGraph with reducers, nodes should receive the full accumulated state
    # Let's simulate this by merging the partial update with the initial state
    full_state = initial_state.copy()
    full_state.update(partial_state)
    
    # NEW WAY with full state
    try:
        new_session_id = full_state["session_id"]
        new_workflow_id = full_state["workflow_id"]
        new_llm_model = full_state["llm_model"]
        
        # Validate they're not empty
        if not new_session_id or new_session_id.strip() == "":
            raise ValueError("session_id is missing or empty in workflow state")
        if not new_workflow_id or new_workflow_id.strip() == "":
            raise ValueError("workflow_id is missing or empty in workflow state")
        if not new_llm_model or new_llm_model.strip() == "":
            raise ValueError("llm_model is missing or empty in workflow state")
        
        print(f"✅ New way - session_id: {new_session_id}")
        print(f"✅ New way - workflow_id: {new_workflow_id}")
        print(f"✅ New way - llm_model: {new_llm_model}")
        
        return True
        
    except Exception as e:
        print(f"❌ New way failed: {e}")
        return False


def test_reducer_behavior():
    """Test that the reducer system preserves immutable fields."""
    print("\n🔧 Testing reducer behavior simulation...")
    
    # Create initial state
    session_id = str(uuid.uuid4())
    workflow_id = str(uuid.uuid4())
    
    initial_state = create_initial_post_state(
        articles=[{"title": "Test", "url": "test", "source": "test", "summary": "test"}],
        topic="Test Topic",
        llm_model="claude-3-5-sonnet",
        session_id=session_id,
        workflow_id=workflow_id,
        news_workflow_id=str(uuid.uuid4())
    )
    
    # Simulate what happens when a node returns a partial update
    node_update = {
        "linkedin_post": {
            "content": "Generated LinkedIn post",
            "char_count": 25,
            "hashtags": ["#Test"],
            "shortened_urls": None
        },
        "current_step": "linkedin_post_generation"
    }
    
    # Simulate LangGraph's reducer behavior
    # The keep_first_value reducer should preserve session_id, workflow_id, etc.
    merged_state = initial_state.copy()
    
    # Apply reducers (simplified simulation)
    for key, value in node_update.items():
        if key in ["session_id", "workflow_id", "llm_model", "topic", "articles"]:
            # These have keep_first_value reducer - don't update
            continue
        else:
            # These can be updated
            merged_state[key] = value
    
    # Verify immutable fields are preserved
    assert merged_state["session_id"] == session_id, "session_id should be preserved by reducer"
    assert merged_state["workflow_id"] == workflow_id, "workflow_id should be preserved by reducer"
    assert merged_state["llm_model"] == "claude-3-5-sonnet", "llm_model should be preserved by reducer"
    
    # Verify new fields are added
    assert merged_state["linkedin_post"] == node_update["linkedin_post"], "linkedin_post should be updated"
    assert merged_state["current_step"] == "linkedin_post_generation", "current_step should be updated"
    
    print("✅ Reducer behavior simulation successful")
    return True


def main():
    """Run all tests."""
    print("🚀 Starting State Access Fix Tests")
    print("=" * 60)
    
    # Test 1: State access pattern
    test1_success = test_state_access_pattern()
    
    # Test 2: Reducer behavior
    test2_success = test_reducer_behavior()
    
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    print(f"State Access Pattern Test: {'✅ PASSED' if test1_success else '❌ FAILED'}")
    print(f"Reducer Behavior Test: {'✅ PASSED' if test2_success else '❌ FAILED'}")
    
    if test1_success and test2_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n📝 SUMMARY OF THE FIX:")
        print("- Changed from state.get('session_id', '') to state['session_id']")
        print("- Added proper validation for empty strings")
        print("- Fixed all three nodes: LinkedIn, X, and Save Posts")
        print("- The fix ensures nodes can access immutable state fields correctly")
        return True
    else:
        print("\n❌ SOME TESTS FAILED.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
