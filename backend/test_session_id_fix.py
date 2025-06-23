"""
Test script to debug the session_id missing issue in post generation workflow.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List

from app.langgraph.state.post_state import PostState, create_initial_post_state
from app.langgraph.nodes.linkedin_post_node import LinkedInPostNode
from app.langgraph.nodes.x_post_node import XPostNode
from app.langgraph.nodes.save_posts_node import SavePostsNode


async def test_state_propagation():
    """Test that session_id is properly propagated through all nodes."""
    
    # Create test data
    session_id = str(uuid.uuid4())
    workflow_id = str(uuid.uuid4())
    news_workflow_id = str(uuid.uuid4())
    
    articles = [
        {
            "title": "AI Breakthrough in Medical Diagnostics",
            "url": "https://techcrunch.com/ai-medical-breakthrough",
            "source": "TechCrunch",
            "summary": "New AI system achieves 95% accuracy in early cancer detection.",
            "published_at": "2025-06-23T10:00:00Z",
            "relevance_score": 0.95
        }
    ]
    
    print(f"🔍 Testing session_id propagation")
    print(f"Session ID: {session_id}")
    print(f"Workflow ID: {workflow_id}")
    print("-" * 60)
    
    # Create initial state
    print("1. Creating initial state...")
    initial_state = create_initial_post_state(
        articles=articles,
        topic="AI Technology",
        llm_model="claude-3-5-haiku",  # Use faster model for testing
        session_id=session_id,
        workflow_id=workflow_id,
        news_workflow_id=news_workflow_id
    )
    
    print(f"   ✅ Initial state session_id: {initial_state.get('session_id')}")
    print(f"   ✅ Initial state workflow_id: {initial_state.get('workflow_id')}")
    print(f"   ✅ Initial state keys: {list(initial_state.keys())}")
    
    # Test LinkedIn node
    print("\n2. Testing LinkedIn post node...")
    linkedin_node = LinkedInPostNode()
    
    try:
        linkedin_result = await linkedin_node(initial_state)
        print(f"   ✅ LinkedIn node completed")
        print(f"   📊 Result type: {type(linkedin_result)}")
        print(f"   📊 Result keys: {list(linkedin_result.keys())}")
        print(f"   📊 Session ID in result: {linkedin_result.get('session_id')}")
        print(f"   📊 Workflow ID in result: {linkedin_result.get('workflow_id')}")
        print(f"   📊 Has LinkedIn post: {linkedin_result.get('linkedin_post') is not None}")
        
        # Check if this is a partial update or full state
        if len(linkedin_result.keys()) < len(initial_state.keys()):
            print(f"   ⚠️  This appears to be a partial update (expected for LangGraph 0.4.8)")
            print(f"   ⚠️  Missing keys that should be preserved by reducers:")
            missing_keys = set(initial_state.keys()) - set(linkedin_result.keys())
            for key in missing_keys:
                print(f"      - {key}")
        
    except Exception as e:
        print(f"   ❌ LinkedIn node failed: {e}")
        return
    
    # Test X post node with LinkedIn result
    print("\n3. Testing X post node...")
    x_node = XPostNode()
    
    try:
        # For testing, we need to simulate what LangGraph would do:
        # merge the partial update back into the full state
        merged_state = initial_state.copy()
        merged_state.update(linkedin_result)
        
        print(f"   📊 Merged state session_id: {merged_state.get('session_id')}")
        print(f"   📊 Merged state workflow_id: {merged_state.get('workflow_id')}")
        
        x_result = await x_node(merged_state)
        print(f"   ✅ X node completed")
        print(f"   📊 Result type: {type(x_result)}")
        print(f"   📊 Result keys: {list(x_result.keys())}")
        print(f"   📊 Session ID in result: {x_result.get('session_id')}")
        print(f"   📊 Workflow ID in result: {x_result.get('workflow_id')}")
        print(f"   📊 Has X post: {x_result.get('x_post') is not None}")
        
    except Exception as e:
        print(f"   ❌ X node failed: {e}")
        return
    
    # Test Save posts node
    print("\n4. Testing Save posts node...")
    save_node = SavePostsNode()
    
    try:
        # Merge X result into state
        final_merged_state = merged_state.copy()
        final_merged_state.update(x_result)
        
        print(f"   📊 Final merged state session_id: {final_merged_state.get('session_id')}")
        print(f"   📊 Final merged state workflow_id: {final_merged_state.get('workflow_id')}")
        
        save_result = await save_node(final_merged_state)
        print(f"   ✅ Save node completed")
        print(f"   📊 Result type: {type(save_result)}")
        print(f"   📊 Result keys: {list(save_result.keys())}")
        print(f"   📊 Session ID in result: {save_result.get('session_id')}")
        print(f"   📊 Has error: {save_result.get('error_message') is not None}")
        
        if save_result.get('error_message'):
            print(f"   ❌ Save error: {save_result.get('error_message')}")
        
    except Exception as e:
        print(f"   ❌ Save node failed: {e}")
        return
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSIS:")
    print("=" * 60)
    
    # Check if the issue is with partial updates
    if linkedin_result.get('session_id') is None:
        print("❌ ISSUE FOUND: LinkedIn node returns partial update without session_id")
        print("   This suggests the LangGraph reducers are not working as expected")
        print("   The keep_first_value reducer should preserve session_id")
    
    if x_result.get('session_id') is None:
        print("❌ ISSUE FOUND: X node returns partial update without session_id")
        print("   This suggests the LangGraph reducers are not working as expected")
    
    if final_merged_state.get('session_id') is None:
        print("❌ CRITICAL ISSUE: session_id lost during state merging")
        print("   This is why the save_posts_node fails")
    else:
        print("✅ Session ID preserved through manual merging")
        print("   The issue is likely in how LangGraph handles the reducers")


if __name__ == "__main__":
    asyncio.run(test_state_propagation())
