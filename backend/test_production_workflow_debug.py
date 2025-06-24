"""
Debug test to reproduce the exact production workflow issue.

This test simulates the exact production scenario to identify
why nodes are receiving empty session_id and workflow_id values.
"""
import asyncio
import uuid
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.langgraph.workflows.post_workflow import PostWorkflow
from app.langgraph.state.post_state import create_initial_post_state


async def test_production_workflow_debug():
    """Test the exact production workflow scenario."""
    print("🔍 Testing Production Workflow Debug")
    print("=" * 60)
    
    # Create test data matching production scenario
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
    
    print(f"Session ID: {session_id}")
    print(f"Workflow ID: {workflow_id}")
    print(f"News Workflow ID: {news_workflow_id}")
    
    try:
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
        
        print(f"✅ Initial state created successfully")
        print(f"   - session_id: {initial_state['session_id']}")
        print(f"   - workflow_id: {initial_state['workflow_id']}")
        print(f"   - llm_model: {initial_state['llm_model']}")
        print(f"   - topic: {initial_state['topic']}")
        print(f"   - articles count: {len(initial_state['articles'])}")
        
        # Test 2: Create workflow instance
        print("\n2️⃣ Testing workflow creation...")
        workflow = PostWorkflow()
        print("✅ Workflow created successfully")
        
        # Test 3: Execute workflow with detailed monitoring
        print("\n3️⃣ Executing workflow with debug monitoring...")
        print("   This will show exactly what state each node receives...")
        
        # Execute the workflow
        final_state = await workflow.execute(
            articles=test_articles,
            topic="AI Technology",
            llm_model="claude-3-5-sonnet",
            session_id=session_id,
            news_workflow_id=news_workflow_id
        )
        
        print("\n4️⃣ Workflow execution completed!")
        print(f"   - Final session_id: {final_state.get('session_id', 'MISSING')}")
        print(f"   - Final workflow_id: {final_state.get('workflow_id', 'MISSING')}")
        print(f"   - Current step: {final_state.get('current_step', 'MISSING')}")
        print(f"   - Has LinkedIn post: {final_state.get('linkedin_post') is not None}")
        print(f"   - Has X post: {final_state.get('x_post') is not None}")
        print(f"   - Error message: {final_state.get('error_message', 'None')}")
        
        # Test 4: Analyze processing steps
        print("\n5️⃣ Analyzing processing steps...")
        processing_steps = final_state.get('processing_steps', [])
        print(f"   - Total processing steps: {len(processing_steps)}")
        
        for i, step in enumerate(processing_steps):
            print(f"   - Step {i+1}: {step.get('step', 'unknown')} - {step.get('status', 'unknown')}")
            if step.get('message'):
                print(f"     Message: {step['message']}")
        
        # Check if workflow succeeded
        if final_state.get('error_message'):
            print(f"\n❌ WORKFLOW FAILED: {final_state['error_message']}")
            print(f"   Failed at step: {final_state.get('failed_step', 'unknown')}")
            return False
        else:
            print("\n✅ WORKFLOW SUCCEEDED!")
            return True
            
    except Exception as e:
        print(f"\n❌ WORKFLOW EXCEPTION: {str(e)}")
        print(f"   Exception type: {type(e).__name__}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False


async def test_individual_node_state_access():
    """Test individual nodes with different state scenarios."""
    print("\n" + "=" * 60)
    print("🔧 Testing Individual Node State Access")
    print("=" * 60)
    
    from app.langgraph.nodes.linkedin_post_node import LinkedInPostNode
    from app.langgraph.nodes.x_post_node import XPostNode
    from app.langgraph.nodes.save_posts_node import SavePostsNode
    
    # Create test state
    session_id = str(uuid.uuid4())
    workflow_id = str(uuid.uuid4())
    
    full_state = create_initial_post_state(
        articles=[{
            "title": "Test Article",
            "url": "https://example.com/test",
            "source": "TestSource",
            "summary": "Test summary",
            "published_at": "2025-06-23T14:00:00Z",
            "relevance_score": 0.8
        }],
        topic="Test Topic",
        llm_model="claude-3-5-sonnet",
        session_id=session_id,
        workflow_id=workflow_id,
        news_workflow_id=str(uuid.uuid4())
    )
    
    print(f"Full state session_id: {full_state['session_id']}")
    print(f"Full state workflow_id: {full_state['workflow_id']}")
    
    # Test 1: LinkedIn node with full state
    print("\n1️⃣ Testing LinkedIn node with full state...")
    try:
        linkedin_node = LinkedInPostNode()
        linkedin_result = await linkedin_node(full_state)
        print("✅ LinkedIn node succeeded with full state")
        print(f"   - Result session_id: {linkedin_result.get('session_id', 'MISSING')}")
        print(f"   - Result workflow_id: {linkedin_result.get('workflow_id', 'MISSING')}")
    except Exception as e:
        print(f"❌ LinkedIn node failed: {str(e)}")
    
    # Test 2: Simulate partial state (what might be happening in production)
    print("\n2️⃣ Testing with partial state (simulating production issue)...")
    partial_state = {
        "linkedin_post": {
            "content": "Test LinkedIn post",
            "char_count": 18,
            "hashtags": ["#Test"],
            "shortened_urls": None
        },
        "current_step": "linkedin_post_generation",
        "processing_steps": []
    }
    
    print(f"Partial state keys: {list(partial_state.keys())}")
    print(f"Partial state session_id: {partial_state.get('session_id', 'MISSING')}")
    
    try:
        x_node = XPostNode()
        x_result = await x_node(partial_state)
        print("❌ X node should have failed with partial state but didn't!")
    except Exception as e:
        print(f"✅ X node correctly failed with partial state: {str(e)}")
    
    # Test 3: Test with merged state (what should happen with reducers)
    print("\n3️⃣ Testing with merged state (what reducers should provide)...")
    merged_state = full_state.copy()
    merged_state.update(partial_state)
    
    print(f"Merged state session_id: {merged_state['session_id']}")
    print(f"Merged state workflow_id: {merged_state['workflow_id']}")
    
    try:
        x_node = XPostNode()
        x_result = await x_node(merged_state)
        print("✅ X node succeeded with merged state")
        print(f"   - Result session_id: {x_result.get('session_id', 'MISSING')}")
        print(f"   - Result workflow_id: {x_result.get('workflow_id', 'MISSING')}")
    except Exception as e:
        print(f"❌ X node failed with merged state: {str(e)}")


async def main():
    """Run all debug tests."""
    print("🚀 Starting Production Workflow Debug Tests")
    print("=" * 80)
    
    # Test 1: Full workflow execution
    workflow_success = await test_production_workflow_debug()
    
    # Test 2: Individual node testing
    await test_individual_node_state_access()
    
    print("\n" + "=" * 80)
    print("📋 DEBUG TEST SUMMARY")
    print("=" * 80)
    print(f"Full Workflow Test: {'✅ PASSED' if workflow_success else '❌ FAILED'}")
    
    if not workflow_success:
        print("\n🔍 DIAGNOSIS:")
        print("The workflow is failing in production, which suggests:")
        print("1. Nodes are receiving partial state instead of full accumulated state")
        print("2. LangGraph reducers may not be working as expected")
        print("3. There might be a version compatibility issue")
        print("4. The state propagation between nodes is broken")
        
        print("\n💡 RECOMMENDED ACTIONS:")
        print("1. Check LangGraph version compatibility")
        print("2. Verify reducer implementations")
        print("3. Add more detailed logging to nodes")
        print("4. Consider using explicit state merging")
    
    return workflow_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
