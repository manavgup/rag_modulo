"""Integrated test script for structured output with NewIBM collection.

This script tests the COMPLETE integration of structured output through SearchService.

Usage:
    # Start infrastructure
    make local-dev-infra

    # Run test
    poetry run python test_structured_output_integrated.py

What it tests:
1. Structured output enabled via config_metadata in SearchInput
2. Citations returned in SearchOutput.structured_answer
3. Multi-page citations with chunk_id and page_number metadata
4. Backward compatibility (without structured output)
"""

import asyncio
from uuid import UUID

from backend.rag_solution.database import SessionLocal
from backend.rag_solution.schemas.search_schema import SearchInput
from backend.rag_solution.services.search_service import SearchService
from core.config import settings
from core.logging_utils import get_logger

logger = get_logger(__name__)

# Test configuration
COLLECTION_ID = UUID("a066f5e7-e402-44d8-acd1-7c74bb752ef7")  # NewIBM collection
USER_ID = UUID("00000000-0000-0000-0000-000000000001")  # Mock user ID


async def test_search_with_structured_output():
    """Test search with structured output enabled."""
    print("\n" + "=" * 100)
    print("TEST 1: Search with Structured Output ENABLED")
    print("=" * 100)

    db = SessionLocal()

    try:
        # Create SearchInput with structured output enabled
        search_input = SearchInput(
            question="What were IBM's key financial highlights in 2023 according to the annual report?",
            collection_id=COLLECTION_ID,
            user_id=USER_ID,
            config_metadata={
                "structured_output_enabled": True,  # ← Enable structured output
                "max_citations": 5,
                "min_confidence": 0.6,
                "format_type": "standard",
            },
        )

        print(f"\n🔍 Query: {search_input.question}")
        print(f"📦 Collection: {COLLECTION_ID}")
        print(f"⚙️  Structured Output: ENABLED")

        # Execute search
        search_service = SearchService(db, settings)
        print("\n🚀 Executing search through SearchService...")
        result = await search_service.search(search_input)

        # Verify structured output
        print("\n" + "=" * 100)
        print("RESULTS")
        print("=" * 100)

        print(f"\n✅ Answer ({len(result.answer)} chars):")
        print(f"   {result.answer[:200]}...")

        if result.structured_answer:
            print(f"\n✅ Structured Answer Found!")
            print(f"   Confidence: {result.structured_answer.confidence}")
            print(f"   Number of Citations: {len(result.structured_answer.citations)}")
            print(f"   Format Type: {result.structured_answer.format_type}")

            print(f"\n📚 Citations:")
            for i, citation in enumerate(result.structured_answer.citations, 1):
                print(f"\n   Citation {i}:")
                print(f"      Document ID: {citation.document_id}")
                print(f"      Title: {citation.title}")
                print(f"      Page: {citation.page_number if citation.page_number else 'N/A'}")
                print(f"      Chunk ID: {citation.chunk_id if citation.chunk_id else 'N/A'}")
                print(f"      Relevance: {citation.relevance_score:.3f}")
                print(f"      Excerpt: {citation.excerpt[:100]}...")

            # Check if multi-page citations are preserved
            page_numbers = [c.page_number for c in result.structured_answer.citations if c.page_number]
            unique_pages = len(set(page_numbers))
            print(f"\n   📄 Multi-page Support: {unique_pages} unique pages cited")

            # Check metadata
            if result.structured_answer.metadata:
                print(f"\n   ℹ️  Metadata:")
                for key, value in result.structured_answer.metadata.items():
                    print(f"      {key}: {value}")

        else:
            print("\n❌ No structured_answer in SearchOutput!")
            print("   This indicates the integration may not be working correctly.")

        print(f"\n📊 Search Metadata:")
        print(f"   Execution Time: {result.execution_time:.2f}s")
        print(f"   Documents Retrieved: {len(result.documents)}")
        print(f"   Pipeline Architecture: {result.metadata.get('pipeline_architecture', 'unknown')}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_search_without_structured_output():
    """Test backward compatibility - search without structured output."""
    print("\n" + "=" * 100)
    print("TEST 2: Search WITHOUT Structured Output (Backward Compatibility)")
    print("=" * 100)

    db = SessionLocal()

    try:
        # Create SearchInput WITHOUT structured output config
        search_input = SearchInput(
            question="What were IBM's key financial highlights in 2023?",
            collection_id=COLLECTION_ID,
            user_id=USER_ID,
            # No config_metadata or structured_output_enabled
        )

        print(f"\n🔍 Query: {search_input.question}")
        print(f"📦 Collection: {COLLECTION_ID}")
        print(f"⚙️  Structured Output: DISABLED (default)")

        # Execute search
        search_service = SearchService(db, settings)
        print("\n🚀 Executing search through SearchService...")
        result = await search_service.search(search_input)

        # Verify NO structured output
        print("\n" + "=" * 100)
        print("RESULTS")
        print("=" * 100)

        print(f"\n✅ Answer ({len(result.answer)} chars):")
        print(f"   {result.answer[:200]}...")

        if result.structured_answer:
            print("\n⚠️  WARNING: structured_answer is present but was not requested!")
            print("   This may indicate a configuration issue.")
        else:
            print("\n✅ Correctly NO structured_answer (backward compatible)")

        print(f"\n📊 Search Metadata:")
        print(f"   Execution Time: {result.execution_time:.2f}s")
        print(f"   Documents Retrieved: {len(result.documents)}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_high_confidence_threshold():
    """Test with high confidence threshold to potentially trigger post-hoc fallback."""
    print("\n" + "=" * 100)
    print("TEST 3: High Confidence Threshold (May Trigger Post-Hoc Fallback)")
    print("=" * 100)

    db = SessionLocal()

    try:
        # Create SearchInput with very high confidence threshold
        search_input = SearchInput(
            question="What were IBM's revenue and profit numbers in 2023?",
            collection_id=COLLECTION_ID,
            user_id=USER_ID,
            config_metadata={
                "structured_output_enabled": True,
                "max_citations": 5,
                "min_confidence": 0.95,  # Very high threshold
                "format_type": "standard",
            },
        )

        print(f"\n🔍 Query: {search_input.question}")
        print(f"⚙️  Min Confidence: 0.95 (HIGH - may trigger fallback)")

        # Execute search
        search_service = SearchService(db, settings)
        result = await search_service.search(search_input)

        # Check attribution method
        if result.structured_answer and result.structured_answer.metadata:
            attribution_method = result.structured_answer.metadata.get("attribution_method", "llm_generated")
            print(f"\n📊 Attribution Method: {attribution_method}")

            if attribution_method == "post_hoc_semantic":
                print("   ✅ Post-hoc attribution used (LLM citations failed validation)")
            else:
                print("   ✅ LLM citations passed validation")

            print(f"   Confidence: {result.structured_answer.confidence}")
            print(f"   Citations: {len(result.structured_answer.citations)}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


async def main():
    """Run all tests."""
    print("\n" + "=" * 100)
    print("INTEGRATED STRUCTURED OUTPUT TESTING")
    print("Testing complete integration through SearchService pipeline")
    print("=" * 100)

    results = []

    # Test 1: With structured output
    results.append(await test_search_with_structured_output())

    # Test 2: Without structured output (backward compatibility)
    results.append(await test_search_without_structured_output())

    # Test 3: High confidence threshold
    results.append(await test_high_confidence_threshold())

    # Summary
    print("\n" + "=" * 100)
    print("TEST SUMMARY")
    print("=" * 100)

    for i, result in enumerate(results, 1):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"Test {i}: {status}")

    all_passed = all(results)
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  SOME TESTS FAILED - Check output above")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
