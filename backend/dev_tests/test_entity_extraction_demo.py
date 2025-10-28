"""Demo script to test EntityExtractionService with the IBM revenue query.

Usage:
    python test_entity_extraction_demo.py                           # Run all built-in tests
    python test_entity_extraction_demo.py "your query here"         # Test custom query
    python test_entity_extraction_demo.py --help                    # Show help
"""

import argparse
import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add backend to path - must be before local imports
backend_path = Path(__file__).parent.parent  # Go up to project root
sys.path.insert(0, str(backend_path))

from rag_solution.services.entity_extraction_service import EntityExtractionService  # noqa: E402


async def test_simple_query():
    """Test entity extraction from simple query: 'what was the IBM revenue'."""
    # Create service with mocked dependencies
    mock_db = MagicMock()
    mock_settings = MagicMock()
    service = EntityExtractionService(mock_db, mock_settings)

    # Simple query without year
    simple_query = "what was the IBM revenue"

    print("=" * 80)
    print("TESTING SIMPLE QUERY: 'what was the IBM revenue'")
    print("=" * 80)
    print(f"Query: {simple_query}\n")

    # Test fast extraction (spaCy)
    print("Method: FAST (spaCy NER)")
    print("-" * 80)
    entities_fast = await service.extract_entities(simple_query, method="fast")
    print(f"Entities extracted: {entities_fast}")
    print(f"Count: {len(entities_fast)}")

    print("\n" + "=" * 80)
    print("EXPECTED vs ACTUAL")
    print("=" * 80)
    print("\nExpected entities: ['IBM', 'revenue']")
    print(f"Actual entities:   {entities_fast}")

    # Check if we got the key entities
    has_ibm = any("ibm" in e.lower() for e in entities_fast)
    has_revenue = any("revenue" in e.lower() for e in entities_fast)

    print(f"\n✓ Has 'IBM': {has_ibm}")
    print(f"✓ Has 'revenue': {has_revenue}")

    return entities_fast


async def test_ibm_revenue_context():
    """Test entity extraction from problematic IBM revenue query context."""
    # Create service with mocked dependencies
    mock_db = MagicMock()
    mock_settings = MagicMock()
    service = EntityExtractionService(mock_db, mock_settings)

    # The problematic context from your logs
    problematic_context = """
    Assistant: Based on the analysis of what was the IBM revenue in 2020?
    (in the context of This, User, Absence, Revenue, strong returns on equity,
    However, Instead, the context, Global Financing, the analysis of what, It,
    Key Points, Assistant, Since, Based, Additionally): The provided context does
    not contain specific revenue figures for IBM in 2020.
    """

    print("=" * 80)
    print("TESTING ENTITY EXTRACTION")
    print("=" * 80)
    print(f"\nContext (truncated): {problematic_context[:200]}...\n")

    # Test fast extraction (spaCy)
    print("Method: FAST (spaCy NER)")
    print("-" * 80)
    entities_fast = await service.extract_entities(problematic_context, method="fast")
    print(f"Entities extracted: {entities_fast}")
    print(f"Count: {len(entities_fast)}")

    # Verify the BAD entities are NOT extracted
    bad_entities = ["This", "User", "However", "Instead", "the context", "Assistant", "Since", "Based"]
    good_entities = ["IBM", "2020", "revenue", "Revenue", "Global Financing"]

    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)

    print("\n✅ Good entities (SHOULD be extracted):")
    for entity in good_entities:
        found = any(entity.lower() in e.lower() for e in entities_fast)
        status = "✅ FOUND" if found else "❌ MISSING"
        print(f"  {status}: {entity}")

    print("\n❌ Bad entities (should NOT be extracted):")
    for entity in bad_entities:
        found = any(entity.lower() == e.lower() for e in entities_fast)
        status = "❌ FOUND (BUG!)" if found else "✅ FILTERED"
        print(f"  {status}: {entity}")

    print("\n" + "=" * 80)
    print("RESULT")
    print("=" * 80)

    # Calculate success rate
    good_found = sum(1 for e in good_entities if any(e.lower() in ef.lower() for ef in entities_fast))
    bad_filtered = sum(1 for e in bad_entities if not any(e.lower() == ef.lower() for ef in entities_fast))

    success_rate = ((good_found + bad_filtered) / (len(good_entities) + len(bad_entities))) * 100

    print(f"\nGood entities found: {good_found}/{len(good_entities)}")
    print(f"Bad entities filtered: {bad_filtered}/{len(bad_entities)}")
    print(f"Success rate: {success_rate:.1f}%")

    if success_rate >= 80:
        print("\n🎉 SUCCESS: Entity extraction is working correctly!")
    else:
        print("\n⚠️ NEEDS IMPROVEMENT: Entity extraction needs tuning")

    return entities_fast


async def test_clean_query():
    """Test with a clean query to show proper extraction."""
    mock_db = MagicMock()
    mock_settings = MagicMock()
    service = EntityExtractionService(mock_db, mock_settings)

    clean_context = (
        "IBM reported total revenue of $73.6 billion in 2020, with Global Financing contributing significantly."
    )

    print("\n\n" + "=" * 80)
    print("TESTING CLEAN QUERY (for comparison)")
    print("=" * 80)
    print(f"Context: {clean_context}\n")

    entities = await service.extract_entities(clean_context, method="fast")
    print(f"Entities extracted: {entities}")
    print(f"Count: {len(entities)}")

    return entities


async def test_custom_query(query: str, method: str = "fast"):
    """Test entity extraction with a custom user-provided query.

    Args:
        query: User-provided query text
        method: Extraction method ("fast", "llm", or "hybrid")
    """
    mock_db = MagicMock()
    mock_settings = MagicMock()
    service = EntityExtractionService(mock_db, mock_settings)

    print("=" * 80)
    print(f"CUSTOM QUERY ENTITY EXTRACTION (method: {method})")
    print("=" * 80)
    print(f"Query: {query}\n")

    # Extract entities
    entities = await service.extract_entities(query, method=method)

    print(f"Entities extracted: {entities}")
    print(f"Count: {len(entities)}")

    # Show detailed breakdown using spaCy directly
    print("\n" + "-" * 80)
    print("DETAILED BREAKDOWN (using spaCy NER):")
    print("-" * 80)

    try:
        import spacy

        nlp = spacy.load("en_core_web_sm")
        doc = nlp(query)

        if doc.ents:
            print("\nNamed Entities:")
            for ent in doc.ents:
                print(f"  • {ent.text:20} → {ent.label_:15} ({ent.label_})")
        else:
            print("\nNo named entities found by spaCy NER")

        print("\nNoun Chunks (concepts):")
        for chunk in doc.noun_chunks:
            print(f"  • {chunk.text}")

    except Exception as e:
        print(f"Could not load spaCy for detailed breakdown: {e}")

    print("\n" + "=" * 80)

    return entities


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Test entity extraction with EntityExtractionService",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run all built-in tests
    python test_entity_extraction_demo.py

    # Test a custom query
    python test_entity_extraction_demo.py "What is the revenue of IBM in 2020?"

    # Test with different method
    python test_entity_extraction_demo.py "IBM revenue 2020" --method hybrid

    # Test a complex query
    python test_entity_extraction_demo.py "How did Apple's iPhone sales compare to Samsung in Q4 2023?"
        """,
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Custom query to test entity extraction (if omitted, runs built-in tests)",
    )

    parser.add_argument(
        "--method",
        "-m",
        choices=["fast", "llm", "hybrid"],
        default="fast",
        help="Extraction method: fast (spaCy only), llm (LLM only), hybrid (both). Default: fast",
    )

    args = parser.parse_args()

    print("\n🚀 EntityExtractionService Demo\n")

    if args.query:
        # User provided a custom query - test it
        asyncio.run(test_custom_query(args.query, method=args.method))
    else:
        # No query provided - run all built-in tests
        print("Running built-in test suite...\n")

        # Test 1: Simple query without year
        asyncio.run(test_simple_query())

        print("\n\n")

        # Test 2: Problematic context from logs
        asyncio.run(test_ibm_revenue_context())

        print("\n\n")

        # Test 3: Clean query
        asyncio.run(test_clean_query())

    print("\n" + "=" * 80)
    print("Demo complete!")
    print("=" * 80)
