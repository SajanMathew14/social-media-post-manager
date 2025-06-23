"""
Test script to verify LangGraph 0.4.8 state reducers are working correctly.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List

# Test the state creation and reducer functions directly
from app.langgraph.state.post_state import (
    PostState, 
    create_initial_post_state,
    keep_first_value,
    use_latest_value,
    add_processing_steps,
    PostGenerationStatus
)


def test_reducer_functions():
    """Test that our custom reducer functions work correctly."""
    
    print("🧪 Testing Custom Reducer Functions")
    print("=" * 50)
    
    # Test keep_first_value reducer
    print("1. Testing keep_first_value reducer...")
    original_session_id = "original-session-123"
    new_session_id = "new-session-456"
    
    result = keep_first_value(original_session_id, new_session_id)
    print(f"   Original: {original_session_id}")
    print(f"   New: {new_session_id}")
    print(f"   Result: {result}")
    
    if result == original_session_id:
        print("   ✅ keep_first_value works correctly")
    else:
        print("   ❌ keep_first_value failed!")
        return False
    
    # Test use_latest_value reducer
    print("\n2. Testing use_latest_value reducer...")
    original_step = "step1"
    new_step = "step2"
    
    result = use_latest_value(original_step, new_step)
    print(f"   Original: {original_step}")
    print(f"   New: {new_step}")
    print(f"   Result: {result}")
    
    if result == new_step:
        print("   ✅ use_latest_value works correctly")
    else:
        print("   ❌ use_latest_value failed!")
        return False
    
    # Test add_processing_steps reducer
    print("\n3. Testing add_processing_steps reducer...")
    original_steps = [
        {
            "step": "step1",
            "status": PostGenerationStatus.COMPLETED,
            "message": "First step",
            "timestamp": datetime.utcnow().isoformat()
        }
    ]
    
    new_steps = [
        {
            "step": "step2", 
            "status": PostGenerationStatus.COMPLETED,
            "message": "Second step",
            "timestamp": datetime.utcnow().isoformat()
        }
    ]
    
    result = add_processing_steps(original_steps, new_steps)
    print(f"   Original steps count: {len(original_steps)}")
    print(f"   New steps count: {len(new_steps)}")
    print(f"   Result steps count: {len(result)}")
    
    if len(result) == len(original_steps) + len(new_steps):
        print("   ✅ add_processing_steps works correctly")
    else:
        print("   ❌ add_processing_steps failed!")
        return False
    
    return True


def test_state_creation():
    """Test that initial state creation works correctly."""
    
    print("\n🏗️  Testing State Creation")
    print("=" * 50)
    
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
    
    print(f"Creating initial state...")
    print(f"   Session ID: {session_id}")
    print(f"   Workflow ID: {workflow_id}")
    
    try:
        initial_state = create_initial_post_state(
            articles=articles,
            topic="AI Technology",
            llm_model="claude-3-5-haiku",
            session_id=session_id,
            workflow_id=workflow_id,
            news_workflow_id=news_workflow_id
        )
        
        print(f"   ✅ State created successfully")
        print(f"   📊 State keys: {list(initial_state.keys())}")
        print(f"   📊 Session ID in state: {initial_state.get('session_id')}")
        print(f"   📊 Workflow ID in state: {initial_state.get('workflow_id')}")
        print(f"   📊 Topic in state: {initial_state.get('topic')}")
        print(f"   📊 Articles count: {len(initial_state.get('articles', []))}")
        
        # Verify all required fields are present
        required_fields = [
            'session_id', 'workflow_id', 'articles', 'topic', 'llm_model',
            'news_workflow_id', 'start_time', 'current_step', 'processing_steps'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in initial_state:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"   ❌ Missing required fields: {missing_fields}")
            return False, None
        else:
            print(f"   ✅ All required fields present")
            return True, initial_state
            
    except Exception as e:
        print(f"   ❌ State creation failed: {e}")
        return False, None


def test_state_update_simulation():
    """Simulate how LangGraph would handle state updates with reducers."""
    
    print("\n🔄 Testing State Update Simulation")
    print("=" * 50)
    
    # Get initial state
    success, initial_state = test_state_creation()
    if not success:
        return False
    
    print(f"\nSimulating node partial updates...")
    
    # Simulate what LinkedIn node would return (partial update)
    linkedin_partial_update = {
        "linkedin_post": {
            "content": "🚀 Exciting AI breakthrough in medical diagnostics! New system achieves 95% accuracy in early cancer detection. This could revolutionize healthcare screening. #AI #HealthTech #Innovation",
            "char_count": 180,
            "hashtags": ["#AI", "#HealthTech", "#Innovation"],
            "shortened_urls": None
        },
        "current_step": "linkedin_post_generation",
        "current_llm_provider": "claude-3-5-haiku",
        "processing_steps": [
            {
                "step": "linkedin_post_generation",
                "status": PostGenerationStatus.COMPLETED,
                "message": "Generated LinkedIn post with 180 characters",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }
    
    print(f"   📤 LinkedIn partial update keys: {list(linkedin_partial_update.keys())}")
    print(f"   📤 Contains session_id: {'session_id' in linkedin_partial_update}")
    print(f"   📤 Contains workflow_id: {'workflow_id' in linkedin_partial_update}")
    
    # Manually apply reducers (simulating what LangGraph should do)
    print(f"\n   🔧 Manually applying reducers...")
    
    merged_state = initial_state.copy()
    
    # Apply each field with its appropriate reducer
    for key, value in linkedin_partial_update.items():
        if key == "processing_steps":
            # Use add_processing_steps reducer
            merged_state[key] = add_processing_steps(
                merged_state.get(key, []), 
                value
            )
        elif key in ["current_step", "current_llm_provider", "linkedin_post"]:
            # Use use_latest_value reducer (or equivalent)
            merged_state[key] = value
        # session_id, workflow_id, etc. should be preserved by keep_first_value
        # (they're not in the partial update, so they remain unchanged)
    
    print(f"   ✅ Manual merge completed")
    print(f"   📊 Merged state session_id: {merged_state.get('session_id')}")
    print(f"   📊 Merged state workflow_id: {merged_state.get('workflow_id')}")
    print(f"   📊 Merged state current_step: {merged_state.get('current_step')}")
    print(f"   📊 Merged state has LinkedIn post: {merged_state.get('linkedin_post') is not None}")
    print(f"   📊 Processing steps count: {len(merged_state.get('processing_steps', []))}")
    
    # Check if critical fields are preserved
    if merged_state.get('session_id') == initial_state.get('session_id'):
        print(f"   ✅ Session ID preserved correctly")
    else:
        print(f"   ❌ Session ID lost during merge!")
        return False
    
    if merged_state.get('workflow_id') == initial_state.get('workflow_id'):
        print(f"   ✅ Workflow ID preserved correctly")
    else:
        print(f"   ❌ Workflow ID lost during merge!")
        return False
    
    return True


def main():
    """Run all tests."""
    
    print("🔍 LangGraph 0.4.8 State Reducer Testing")
    print("=" * 60)
    
    # Test 1: Reducer functions
    if not test_reducer_functions():
        print("\n❌ REDUCER FUNCTIONS TEST FAILED")
        return
    
    # Test 2: State creation  
    success, _ = test_state_creation()
    if not success:
        print("\n❌ STATE CREATION TEST FAILED")
        return
    
    # Test 3: State update simulation
    if not test_state_update_simulation():
        print("\n❌ STATE UPDATE SIMULATION TEST FAILED")
        return
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSIS SUMMARY")
    print("=" * 60)
    print("✅ All reducer functions work correctly")
    print("✅ State creation works correctly")
    print("✅ Manual state merging preserves session_id")
    print("")
    print("🔍 CONCLUSION:")
    print("The issue is likely NOT with our reducer functions or state definition.")
    print("The problem appears to be in how LangGraph 0.4.8 applies the reducers")
    print("when nodes return partial updates in the actual workflow execution.")
    print("")
    print("💡 NEXT STEPS:")
    print("1. Check if nodes need to return PostState type instead of dict")
    print("2. Verify LangGraph workflow compilation is using our state schema")
    print("3. Test with actual LangGraph workflow execution")


if __name__ == "__main__":
    main()
