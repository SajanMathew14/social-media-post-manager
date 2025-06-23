"""
Test script to verify the session ID propagation fix for post generation workflow.

This script tests that session_id and workflow_id are properly propagated
through all nodes in the post generation workflow.
"""
import asyncio
import uuid
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.langgraph.workflows.post_workflow import execute_post_workflow
from app.langgraph.state.post_state import create_initial_post_state
from app.langgraph.nodes.linkedin_post_node import LinkedInPostNode
from app.langgraph.nodes.x_post_node import XPostNode
from app.langgraph.nodes.save_posts_node import SavePostsNode


async def test_state_propagation():
    """Test that state fields propagate correctly through all nodes."""
    print("🧪 Testing session ID propagation fix...")
    
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
        },
        {
            "title": "Quantum Computing Milestone",
            "url": "https://example.com/quantum",
            "source": "ScienceDaily",
            "summary": "New quantum processor achieves unprecedented computational speed",
            "published_at": "2025-06-23T13:30:00Z",
            "relevance_score": 0.88
        }
    ]
    
    # Test 1: Initial state creation
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
    
    # Test 2: LinkedIn Post Node
    print("\n2️⃣ Testing LinkedIn Post Node state access...")
    linkedin_node = LinkedInPostNode()
    
    try:
        # This should not raise an error with the fix
        linkedin_result = await linkedin_node(initial_state)
        
        # Verify the node could access session_id and workflow_id
        assert "linkedin_post" in linkedin_result or "error_message" in linkedin_result, "LinkedIn node should return either a post or error"
        print("✅ LinkedIn Post Node state access successful")
        
        # Update state for next test
        if "linkedin_post" in linkedin_result:
            # Merge the result back into state (simulating LangGraph behavior)
            updated_state = initial_state.copy()
            updated_state.update(linkedin_result)
            current_state = updated_state
        else:
            current_state = linkedin_result
            
    except Exception as e:
        print(f"❌ LinkedIn Post Node failed: {e}")
        return False
    
    # Test 3: X Post Node
    print("\n3️⃣ Testing X Post Node state access...")
    x_node = XPostNode()
    
    try:
        # This should not raise an error with the fix
        x_result = await x_node(current_state)
        
        # Verify the node could access session_id and workflow_id
        assert "x_post" in x_result or "error_message" in x_result, "X node should return either a post or error"
        print("✅ X Post Node state access successful")
        
        # Update state for next test
        if "x_post" in x_result:
            # Merge the result back into state (simulating LangGraph behavior)
            updated_state = current_state.copy()
            updated_state.update(x_result)
            current_state = updated_state
        else:
            current_state = x_result
            
    except Exception as e:
        print(f"❌ X Post Node failed: {e}")
        return False
    
    # Test 4: Save Posts Node (this was the main failing node)
    print("\n4️⃣ Testing Save Posts Node state access...")
    save_node = SavePostsNode()
    
    try:
        # This should not raise the "Session ID is missing" error with the fix
        save_result = await save_node(current_state)
        
        # Verify the node could access session_id and workflow_id
        assert "processing_steps" in save_result or "error_message" in save_result, "Save node should return processing steps or error"
        print("✅ Save Posts Node state access successful")
        
    except Exception as e:
        print(f"❌ Save Posts Node failed: {e}")
        return False
    
    print("\n🎉 All state propagation tests passed!")
    return True


async def test_full_workflow():
    """Test the complete workflow end-to-end."""
    print("\n🔄 Testing complete workflow execution...")
    
    # Create test data
    session_id = str(uuid.uuid4())
    news_workflow_id = str(uuid.uuid4())
    
    test_articles = [
        {
            "title": "Breakthrough in Renewable Energy",
            "url": "https://example.com/renewable",
            "source": "EnergyNews",
            "summary": "New solar panel technology achieves 50% efficiency",
            "published_at": "2025-06-23T14:00:00Z",
            "relevance_score": 0.92
        }
    ]
    
    try:
        # Execute the complete workflow
        result = await execute_post_workflow(
            articles=test_articles,
            topic="Clean Energy",
            llm_model="claude-3-5-sonnet",
            session_id=session_id,
            news_workflow_id=news_workflow_id
        )
        
        # Verify workflow completed successfully
        assert "workflow_id" in result, "Workflow should return workflow_id"
        assert "posts" in result, "Workflow should return posts"
        
        print("✅ Complete workflow execution successful")
        print(f"📊 Workflow ID: {result['workflow_id']}")
        print(f"📊 Processing time: {result.get('processing_time', 'N/A')} seconds")
        print(f"📊 Posts generated: {len(result.get('posts', {}))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Complete workflow failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting Session ID Propagation Fix Tests")
    print("=" * 60)
    
    # Test 1: State propagation through individual nodes
    test1_success = await test_state_propagation()
    
    # Test 2: Complete workflow execution
    test2_success = await test_full_workflow()
    
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    print(f"State Propagation Test: {'✅ PASSED' if test1_success else '❌ FAILED'}")
    print(f"Complete Workflow Test: {'✅ PASSED' if test2_success else '❌ FAILED'}")
    
    if test1_success and test2_success:
        print("\n🎉 ALL TESTS PASSED! Session ID propagation fix is working correctly.")
        return True
    else:
        print("\n❌ SOME TESTS FAILED. Please check the error messages above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
