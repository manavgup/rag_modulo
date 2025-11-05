#!/usr/bin/env python3
"""
Test search with CoT disabled using direct service access.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from pydantic import UUID4
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.search_service import SearchService
from core.config import get_settings

async def test_search_no_cot():
    """Test search with CoT explicitly disabled."""

    # Configuration
    collection_id = "2cae53c2-4a7e-444a-a12c-ca6831a31426"
    user_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"  # Valid UUIDv4 for test user
    query = "What services did IBM offer for free during the COVID-19 pandemic and to which organizations did they provide it?"

    print("=" * 80)
    print("TEST: Search with CoT DISABLED")
    print("=" * 80)
    print(f"Collection ID: {collection_id}")
    print(f"User ID: {user_id}")
    print(f"Query: {query}")
    print("=" * 80)
    print()

    # Create search input with CoT disabled
    search_input = SearchInput(
        question=query,
        collection_id=UUID4(collection_id),
        user_id=UUID4(user_id),
        config_metadata={
            "cot_enabled": False,  # EXPLICITLY DISABLE CoT
        }
    )

    # Initialize search service
    settings = get_settings()
    search_service = SearchService(settings=settings)

    # Execute search
    print("Executing search...")
    result = await search_service.search(search_input)

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"\nAnswer ({len(result.answer)} chars):")
    print(result.answer)

    print(f"\nDocuments retrieved: {len(result.documents)}")
    if result.documents:
        print("\nTop 3 document snippets:")
        for i, doc in enumerate(result.documents[:3], 1):
            print(f"\n{i}. {doc.document_name} (Page {doc.metadata.get('page_number', 'N/A')})")
            print(f"   Text: {doc.text[:200]}...")

    print("\n" + "=" * 80)
    print("CoT Metadata:")
    print(f"  - CoT Used: {result.metadata.get('cot_used', 'N/A')}")
    print(f"  - Reasoning Strategy: {result.metadata.get('reasoning_strategy', 'N/A')}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_search_no_cot())
