"""
Script to seed the database with initial topic configurations.

This script creates the default topic configurations that are used
for domain-aware news filtering and source prioritization.
"""
import asyncio
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models.topic_config import TopicConfig


async def seed_topics():
    """Seed the database with initial topic configurations."""
    
    # Define topic configurations
    topics = [
        {
            "topic_name": "ai",
            "keywords": [
                "AI", "artificial intelligence", "machine learning", "deep learning",
                "neural networks", "LLM", "GPT", "Claude", "OpenAI", "Anthropic",
                "computer vision", "natural language processing", "NLP", "automation"
            ],
            "trusted_sources": [
                "techcrunch.com", "venturebeat.com", "mit.edu", "nvidia.com",
                "openai.com", "anthropic.com", "deepmind.com", "arxiv.org",
                "nature.com", "science.org", "ieee.org", "acm.org"
            ],
            "priority_weight": 1.5
        },
        {
            "topic_name": "finance",
            "keywords": [
                "finance", "fintech", "banking", "cryptocurrency", "bitcoin",
                "blockchain", "markets", "trading", "investment", "venture capital",
                "IPO", "stocks", "bonds", "derivatives", "DeFi", "payments"
            ],
            "trusted_sources": [
                "bloomberg.com", "reuters.com", "wsj.com", "ft.com",
                "forbes.com", "economist.com", "cnbc.com", "marketwatch.com",
                "coindesk.com", "cointelegraph.com", "sec.gov", "federalreserve.gov"
            ],
            "priority_weight": 1.4
        },
        {
            "topic_name": "healthcare",
            "keywords": [
                "healthcare", "medical", "biotech", "pharmaceuticals", "drugs",
                "clinical trials", "FDA", "medicine", "health tech", "telemedicine",
                "genomics", "precision medicine", "medical devices", "diagnostics"
            ],
            "trusted_sources": [
                "nejm.org", "thelancet.com", "nature.com", "science.org",
                "nih.gov", "fda.gov", "who.int", "cdc.gov", "statnews.com",
                "fiercebiotech.com", "biopharmadive.com", "medpagetoday.com"
            ],
            "priority_weight": 1.3
        },
        {
            "topic_name": "technology",
            "keywords": [
                "technology", "tech", "software", "hardware", "startup",
                "innovation", "digital transformation", "cloud computing",
                "cybersecurity", "data", "analytics", "IoT", "5G", "quantum"
            ],
            "trusted_sources": [
                "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
                "engadget.com", "zdnet.com", "computerworld.com", "infoworld.com",
                "ieee.org", "acm.org", "mit.edu", "stanford.edu"
            ],
            "priority_weight": 1.2
        },
        {
            "topic_name": "business",
            "keywords": [
                "business", "corporate", "enterprise", "economy", "GDP",
                "earnings", "revenue", "profit", "merger", "acquisition",
                "leadership", "strategy", "management", "operations", "supply chain"
            ],
            "trusted_sources": [
                "wsj.com", "ft.com", "bloomberg.com", "reuters.com",
                "economist.com", "forbes.com", "fortune.com", "businessinsider.com",
                "hbr.org", "mckinsey.com", "bcg.com", "pwc.com"
            ],
            "priority_weight": 1.1
        }
    ]
    
    async with AsyncSessionLocal() as session:
        try:
            print("🌱 Seeding topic configurations...")
            
            for topic_data in topics:
                # Check if topic already exists
                from sqlalchemy import select
                result = await session.execute(
                    select(TopicConfig).where(TopicConfig.topic_name == topic_data["topic_name"])
                )
                existing_topic = result.scalar_one_or_none()
                
                if existing_topic:
                    print(f"   ⚠️  Topic '{topic_data['topic_name']}' already exists, skipping...")
                    continue
                
                # Create new topic configuration
                topic_config = TopicConfig(
                    topic_name=topic_data["topic_name"],
                    keywords=topic_data["keywords"],
                    trusted_sources=topic_data["trusted_sources"],
                    priority_weight=topic_data["priority_weight"]
                )
                
                session.add(topic_config)
                print(f"   ✅ Added topic configuration for '{topic_data['topic_name']}'")
            
            # Commit all changes
            await session.commit()
            print("🎉 Topic configurations seeded successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error seeding topics: {str(e)}")
            raise


async def main():
    """Main function to run the seeding script."""
    print("🚀 Starting topic configuration seeding...")
    
    try:
        await seed_topics()
        print("✨ Seeding completed successfully!")
        
    except Exception as e:
        print(f"💥 Seeding failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
