#!/usr/bin/env python3
"""
Test script to verify backend fixes for post generation errors.
"""
import asyncio
import aiohttp
import json
import sys
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000/api"

# Test data
TEST_SESSION_ID = None  # Will be created during test
TEST_TOPIC = "AI"
TEST_ARTICLES = [
    {
        "title": "OpenAI Announces GPT-5 Development",
        "url": "https://example.com/gpt5",
        "source": "TechCrunch",
        "summary": "OpenAI has announced the development of GPT-5, promising significant improvements in reasoning and multimodal capabilities.",
        "published_at": "2024-01-19T10:00:00Z",
        "relevance_score": 0.95
    },
    {
        "title": "Google's Gemini Pro Beats GPT-4 in Benchmarks",
        "url": "https://example.com/gemini",
        "source": "The Verge",
        "summary": "Google's latest Gemini Pro model has shown superior performance in several key benchmarks, challenging OpenAI's dominance.",
        "published_at": "2024-01-19T09:00:00Z",
        "relevance_score": 0.92
    }
]


async def create_session():
    """Create a test session."""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/sessions/create") as response:
            if response.status == 200:
                data = await response.json()
                return data["sessionId"]
            else:
                print(f"Failed to create session: {response.status}")
                text = await response.text()
                print(f"Response: {text}")
                return None


async def test_post_generation_without_api_keys():
    """Test post generation without API keys configured."""
    print("\n=== Testing Post Generation Without API Keys ===")
    
    # Create session
    session_id = await create_session()
    if not session_id:
        print("❌ Failed to create session")
        return False
    
    print(f"✅ Created session: {session_id}")
    
    # Try to generate posts
    async with aiohttp.ClientSession() as session:
        payload = {
            "articles": TEST_ARTICLES,
            "topic": TEST_TOPIC,
            "llmModel": "claude-3-5-sonnet",
            "sessionId": session_id,
            "newsWorkflowId": "test-workflow-123"
        }
        
        async with session.post(
            f"{BASE_URL}/posts/generate",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            data = await response.json()
            
            if response.status == 400:
                # Expected error when no API keys are configured
                if "No LLM providers configured" in data.get("message", ""):
                    print("✅ Correctly detected missing LLM providers")
                    print(f"   Error message: {data['message']}")
                    print(f"   Details: {json.dumps(data.get('details', {}), indent=2)}")
                    return True
                else:
                    print(f"❌ Unexpected 400 error: {data}")
                    return False
            elif response.status == 200:
                print("❌ Post generation succeeded when it should have failed")
                print(f"   Response: {json.dumps(data, indent=2)}")
                return False
            else:
                print(f"❌ Unexpected status code: {response.status}")
                print(f"   Response: {json.dumps(data, indent=2)}")
                return False


async def test_news_fetch():
    """Test that news fetch still works correctly."""
    print("\n=== Testing News Fetch (Should Still Work) ===")
    
    # Create session
    session_id = await create_session()
    if not session_id:
        print("❌ Failed to create session")
        return False
    
    print(f"✅ Created session: {session_id}")
    
    # Fetch news
    async with aiohttp.ClientSession() as session:
        payload = {
            "topic": TEST_TOPIC,
            "articleCount": 5,
            "llmModel": "claude-3-5-sonnet",
            "sessionId": session_id
        }
        
        async with session.post(
            f"{BASE_URL}/news/fetch",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 200:
                data = await response.json()
                print("✅ News fetch succeeded")
                print(f"   Workflow ID: {data.get('workflowId')}")
                print(f"   Articles found: {data.get('articlesFound', 0)}")
                return True
            else:
                print(f"❌ News fetch failed: {response.status}")
                text = await response.text()
                print(f"   Response: {text}")
                return False


async def main():
    """Run all tests."""
    print("Starting backend fix verification tests...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"API Base URL: {BASE_URL}")
    
    # Check if backend is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/health") as response:
                if response.status != 200:
                    print("\n❌ Backend is not running or not healthy")
                    print("Please start the backend with: cd backend && uvicorn app.main:app --reload")
                    return
    except aiohttp.ClientConnectorError:
        print("\n❌ Cannot connect to backend")
        print("Please start the backend with: cd backend && uvicorn app.main:app --reload")
        return
    
    print("\n✅ Backend is running")
    
    # Run tests
    tests_passed = 0
    total_tests = 2
    
    # Test 1: Post generation without API keys
    if await test_post_generation_without_api_keys():
        tests_passed += 1
    
    # Test 2: News fetch should still work
    if await test_news_fetch():
        tests_passed += 1
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✅ All tests passed! Backend fixes are working correctly.")
        print("\nNext steps:")
        print("1. Add at least one LLM API key to backend/.env:")
        print("   - ANTHROPIC_API_KEY=your_key_here")
        print("   - OPENAI_API_KEY=your_key_here")
        print("   - GOOGLE_API_KEY=your_key_here")
        print("2. Restart the backend")
        print("3. Try generating posts again")
    else:
        print("❌ Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
