#!/usr/bin/env python3
"""
Test podcast script generation to validate text length.

This script tests ONLY the script generation step (Step 1 of podcast creation):
1. Fetch RAG results from collection
2. Generate script using LLM
3. Validate script length and format
"""

import asyncio
import os
import sys
from uuid import UUID

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from core.config import get_settings
from rag_solution.file_management.database import SessionLocal
from rag_solution.schemas.podcast_schema import PodcastGenerationInput
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.podcast_service import PodcastService
from rag_solution.services.search_service import SearchService


async def test_script_generation():
    """Test script generation for a 15-minute podcast."""

    print("🎙️  Testing Podcast Script Generation")
    print("=" * 80)

    # Get settings and database
    settings = get_settings()
    db = SessionLocal()

    try:
        # Collection ID from user's request
        collection_id = UUID("351a852a-368b-4d47-b650-ac2058227996")
        user_id = UUID("ee76317f-3b6f-4fea-8b74-56483731f58c")  # Mock user ID

        print(f"\n📁 Collection ID: {collection_id}")
        print(f"👤 User ID: {user_id}")

        # Create services
        collection_service = CollectionService(db, settings)
        search_service = SearchService(db, settings)
        podcast_service = PodcastService(db, collection_service, search_service)

        # Validate collection exists
        print("\n✅ Validating collection...")
        collection = collection_service.get_collection(collection_id)
        print(f"   Collection name: {collection.name}")
        print(f"   Collection status: {collection.status}")

        # Create podcast input
        podcast_input = PodcastGenerationInput(
            collection_id=collection_id,
            user_id=user_id,  # Add user_id
            duration=15,  # 15 minutes
            voice_settings={
                "voice_id": "nova",
                "gender": "female",
                "speed": 1.0,
                "pitch": 1.0,
                "language": "en-US",
                "name": "Nova",
            },
            title="Test Script Generation",
            description="Overview of the collection content",
        )

        print(f"\n🎯 Target duration: {podcast_input.duration} minutes")
        print(f"   Target word count: ~{podcast_input.duration * 150} words")

        # Step 1: Fetch RAG results
        print("\n📚 Step 1: Fetching RAG results...")
        search_input = SearchInput(
            question=podcast_input.description or "Provide an overview of the content",
            collection_id=collection_id,
            user_id=user_id,
        )

        search_result = await search_service.search(search_input)
        rag_results = search_result.answer

        print(f"   RAG results length: {len(rag_results)} characters")
        print(f"   RAG results preview: {rag_results[:200]}...")

        # Step 2: Generate script
        print("\n🤖 Step 2: Generating script with LLM...")
        print(f"   LLM Provider: {settings.llm_provider}")

        script_text = await podcast_service._generate_script(podcast_input, rag_results)

        # Validate script
        print("\n📊 Script Generation Results:")
        print("=" * 80)
        print(f"✅ Script length: {len(script_text)} characters")
        print(f"✅ Word count: ~{len(script_text.split())} words")
        print(f"✅ Lines: {len(script_text.splitlines())} lines")

        # Check if script meets minimum requirements
        word_count = len(script_text.split())
        min_words = podcast_input.duration * 150 * 0.8  # 80% of target
        max_words = podcast_input.duration * 150 * 1.2  # 120% of target

        print("\n📏 Validation:")
        print(f"   Min expected: {min_words:.0f} words")
        print(f"   Max expected: {max_words:.0f} words")
        print(f"   Actual: {word_count} words")

        if word_count < min_words:
            print("   ⚠️  WARNING: Script is shorter than expected!")
        elif word_count > max_words:
            print("   ⚠️  WARNING: Script is longer than expected!")
        else:
            print("   ✅ Script length is within target range!")

        # Show script preview
        print("\n📝 Script Preview (first 500 characters):")
        print("-" * 80)
        print(script_text[:500])
        print("-" * 80)

        # Check for HOST/EXPERT format
        has_host = "HOST:" in script_text or "Host:" in script_text
        has_expert = "EXPERT:" in script_text or "Expert:" in script_text

        print("\n🎭 Format Check:")
        print(f"   Has HOST: {has_host}")
        print(f"   Has EXPERT: {has_expert}")

        if has_host and has_expert:
            print("   ✅ Script has proper dialogue format!")
        else:
            print("   ⚠️  WARNING: Script may not have proper HOST/EXPERT format!")

        print("\n" + "=" * 80)
        print("✅ Script generation test completed successfully!")

        return True

    except Exception as e:
        print(f"\n❌ Error during script generation test: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Starting Podcast Script Generation Test\n")
    success = asyncio.run(test_script_generation())

    if success:
        print("\n🎉 Test completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Test failed!")
        sys.exit(1)
