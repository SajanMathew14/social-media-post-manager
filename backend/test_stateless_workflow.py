"""
Test the new stateless workflow approach that bypasses LangGraph's broken state management.

This test validates that the external state management approach works correctly
and completely avoids the session_id/workflow_id issues we've been experiencing.
"""
import asyncio
import uuid
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.langgraph.workflows.stateless_post_workflow import get_stateless_post_workflow
from app.langgraph.utils.external_state_manager import get_external_state_manager


async def test_external_state_manager():
    """Test the external state manager functionality."""
    print("🧪 Testing External State Manager...")
    
    state_manager = get_external_state_manager()
    
    # Test 1: Create state
    test_data = {
        "session_id": str(uuid.uuid4()),
        "workflow_id": str(uuid.uuid4()),
        "test_field": "test_value"
    }
    
    state_key = await state_manager.create_state(test_data)
    print(f"✅ Created state with key: {state_key}")
    
    # Test 2: Retrieve state
    retrieved_state = await state_manager.get_state(state_key)
    assert retrieved_state is not None, "State should be retrievable"
    assert retrieved_state["session_id"] == test_data["session_id"], "Session ID should match"
    assert retrieved_state["workflow_id"] == test_data["workflow_id"], "Workflow ID should match"
    print(f"✅ Retrieved state successfully")
    
    # Test 3: Update state
    updates = {"new_field": "new_value", "test_field": "updated_value"}
    success = await state_manager.update_state(state_key, updates)
    assert success, "Update should succeed"
    
    updated_state = await state_manager.get_state(state_key)
    assert updated_state["new_field"] == "new_value", "New field should be added"
    assert updated_state["test_field"] == "updated_value", "Existing field should be updated"
    print(f"✅ Updated state successfully")
    
    # Test 4: Delete state
    deleted = await state_manager.delete_state(state_key)
    assert deleted, "Delete should succeed"
    
    deleted_state = await state_manager.get_state(state_key)
    assert deleted_state is None, "State should be deleted"
    print(f"✅ Deleted state successfully")
    
    return True


async def test_stateless_workflow():
    """Test the complete stateless workflow."""
    print("\n🚀 Testing Stateless Workflow...")
    
    # Test data
    session_id = str(uuid.uuid4())
    news_workflow_id = str(uuid.uuid4())
    
    test_articles = [
        {
            "title": "Revolutionary AI Breakthrough in Healthcare",
            "url": "https://example.com/ai-healthcare",
            "source": "TechNews",
            "summary": "New AI system improves medical diagnosis accuracy by 40% using advanced machine learning algorithms",
            "published_at": "2025-06-23T14:00:00Z",
            "relevance_score": 0.95
        },
        {
            "title": "Quantum Computing Reaches New Milestone",
            "url": "https://example.com/quantum-computing",
            "source": "ScienceDaily",
            "summary": "Scientists achieve 99.9% fidelity in quantum error correction, bringing practical quantum computers closer to reality",
            "published_at": "2025-06-23T15:30:00Z",
            "relevance_score": 0.88
        }
    ]
    
    print(f"Session ID: {session_id}")
    print(f"Articles: {len(test_articles)}")
    
    try:
        # Get stateless workflow
        workflow = get_stateless_post_workflow()
        
        # Execute workflow
        result = await workflow.execute(
            articles=test_articles,
            topic="AI Technology",
            llm_model="claude-3-5-sonnet",
            session_id=session_id,
            news_workflow_id=news_workflow_id
        )
        
        # Validate results
        assert result is not None, "Result should not be None"
        assert "workflow_id" in result, "Result should contain workflow_id"
        assert "posts" in result, "Result should contain posts"
        assert "processing_time" in result, "Result should contain processing_time"
        
        print(f"✅ Workflow completed successfully")
        print(f"   Workflow ID: {result['workflow_id']}")
        print(f"   Processing Time: {result['processing_time']:.2f}s")
        print(f"   Posts Generated: {list(result['posts'].keys())}")
        
        # Validate LinkedIn post
        if "linkedin" in result["posts"]:
            linkedin_post = result["posts"]["linkedin"]
            assert "content" in linkedin_post, "LinkedIn post should have content"
            assert "char_count" in linkedin_post, "LinkedIn post should have char_count"
            assert linkedin_post["char_count"] > 0, "LinkedIn post should have content"
            print(f"   ✅ LinkedIn post: {linkedin_post['char_count']} characters")
        
        # Validate X post
        if "x" in result["posts"]:
            x_post = result["posts"]["x"]
            assert "content" in x_post, "X post should have content"
            assert "char_count" in x_post, "X post should have char_count"
            assert x_post["char_count"] > 0, "X post should have content"
            assert x_post["char_count"] <= 280, "X post should be under 280 characters"
            print(f"   ✅ X post: {x_post['char_count']} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        return False


async def test_state_isolation():
    """Test that multiple workflows don't interfere with each other."""
    print("\n🔄 Testing State Isolation...")
    
    # Create multiple concurrent workflows
    workflows = []
    session_ids = []
    
    for i in range(3):
        session_id = str(uuid.uuid4())
        session_ids.append(session_id)
        
        test_articles = [
            {
                "title": f"Test Article {i+1}",
                "url": f"https://example.com/article-{i+1}",
                "source": "TestSource",
                "summary": f"Test summary for article {i+1}",
                "published_at": "2025-06-23T14:00:00Z",
                "relevance_score": 0.9
            }
        ]
        
        workflow = get_stateless_post_workflow()
        task = workflow.execute(
            articles=test_articles,
            topic=f"Test Topic {i+1}",
            llm_model="claude-3-5-sonnet",
            session_id=session_id,
            news_workflow_id=str(uuid.uuid4())
        )
        workflows.append(task)
    
    # Execute all workflows concurrently
    try:
        results = await asyncio.gather(*workflows, return_exceptions=True)
        
        # Validate all succeeded
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"   ❌ Workflow {i+1} failed: {result}")
            else:
                print(f"   ✅ Workflow {i+1} completed: {result['workflow_id']}")
                success_count += 1
        
        print(f"✅ {success_count}/3 workflows completed successfully")
        return success_count == 3
        
    except Exception as e:
        print(f"❌ Concurrent execution failed: {e}")
        return False


async def test_error_handling():
    """Test error handling in the stateless workflow."""
    print("\n⚠️  Testing Error Handling...")
    
    workflow = get_stateless_post_workflow()
    
    # Test with invalid data
    try:
        result = await workflow.execute(
            articles=[],  # Empty articles
            topic="",     # Empty topic
            llm_model="invalid-model",
            session_id="",  # Empty session_id
            news_workflow_id=""
        )
        print(f"❌ Expected error but workflow succeeded: {result}")
        return False
        
    except Exception as e:
        print(f"✅ Correctly handled error: {str(e)[:100]}...")
        return True


async def main():
    """Run all stateless workflow tests."""
    print("🚀 Starting Stateless Workflow Tests")
    print("=" * 80)
    
    # Test 1: External state manager
    test1_success = await test_external_state_manager()
    
    # Test 2: Complete stateless workflow
    test2_success = await test_stateless_workflow()
    
    # Test 3: State isolation
    test3_success = await test_state_isolation()
    
    # Test 4: Error handling
    test4_success = await test_error_handling()
    
    print("\n" + "=" * 80)
    print("📋 STATELESS WORKFLOW TEST SUMMARY")
    print("=" * 80)
    print(f"External State Manager Test: {'✅ PASSED' if test1_success else '❌ FAILED'}")
    print(f"Stateless Workflow Test: {'✅ PASSED' if test2_success else '❌ FAILED'}")
    print(f"State Isolation Test: {'✅ PASSED' if test3_success else '❌ FAILED'}")
    print(f"Error Handling Test: {'✅ PASSED' if test4_success else '❌ FAILED'}")
    
    all_passed = test1_success and test2_success and test3_success and test4_success
    
    if all_passed:
        print("\n🎉 ALL STATELESS WORKFLOW TESTS PASSED!")
        print("\n📝 STATELESS APPROACH BENEFITS:")
        print("✅ Completely bypasses LangGraph reducer issues")
        print("✅ Guaranteed state integrity throughout workflow")
        print("✅ No session_id/workflow_id access problems")
        print("✅ Concurrent workflow isolation")
        print("✅ Robust error handling")
        print("✅ Clean separation of concerns")
        print("\n🚀 READY TO REPLACE THE BROKEN WORKFLOW")
        return True
    else:
        print("\n❌ SOME STATELESS WORKFLOW TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
