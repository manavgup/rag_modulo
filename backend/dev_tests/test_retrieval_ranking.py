#!/usr/bin/env python3
"""
Test where the revenue chunk ranks in search results
"""

from pymilvus import Collection, connections
from sentence_transformers import SentenceTransformer

from core.config import get_settings


def main():
    settings = get_settings()

    # Connect to Milvus
    print("🔌 Connecting to Milvus...")
    connections.connect(alias="default", host=settings.milvus_host, port=settings.milvus_port)

    collection_name = "collection_9c26cf34bb304e00a11f017ed63671f0"
    print(f"📚 Testing retrieval for collection: {collection_name}")

    collection = Collection(collection_name)
    collection.load()

    # Initialize embedding model
    embedding_model_name = settings.embedding_model
    print(f"\n🤖 Initializing embedding model: {embedding_model_name}")
    embedding_model = SentenceTransformer(embedding_model_name)

    # Create query embedding
    query = "What was IBM revenue in 2021?"
    print(f"\n🔍 Query: {query}")
    query_embedding = embedding_model.encode(query).tolist()
    print(f"✅ Generated embedding with {len(query_embedding)} dimensions")

    # Search with a larger top_k to see full ranking
    print("\n📊 Searching for top 20 results...")
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

    results = collection.search(
        data=[query_embedding],
        anns_field="embeddings",
        param=search_params,
        limit=20,
        output_fields=["chunk_id", "text", "page_number", "chunk_number"],
    )

    # Revenue chunk ID (we know this from our earlier investigation)
    revenue_chunk_id = None  # We'll identify it by content

    print("\n📋 Top 20 Results:")
    print("=" * 100)

    for rank, result in enumerate(results[0], 1):
        chunk_id = result.entity.get("chunk_id")
        text = result.entity.get("text", "")[:150]
        page_num = result.entity.get("page_number")
        chunk_num = result.entity.get("chunk_number")
        score = result.distance

        # Check if this is the revenue chunk
        is_revenue = "57.4" in text and "revenue" in text.lower()
        marker = " ← REVENUE CHUNK!" if is_revenue else ""

        print(f"\n{rank}. Score: {score:.4f} | Page {page_num}, Chunk {chunk_num}{marker}")
        print(f"   {text}...")

        if is_revenue:
            revenue_chunk_id = chunk_id
            print(f"   ✅ FOUND REVENUE CHUNK AT RANK {rank}")

    print("\n" + "=" * 100)
    print("ANALYSIS")
    print("=" * 100)

    if revenue_chunk_id:
        rank = None
        for i, result in enumerate(results[0], 1):
            if result.entity.get("chunk_id") == revenue_chunk_id:
                rank = i
                break

        if rank:
            print(f"\n✅ Revenue chunk found at rank {rank}")
            if rank <= 5:
                print("   → This chunk SHOULD be in the top 5 results")
                print("   → Problem likely with the test or configuration")
            else:
                print("   → This chunk is OUTSIDE the top 5 results (default top_k=5)")
                print("   → This explains why it's not being retrieved!")
                print("\nPOSSIBLE CAUSES:")
                print("  1. EMBEDDING MODEL: Query embedding doesn't match document embedding well")
                print("  2. QUERY REWRITING: The rewritten query may not match as well")
                print("  3. TOP_K TOO SMALL: top_k=5 is insufficient for this collection")
                print("  4. EMBEDDING QUALITY: Document chunking may have hurt embedding quality")
    else:
        print("\n❌ Revenue chunk NOT found in top 20 results!")
        print("   This indicates a serious embedding or indexing problem")

    connections.disconnect("default")


if __name__ == "__main__":
    main()
