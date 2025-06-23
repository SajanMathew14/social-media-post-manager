"""
Script to add the generated_posts table to the database.

This script creates the new table for storing LinkedIn and X posts
generated from news articles.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine
from app.models import Base, GeneratedPost


async def create_generated_posts_table():
    """Create the generated_posts table if it doesn't exist."""
    
    print("Creating generated_posts table...")
    
    try:
        # Create all tables (this will only create tables that don't exist)
        async with engine.begin() as conn:
            # First check if the table already exists
            result = await conn.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'generated_posts'
                    );
                """)
            )
            table_exists = result.scalar()
            
            if table_exists:
                print("✓ Table 'generated_posts' already exists")
                return
            
            # Create the table using SQLAlchemy metadata
            await conn.run_sync(Base.metadata.create_all)
            
            print("✓ Successfully created 'generated_posts' table")
            
            # Verify the table was created
            result = await conn.execute(
                text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public' 
                    AND table_name = 'generated_posts'
                    ORDER BY ordinal_position;
                """)
            )
            
            columns = result.fetchall()
            print("\nTable structure:")
            for col in columns:
                nullable = "NULL" if col.is_nullable == "YES" else "NOT NULL"
                print(f"  - {col.column_name}: {col.data_type} {nullable}")
                
    except Exception as e:
        print(f"✗ Error creating table: {str(e)}")
        raise


async def main():
    """Main function to run the migration."""
    print("Starting database migration for Sprint 3...")
    print(f"Database URL: {engine.url}")
    
    try:
        await create_generated_posts_table()
        print("\n✓ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}")
        sys.exit(1)
    
    finally:
        # Dispose of the engine
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
