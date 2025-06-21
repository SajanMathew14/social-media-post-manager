"""
Test script to verify post generation fixes
"""
import asyncio
import httpx
import json
from datetime import datetime

# Test configuration
API_BASE_URL = "http://localhost:8000/api"

# Test data
TEST_SESSION_ID = "47a9cee0-8504-490b-9c64-843de41ce6b6"  # From the logs
TEST_ARTICLES = [
    {
        "title": "AI Breakthrough in Healthcare",
        "url": "https://example.com/ai-healthcare",
        "source": "TechNews",
        "summary": "New AI model can detect diseases with 95% accuracy",
        "published_at": "2024-01-21T10:00:00Z",
        "relevance_score": 0.95
    },
    {
        "title": "Tech Giants Invest in Green Energy",
        "url": "https://example.com/tech-green",
        "source": "BusinessDaily",
        "summary": "Major tech companies pledge $10B for renewable energy",
        "published_at": "2024-01-21T09:00:00Z",
        "relevance_score": 0.88
    }
]

async def test_post_generation():
    """Test the post generation endpoint"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n=== Testing Post Generation ===")
        print(f"Session ID: {TEST_SESSION_ID}")
        print(f"Articles: {len(TEST_ARTICLES)}")
        
        # Prepare request data
        request_data = {
            "articles": TEST_ARTICLES,
            "topic": "AI Technology",
            "llmModel": "claude-3-5-sonnet",
            "sessionId": TEST_SESSION_ID,
            "newsWorkflowId": "test-workflow-123"
        }
        
        print("\nSending POST request to /api/posts/generate...")
        print(f"Request data: {json.dumps(request_data, indent=2)}")
        
        try:
            # Send request
            response = await client.post(
                f"{API_BASE_URL}/posts/generate",
                json=request_data
            )
            
            print(f"\nResponse status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                print("\n✅ SUCCESS! Post generation completed")
                print(f"Workflow ID: {result.get('workflowId')}")
                print(f"Processing time: {result.get('processingTime')} seconds")
                print(f"LLM model used: {result.get('llmModelUsed')}")
                
                posts = result.get('posts', {})
                if 'linkedin' in posts:
                    print(f"\nLinkedIn post generated:")
                    print(f"- Character count: {posts['linkedin']['char_count']}")
                    print(f"- Hashtags: {posts['linkedin'].get('hashtags', [])}")
                    print(f"- Content preview: {posts['linkedin']['content'][:100]}...")
                
                if 'x' in posts:
                    print(f"\nX post generated:")
                    print(f"- Character count: {posts['x']['char_count']}")
                    print(f"- Hashtags: {posts['x'].get('hashtags', [])}")
                    print(f"- Content: {posts['x']['content']}")
                
            else:
                error_detail = response.json()
                print(f"\n❌ ERROR: {response.status_code}")
                print(f"Error type: {error_detail.get('error')}")
                print(f"Message: {error_detail.get('message')}")
                print(f"Details: {json.dumps(error_detail.get('details', {}), indent=2)}")
                
        except Exception as e:
            print(f"\n❌ Request failed: {type(e).__name__}: {str(e)}")

async def test_empty_session_id():
    """Test with empty session ID to verify our defensive checks"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n\n=== Testing Empty Session ID Handling ===")
        
        request_data = {
            "articles": TEST_ARTICLES,
            "topic": "AI Technology",
            "llmModel": "claude-3-5-sonnet",
            "sessionId": "",  # Empty session ID
            "newsWorkflowId": "test-workflow-123"
        }
        
        print("Sending request with empty session ID...")
        
        try:
            response = await client.post(
                f"{API_BASE_URL}/posts/generate",
                json=request_data
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                error_detail = response.json()
                print(f"✅ Correctly rejected empty session ID")
                print(f"Error: {error_detail.get('message')}")
            else:
                print("❌ ERROR: Request should have failed with empty session ID")
                
        except Exception as e:
            print(f"Request failed: {type(e).__name__}: {str(e)}")

async def test_invalid_llm_model():
    """Test with invalid LLM model"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n\n=== Testing Invalid LLM Model Handling ===")
        
        request_data = {
            "articles": TEST_ARTICLES,
            "topic": "AI Technology",
            "llmModel": "invalid-model",  # Invalid model
            "sessionId": TEST_SESSION_ID,
            "newsWorkflowId": "test-workflow-123"
        }
        
        print("Sending request with invalid LLM model...")
        
        try:
            response = await client.post(
                f"{API_BASE_URL}/posts/generate",
                json=request_data
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                error_detail = response.json()
                print(f"✅ Correctly rejected invalid LLM model")
                print(f"Error: {error_detail.get('message')}")
            else:
                print("❌ ERROR: Request should have failed with invalid LLM model")
                
        except Exception as e:
            print(f"Request failed: {type(e).__name__}: {str(e)}")

async def main():
    """Run all tests"""
    print("Starting post generation tests...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Run tests
    await test_post_generation()
    await test_empty_session_id()
    await test_invalid_llm_model()
    
    print("\n\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
