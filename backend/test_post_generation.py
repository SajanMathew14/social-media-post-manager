#!/usr/bin/env python3
"""
Test script for post generation workflow.

This script tests the post generation functionality to verify
that our fixes work correctly.
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.langgraph.workflows.post_workflow import execute_post_workflow
from app.core.database import AsyncSessionLocal
from app.models.session import Session
from app.models.generated_post import GeneratedPost


async def create_test_session() -> str:
    """Create a test session in the database."""
    async with AsyncSessionLocal() as db:
        # Create a test session
        session_id = str(uuid.uuid4())
        session = Session(
            id=uuid.UUID(session_id),
            created_at=datetime.utcnow()
        )
        
        db.add(session)
        await db.commit()
        
        print(f"✅ Created test session: {session_id}")
        return session_id


async def test_post_generation():
    """Test the post generation workflow."""
    print("🚀 Starting post generation test...")
    
    try:
        # Create test session
        session_id = await create_test_session()
        
        # Sample articles (similar to what would come from news workflow)
        test_articles = [
            {
                "title": "OpenAI Releases GPT-5 with Revolutionary Capabilities",
                "url": "https://example.com/gpt5-release",
                "source": "TechCrunch",
                "summary": "OpenAI has announced GPT-5, featuring advanced reasoning capabilities and multimodal understanding that surpasses previous models.",
                "published_at": "2025-06-20T10:00:00Z",
                "relevance_score": 0.95
            },
            {
                "title": "AI Startup Raises $100M Series B for Enterprise Solutions",
                "url": "https://example.com/ai-startup-funding",
                "source": "VentureBeat",
                "summary": "A promising AI startup focused on enterprise automation has secured significant funding to expand their platform.",
                "published_at": "2025-06-20T09:30:00Z",
                "relevance_score": 0.88
            },
            {
                "title": "New AI Regulations Proposed by European Union",
                "url": "https://example.com/eu-ai-regulations",
                "source": "Reuters",
                "summary": "The EU has proposed comprehensive AI regulations aimed at ensuring responsible development and deployment of AI technologies.",
                "published_at": "2025-06-20T08:15:00Z",
                "relevance_score": 0.82
            }
        ]
        
        # Test parameters
        topic = "AI, Tech and AI based Startups"
        llm_model = "claude-3-5-sonnet"
        news_workflow_id = str(uuid.uuid4())
        
        print(f"📝 Test parameters:")
        print(f"   - Session ID: {session_id}")
        print(f"   - Topic: {topic}")
        print(f"   - LLM Model: {llm_model}")
        print(f"   - Articles: {len(test_articles)}")
        print(f"   - News Workflow ID: {news_workflow_id}")
        
        # Execute post generation workflow
        print("\n🔄 Executing post generation workflow...")
        
        result = await execute_post_workflow(
            articles=test_articles,
            topic=topic,
            llm_model=llm_model,
            session_id=session_id,
            news_workflow_id=news_workflow_id
        )
        
        # Display results
        print("\n✅ Post generation completed successfully!")
        print(f"📊 Results:")
        print(f"   - Workflow ID: {result['workflow_id']}")
        print(f"   - Processing Time: {result['processing_time']:.2f}s")
        print(f"   - LLM Model Used: {result['llm_model_used']}")
        print(f"   - Posts Generated: {len(result['posts'])}")
        
        # Display generated posts
        for platform, post_data in result["posts"].items():
            print(f"\n📱 {platform.upper()} Post:")
            print(f"   - Character Count: {post_data['char_count']}")
            print(f"   - Hashtags: {post_data.get('hashtags', [])}")
            print(f"   - Content Preview: {post_data['content'][:100]}...")
        
        # Verify posts were saved to database
        print("\n🔍 Verifying database records...")
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            
            result_db = await db.execute(
                select(GeneratedPost).where(GeneratedPost.session_id == uuid.UUID(session_id))
            )
            saved_posts = result_db.scalars().all()
            
            print(f"✅ Found {len(saved_posts)} posts in database:")
            for post in saved_posts:
                print(f"   - {post.post_type.value}: {post.char_count} chars (ID: {post.id})")
        
        print("\n🎉 Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        # Print full traceback for debugging
        import traceback
        print(f"\nFull traceback:")
        traceback.print_exc()
        
        return False


async def cleanup_test_data():
    """Clean up test data from database."""
    print("\n🧹 Cleaning up test data...")
    
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import delete
            
            # Delete test posts and sessions
            await db.execute(delete(GeneratedPost))
            await db.execute(delete(Session))
            await db.commit()
            
            print("✅ Test data cleaned up successfully")
            
    except Exception as e:
        print(f"⚠️ Warning: Failed to clean up test data: {str(e)}")


async def main():
    """Main test function."""
    print("=" * 60)
    print("🧪 POST GENERATION WORKFLOW TEST")
    print("=" * 60)
    
    try:
        # Run the test
        success = await test_post_generation()
        
        if success:
            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED!")
            print("The post generation workflow is working correctly.")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ TESTS FAILED!")
            print("There are issues with the post generation workflow.")
            print("=" * 60)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {str(e)}")
        sys.exit(1)
    finally:
        # Always try to clean up
        await cleanup_test_data()


if __name__ == "__main__":
    # Run the test
    asyncio.run(main())
