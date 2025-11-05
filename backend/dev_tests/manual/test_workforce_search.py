#!/usr/bin/env python3
"""Test script to search for IBM workforce diversity data in Milvus.

This script searches for workforce/diversity information to diagnose why
the query "What percentage of IBM's workforce currently consists of women?"
returns financial data instead of diversity data.
"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
from pymilvus import Collection, connections
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import Embeddings

# Load environment variables
load_dotenv()


def test_workforce_diversity_search():
    """Test search for workforce diversity information."""

    # Configuration - UPDATE THIS with your actual collection name
    collection_name = "collection_0fa6e28b3b76494a97cbdf3c9288747e"  # From debug log

    # Test queries - original failing query + variations
    queries = [
        # Original failing query
        "What percentage of IBM's workforce currently consists of women?",

        # Variations to test semantic search
        "IBM women workforce percentage",
        "female employees IBM statistics",
        "workforce diversity women",
        "gender diversity IBM",

        # Keywords that should exist in annual reports
        "diversity inclusion women",
        "employee demographics gender",

        # Control: query that works (financial data)
        "IBM revenue gross profit",
    ]

    print("=" * 80)
    print("WORKFORCE DIVERSITY SEARCH TEST")
    print("=" * 80)
    print(f"\nCollection: {collection_name}")
    print(f"Testing {len(queries)} queries\n")

    # Get credentials from environment
    print("Loading WatsonX credentials...")
    api_key = os.getenv("WATSONX_APIKEY") or os.getenv("WATSONX_API_KEY")
    project_id = os.getenv("WATSONX_INSTANCE_ID") or os.getenv("WATSONX_PROJECT_ID") or "3f77f23d-71b7-426b-ae13-bc4710769880"
    url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key:
        print("❌ Missing WATSONX_APIKEY in environment")
        return

    print(f"✅ Credentials loaded")

    # Initialize WatsonX embeddings client
    print("Initializing WatsonX embeddings client...")
    try:
        credentials = Credentials(api_key=api_key, url=url)
        embeddings_client = Embeddings(
            model_id="ibm/slate-125m-english-rtrvr-v2",
            credentials=credentials,
            project_id=project_id
        )
        print("✅ Embeddings client initialized\n")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return

    # Connect to Milvus
    print("Connecting to Milvus...")
    try:
        connections.connect(alias="default", host="localhost", port=19530)
        print("✅ Connected to Milvus\n")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    # Load collection
    print(f"Loading collection...")
    try:
        collection = Collection(collection_name)
        collection.load()

        # Get collection stats
        num_entities = collection.num_entities
        print(f"✅ Collection loaded: {num_entities:,} chunks\n")
    except Exception as e:
        print(f"❌ Failed to load collection: {e}")
        connections.disconnect("default")
        return

    # Test each query
    for i, query in enumerate(queries, 1):
        print("=" * 80)
        print(f"QUERY {i}: {query}")
        print("=" * 80)

        # Get embeddings
        try:
            result = embeddings_client.embed_documents(texts=[query])
            query_embedding = result[0]
            print(f"✅ Embedding generated (dim: {len(query_embedding)})")
        except Exception as e:
            print(f"❌ Embedding failed: {e}")
            continue

        # Search Milvus
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

        try:
            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=20,
                output_fields=["text", "document_name", "page_number", "chunk_number"],
            )
        except Exception as e:
            print(f"❌ Search failed: {e}")
            continue

        # Analyze results
        if not results or len(results) == 0 or len(results[0]) == 0:
            print("❌ NO RESULTS FOUND\n")
            continue

        print(f"\n📊 TOP 10 RESULTS (out of {len(results[0])}):")
        print("-" * 80)

        # Track content types
        has_diversity_content = False
        has_financial_content = False
        diversity_keywords = ["women", "female", "gender", "diversity", "workforce", "employee"]
        financial_keywords = ["revenue", "profit", "margin", "financing", "maturities"]

        for j, hit in enumerate(results[0][:10], 1):
            score = hit.score
            text = hit.entity.get("text") or ""
            doc_name = hit.entity.get("document_name") or "unknown"
            page = hit.entity.get("page_number") or "?"
            chunk = hit.entity.get("chunk_number") or "?"

            # Check content type
            text_lower = text.lower()
            is_diversity = any(kw in text_lower for kw in diversity_keywords)
            is_financial = any(kw in text_lower for kw in financial_keywords)

            if is_diversity:
                has_diversity_content = True
            if is_financial:
                has_financial_content = True

            # Display result
            content_type = []
            if is_diversity:
                content_type.append("🎯 DIVERSITY")
            if is_financial:
                content_type.append("💰 FINANCIAL")
            if not content_type:
                content_type.append("📄 OTHER")

            print(f"\n{j}. Score: {score:.4f} | Page: {page} | {' '.join(content_type)}")
            print(f"   Doc: {doc_name}")
            print(f"   Text preview: {text[:200]}...")

        # Summary
        print("\n" + "-" * 80)
        print("📊 CONTENT ANALYSIS:")
        print(f"   ✓ Contains diversity content: {'YES ✅' if has_diversity_content else 'NO ❌'}")
        print(f"   ✓ Contains financial content: {'YES' if has_financial_content else 'NO'}")

        if not has_diversity_content and "women" in query.lower():
            print("\n⚠️  WARNING: Diversity query returned NO diversity content!")
            print("   This explains why the LLM couldn't answer the question.")

        print()

    # Cleanup
    print("=" * 80)
    connections.disconnect("default")
    print("✅ Test complete!")
    print("\n💡 DIAGNOSIS:")
    print("   If diversity queries return only financial data, the issue is:")
    print("   1. Document chunking split diversity sections from context")
    print("   2. Diversity sections weren't indexed properly")
    print("   3. Embedding model has poor semantic understanding of 'percentage'")
    print("=" * 80)


if __name__ == "__main__":
    test_workforce_diversity_search()
