#!/usr/bin/env python3
"""
Test reranking impact on search results.

Compares search results with and without reranking to demonstrate
the fix for Issue #465 (reranking variable name mismatch).
"""

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

import httpx
from dotenv import load_dotenv

# Test configuration
TEST_FILE = "/Users/mg/Downloads/2021-ibm-annual-report.txt"  # Using 2021 for existing collections
TEST_QUERY = "What was IBM revenue in 2021?"
EXPECTED_ANSWER = "57.4 billion"  # 2021 revenue

# API configuration
API_BASE = "http://localhost:8000"
USER_UUID = "ee76317f-3b6f-4fea-8b74-56483731f58c"

# Use existing collection from embedding comparison test
# Collections are named like: test-slate-125m-english-rtrvr-{random}
COLLECTION_PREFIX = "test-slate-125m-english-rtrvr"


async def search_with_config(collection_id: str, query: str, enable_reranking: bool, top_k: int = 20) -> dict:
    """Run search query with specific reranking configuration."""
    config_label = "WITH reranking" if enable_reranking else "WITHOUT reranking"
    print(f"\n{'=' * 80}")
    print(f"🔍 Testing {config_label}")
    print(f"{'=' * 80}")

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{API_BASE}/api/search",
            headers={
                "Content-Type": "application/json",
                "X-User-UUID": USER_UUID,
            },
            json={
                "question": query,
                "collection_id": collection_id,
                "user_id": USER_UUID,
                "config_metadata": {
                    "cot_disabled": True,  # Disable CoT to isolate reranking effect
                    "top_k": top_k,
                    "enable_reranking": enable_reranking,  # Explicit control
                },
            },
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Search failed: {response.status_code} - {response.text}")


def analyze_results(results: dict, expected_text: str, label: str) -> dict:
    """Analyze search results to find where the expected chunk ranks."""
    query_results = results.get("query_results", [])
    answer = results.get("answer", "")

    # Find revenue chunk
    revenue_chunk_rank = None
    revenue_chunk_score = None
    revenue_chunk_text = None

    for i, result in enumerate(query_results, 1):
        chunk_text = result["chunk"]["text"]
        if expected_text in chunk_text:
            revenue_chunk_rank = i
            revenue_chunk_score = result["score"]
            revenue_chunk_text = chunk_text[:200]
            break

    # Check if answer contains expected text
    answer_correct = expected_text in answer

    analysis = {
        "label": label,
        "revenue_chunk_rank": revenue_chunk_rank,
        "revenue_chunk_score": revenue_chunk_score,
        "revenue_chunk_text": revenue_chunk_text,
        "answer_correct": answer_correct,
        "total_results": len(query_results),
    }

    # Print results
    print(f"\n📊 Results {label}:")
    print(f"   Total chunks returned: {len(query_results)}")

    if revenue_chunk_rank:
        print(f"   ✅ Revenue chunk found at rank: #{revenue_chunk_rank}")
        print(f"   📈 Score: {revenue_chunk_score:.4f}")
        print(f"   📝 Text preview: {revenue_chunk_text[:100]}...")
    else:
        print(f"   ❌ Revenue chunk NOT found in top {len(query_results)} results")

    print(f"   {'✅' if answer_correct else '❌'} Answer contains '{expected_text}': {answer_correct}")

    # Show top 5 chunks with scores
    print(f"\n   Top 5 chunks {label}:")
    for i, result in enumerate(query_results[:5], 1):
        chunk_text = result["chunk"]["text"][:80]
        score = result["score"]
        is_revenue = "🎯 REVENUE" if expected_text in result["chunk"]["text"] else ""
        print(f"   {i:2d}. Score: {score:.4f} - {chunk_text}... {is_revenue}")

    return analysis


async def get_or_create_collection():
    """Get existing collection from embedding comparison test."""
    print(f"🔍 Looking for collection starting with: {COLLECTION_PREFIX}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # List collections
        response = await client.get(
            f"{API_BASE}/api/collections",
            headers={"X-User-UUID": USER_UUID},
        )

        if response.status_code == 200:
            collections = response.json()
            matching_collections = [col for col in collections if col["name"].startswith(COLLECTION_PREFIX)]

            if matching_collections:
                # Find first completed/ready collection
                for col in matching_collections:
                    if col.get("status") in ["completed", "ready"]:
                        print(f"✅ Found collection: {col['name']} (ID: {col['id']}) - Status: {col['status']}")
                        return col["id"]

                # If no completed collections, use first one but warn
                col = matching_collections[0]
                print(f"⚠️  Found collection: {col['name']} (ID: {col['id']}) - Status: {col.get('status', 'unknown')}")
                return col["id"]

        print(f"❌ No collection found starting with '{COLLECTION_PREFIX}'")
        print("   Please run test_embedding_comparison.py first to create test collections")
        print("   or manually create a collection with the IBM Slate 125M model")
        return None


async def main():
    """Run reranking comparison test."""
    print("=" * 80)
    print("🔬 RERANKING IMPACT TEST")
    print("=" * 80)
    print(f"Query: '{TEST_QUERY}'")
    print(f"Expected text: '{EXPECTED_ANSWER}'")

    # Get collection
    collection_id = await get_or_create_collection()
    if not collection_id:
        return

    # Test WITHOUT reranking
    results_no_rerank = await search_with_config(collection_id, TEST_QUERY, enable_reranking=False, top_k=20)
    analysis_no_rerank = analyze_results(results_no_rerank, EXPECTED_ANSWER, "WITHOUT reranking")

    # Test WITH reranking
    results_with_rerank = await search_with_config(collection_id, TEST_QUERY, enable_reranking=True, top_k=20)
    analysis_with_rerank = analyze_results(results_with_rerank, EXPECTED_ANSWER, "WITH reranking")

    # Compare results
    print("\n" + "=" * 80)
    print("📊 COMPARISON SUMMARY")
    print("=" * 80)

    rank_no_rerank = analysis_no_rerank["revenue_chunk_rank"]
    rank_with_rerank = analysis_with_rerank["revenue_chunk_rank"]

    if rank_no_rerank and rank_with_rerank:
        improvement = rank_no_rerank - rank_with_rerank
        print("\n🎯 Revenue Chunk Ranking:")
        print(f"   WITHOUT reranking: #{rank_no_rerank}")
        print(f"   WITH reranking:    #{rank_with_rerank}")

        if improvement > 0:
            print(f"   ✅ Reranking IMPROVED ranking by {improvement} positions! 🎉")
        elif improvement < 0:
            print(f"   ⚠️  Reranking worsened ranking by {abs(improvement)} positions")
        else:
            print("   ➡️  No change in ranking")

        # Show score change
        score_no_rerank = analysis_no_rerank["revenue_chunk_score"]
        score_with_rerank = analysis_with_rerank["revenue_chunk_score"]
        print("\n📈 Revenue Chunk Score:")
        print(f"   WITHOUT reranking: {score_no_rerank:.4f}")
        print(f"   WITH reranking:    {score_with_rerank:.4f}")
        print(f"   Change: {score_with_rerank - score_no_rerank:+.4f}")
    else:
        print("\n❌ Could not compare - revenue chunk not found in one or both result sets")

    print("\n" + "=" * 80)
    print("✅ Test complete!")
    print("=" * 80)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
