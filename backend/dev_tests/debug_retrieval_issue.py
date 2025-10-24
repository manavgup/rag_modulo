#!/usr/bin/env python3
"""
Debug script to investigate why revenue information from page 1 isn't being retrieved.
"""

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from pymilvus import Collection, connections

from core.config import get_settings


async def main():
    settings = get_settings()

    # Connect to Milvus
    print("🔌 Connecting to Milvus...")
    connections.connect(alias="default", host=settings.milvus_host, port=settings.milvus_port)

    collection_name = "collection_9c26cf34bb304e00a11f017ed63671f0"
    print(f"📚 Analyzing collection: {collection_name} (test-slate-768-dims-NEW)")

    collection = Collection(collection_name)
    collection.load()

    # Query 1: Get all chunks from page 1
    print("\n" + "=" * 80)
    print("STEP 1: Checking if page 1 chunks exist in Milvus")
    print("=" * 80)

    expr = "page_number == 1"
    page1_chunks = collection.query(
        expr=expr, output_fields=["chunk_id", "text", "page_number", "chunk_number"], limit=100
    )

    print(f"\n✅ Found {len(page1_chunks)} chunks from page 1")

    if len(page1_chunks) == 0:
        print("❌ PROBLEM: No chunks from page 1 found in Milvus!")
        print("   This indicates a document parsing or ingestion issue.")
        return

    # Display page 1 chunks
    print("\n📄 Page 1 chunks:")
    revenue_chunk_found = False
    revenue_chunk_id = None

    for i, chunk in enumerate(page1_chunks, 1):
        text = chunk["text"][:200]  # First 200 chars
        print(f"\n  Chunk {i} (ID: {chunk['chunk_id']}, chunk_number: {chunk['chunk_number']}):")
        print(f"    {text}...")

        # Check if this chunk contains revenue info
        if "revenue" in text.lower() and "57.4" in text:
            revenue_chunk_found = True
            revenue_chunk_id = chunk["chunk_id"]
            print("    ✅ REVENUE CHUNK FOUND!")

    if not revenue_chunk_found:
        print("\n❌ PROBLEM: Revenue information not found in any page 1 chunk!")
        print("   This indicates a chunking issue - the revenue text was lost or split incorrectly.")
        return

    print(f"\n✅ Revenue chunk found: {revenue_chunk_id}")

    # Query 2: Get the full revenue chunk
    print("\n" + "=" * 80)
    print("STEP 2: Analyzing the revenue chunk content")
    print("=" * 80)

    revenue_chunks = collection.query(
        expr=f'chunk_id == "{revenue_chunk_id}"',
        output_fields=["chunk_id", "text", "page_number", "chunk_number", "embeddings"],
        limit=1,
    )

    if len(revenue_chunks) > 0:
        revenue_chunk = revenue_chunks[0]
        print("\n📝 Full revenue chunk text:")
        print(f"{revenue_chunk['text']}")
        print(f"\n   Page: {revenue_chunk['page_number']}, Chunk: {revenue_chunk['chunk_number']}")

    # Query 3: Perform a search to see what gets retrieved
    print("\n" + "=" * 80)
    print("STEP 3: Testing retrieval with search query")
    print("=" * 80)

    # We need to create an embedding for the query
    # For now, let's just see what the top chunks are sorted by their text relevance

    print("\n🔍 Searching for 'revenue' keyword in all chunks...")
    revenue_keyword_chunks = collection.query(
        expr='text like "%revenue%"', output_fields=["chunk_id", "text", "page_number", "chunk_number"], limit=10
    )

    print(f"\n✅ Found {len(revenue_keyword_chunks)} chunks containing 'revenue'")
    for i, chunk in enumerate(revenue_keyword_chunks, 1):
        text = chunk["text"][:150]
        print(f"\n  {i}. Page {chunk['page_number']}, Chunk {chunk['chunk_number']}:")
        print(f"     {text}...")

    # Query 4: Get info about the chunks that WERE retrieved
    print("\n" + "=" * 80)
    print("STEP 4: Analyzing the chunks that WERE retrieved by the search")
    print("=" * 80)

    retrieved_chunk_ids = [
        "352a9e26-3b60-4fcc-8ae3-155374e63f47",  # Page 141
        "7f7989e1-2e65-49d0-b75f-e99163856c6a",  # Page 6
        "3351f43d-5723-4df0-bc9d-5de480217516",  # Page 17
        "9e32a497-7396-4a1d-9a57-3effdb4843fc",  # Page 5
        "e7d1142e-bc3d-452e-9ccd-fb99f67710b8",  # Page 18
    ]

    print("\n🔍 Retrieved chunks (from test_search.py results):")
    for chunk_id in retrieved_chunk_ids:
        chunks = collection.query(
            expr=f'chunk_id == "{chunk_id}"', output_fields=["chunk_id", "text", "page_number"], limit=1
        )
        if chunks:
            chunk = chunks[0]
            print(f"\n  📄 Page {chunk['page_number']}: {chunk['text'][:100]}...")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if revenue_chunk_found:
        print("\n✅ Document parsed correctly: Revenue chunk exists")
        print("❌ Problem is in RETRIEVAL: Revenue chunk not returned in top 5 results")
        print("\nPossible causes:")
        print("  1. EMBEDDING ISSUE: Query embedding doesn't match revenue chunk embedding")
        print("  2. RETRIEVAL PARAMETERS: top_k=5 is too small, revenue chunk ranked 6th or lower")
        print("  3. EMBEDDING MODEL MISMATCH: Different models used for ingestion vs search")
        print("  4. VECTOR NORMALIZATION: Embeddings not normalized consistently")
    else:
        print("\n❌ Revenue chunk NOT found in page 1")
        print("\nPossible causes:")
        print("  1. DOCUMENT PARSING: Docling failed to extract page 1")
        print("  2. CHUNKING: Revenue text was split across chunks and lost context")

    connections.disconnect("default")


if __name__ == "__main__":
    asyncio.run(main())
