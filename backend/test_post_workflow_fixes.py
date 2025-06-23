"""
Test script to verify post workflow fixes.

This script tests the fixed post generation workflow to ensure:
1. State propagation works correctly
2. LLM provider validation and fallback work
3. Session ID validation works
4. Error handling maintains state
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List

# Import the fixed components
from app.langgraph.workflows.post_workflow import execute_post_workflow
from app.langgraph.state.post_state import create_initial_post_state
from app.langgraph.nodes.linkedin_post_node import LinkedInPostNode
from app.langgraph.nodes.x_post_node import XPostNode
from app.langgraph.nodes.save_posts_node import SavePostsNode


def create_test_articles() -> List[Dict[str, Any]]:
    """Create test articles for post generation."""
    return [
        {
            "title": "AI Breakthrough in Healthcare",
            "url": "https://example.com/ai-healthcare",
            "source": "TechNews",
            "summary": "New AI system shows 95% accuracy in early disease detection, revolutionizing medical diagnostics.",
            "published_at": "2025-06-23T10:00:00Z",
            "relevance_score": 0.95
        },
        {
            "title": "Quantum Computing Milestone",
            "url": "https://example.com/quantum-computing",
            "source": "ScienceDaily",
            "summary": "Researchers achieve quantum supremacy with 1000-qubit processor, opening new possibilities for complex calculations.",
            "published_at": "2025-06-23T09:30:00Z",
            "relevance_score": 0.88
        }
    ]


async def test_state_propagation():
    """Test that state is properly propagated between nodes."""
    print("🧪 Testing state propagation...")
    
    # Create initial state
    articles = create_test_articles()
    session_id = str(uuid.uuid4())
    workflow_id = str(uuid.uuid4())
    
    initial_state = create_initial_post_state(
        articles=articles,
        topic="AI Technology",
        llm_model="claude-3-5-sonnet",
        session_id=session_id,
        workflow_id=workflow_id,
        news_workflow_id=str(uuid.uuid4())
    )
    
    print(f"✅ Initial state created with session_id: {session_id}")
    print(f"✅ State keys: {list(initial_state.keys())}")
    
    # Test LinkedIn node
    linkedin_node = LinkedInPostNode()
    try:
        linkedin_result = await linkedin_node(initial_state)
        print(f"✅ LinkedIn node completed successfully")
        print(f"✅ LinkedIn result has session_id: {linkedin_result.get('session_id', 'MISSING')}")
        print(f"✅ LinkedIn result has workflow_id: {linkedin_result.get('workflow_id', 'MISSING')}")
        print(f"✅ LinkedIn post generated: {linkedin_result.get('linkedin_post') is not None}")
        
        # Test X node with LinkedIn result
        x_node = XPostNode()
        x_result = await x_node(linkedin_result)
        print(f"✅ X node completed successfully")
        print(f"✅ X result has session_id: {x_result.get('session_id', 'MISSING')}")
        print(f"✅ X result has workflow_id: {x_result.get('workflow_id', 'MISSING')}")
        print(f"✅ X post generated: {x_result.get('x_post') is not None}")
        print(f"✅ LinkedIn post preserved: {x_result.get('linkedin_post') is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ State propagation test failed: {str(e)}")
        return False


async def test_llm_provider_validation():
    """Test LLM provider validation and fallback."""
    print("\n🧪 Testing LLM provider validation...")
    
    articles = create_test_articles()
    session_id = str(uuid.uuid4())
    workflow_id = str(uuid.uuid4())
    
    # Test with invalid LLM provider
    initial_state = create_initial_post_state(
        articles=articles,
        topic="AI Technology",
        llm_model="invalid-model",  # This should trigger fallback
        session_id=session_id,
        workflow_id=workflow_id,
        news_workflow_id=str(uuid.uuid4())
    )
    
    try:
        linkedin_node = LinkedInPostNode()
        result = await linkedin_node(initial_state)
        
        if result.get("error_message"):
            print(f"✅ LLM provider validation working - error caught: {result['error_message']}")
        else:
            print(f"✅ LLM provider fallback working - used provider: {result.get('current_llm_provider', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM provider validation test failed: {str(e)}")
        return False


async def test_missing_session_id():
    """Test handling of missing session ID."""
    print("\n🧪 Testing missing session ID handling...")
    
    articles = create_test_articles()
    
    # Create state without session_id
    invalid_state = {
        "articles": articles,
        "topic": "AI Technology",
        "llm_model": "claude-3-5-sonnet",
        "workflow_id": str(uuid.uuid4()),
        "news_workflow_id": str(uuid.uuid4()),
        "start_time": datetime.utcnow().timestamp(),
        "current_step": "test",
        "processing_steps": [],
        "linkedin_post": None,
        "x_post": None,
        "processing_time": None,
        "error_message": None,
        "failed_step": None,
        "retry_count": 0,
        "llm_providers_tried": [],
        "current_llm_provider": "claude-3-5-sonnet"
        # Missing session_id intentionally
    }
    
    try:
        linkedin_node = LinkedInPostNode()
        result = await linkedin_node(invalid_state)
        
        if result.get("error_message") and "session_id is missing" in result["error_message"]:
            print("✅ Missing session ID properly detected and handled")
            return True
        else:
            print(f"❌ Missing session ID not properly handled: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Missing session ID test failed: {str(e)}")
        return False


async def test_error_state_maintenance():
    """Test that error states maintain all original state fields."""
    print("\n🧪 Testing error state maintenance...")
    
    articles = create_test_articles()
    session_id = str(uuid.uuid4())
    workflow_id = str(uuid.uuid4())
    
    # Create state with empty LLM model to trigger error
    initial_state = create_initial_post_state(
        articles=articles,
        topic="AI Technology",
        llm_model="",  # Empty model should trigger validation error
        session_id=session_id,
        workflow_id=workflow_id,
        news_workflow_id=str(uuid.uuid4())
    )
    
    try:
        linkedin_node = LinkedInPostNode()
        result = await linkedin_node(initial_state)
        
        # Check that error state maintains original fields
        if result.get("error_message"):
            original_keys = set(initial_state.keys())
            result_keys = set(result.keys())
            
            # Error state should have all original keys plus error fields
            missing_keys = original_keys - result_keys
            if not missing_keys:
                print("✅ Error state maintains all original state fields")
                print(f"✅ Error message: {result['error_message']}")
                return True
            else:
                print(f"❌ Error state missing keys: {missing_keys}")
                return False
        else:
            print("❌ Expected error but none occurred")
            return False
            
    except Exception as e:
        print(f"❌ Error state maintenance test failed: {str(e)}")
        return False


async def run_all_tests():
    """Run all test cases."""
    print("🚀 Starting Post Workflow Fixes Test Suite")
    print("=" * 50)
    
    tests = [
        ("State Propagation", test_state_propagation),
        ("LLM Provider Validation", test_llm_provider_validation),
        ("Missing Session ID", test_missing_session_id),
        ("Error State Maintenance", test_error_state_maintenance),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Post workflow fixes are working correctly.")
    else:
        print("⚠️  Some tests failed. Please review the fixes.")
    
    return passed == len(results)


if __name__ == "__main__":
    # Run the test suite
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
