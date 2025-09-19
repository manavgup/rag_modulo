#!/usr/bin/env python3
"""Debug script to examine Milvus vector database content."""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))

from pymilvus import connections, Collection, utility
from core.config import get_settings
from vectordbs.data_types import VectorQuery
from vectordbs.factory import VectorStoreFactory

def main():
    """Examine Milvus database content for collection 40."""

    # Get settings and connect to Milvus
    settings = get_settings()

    # Connect to Milvus - use localhost since port is exposed
    connections.connect(
        alias="default",
        host="localhost",
        port=19530
    )

    print("Connected to Milvus")

    # List all collections
    collections = utility.list_collections()
    print(f"Available collections: {collections}")

    # Target collection for AI_Agents_Demo_20250917_004116
    target_collection = "collection_4db3f44637fd456fbc652b033cda98e7"

    if target_collection not in collections:
        print(f"Target collection {target_collection} not found")
        print(f"Available: {collections}")
        return

    print(f"Using collection: {target_collection}")

    # Get collection info
    collection = Collection(target_collection)
    print(f"Collection schema: {collection.schema}")
    print(f"Collection count: {collection.num_entities}")

    # Load the collection
    collection.load()

    # Search for some sample documents
    query_vectors = [[0.1] * 384]  # Dummy vector for testing (384 dims)

    search_params = {
        "metric_type": "COSINE",
        "params": {"nprobe": 10}
    }

    # Get sample results
    results = collection.search(
        data=query_vectors,
        anns_field="embedding",
        param=search_params,
        limit=10,
        expr=None,
        output_fields=["text", "document_id", "chunk_id", "document_name", "page_number", "chunk_number"]
    )

    print("\nSample chunks in the collection:")
    for i, hits in enumerate(results):
        print(f"\nQuery {i}:")
        for j, hit in enumerate(hits):
            print(f"  Chunk {j} (score: {hit.score:.3f}):")
            print(f"    Document ID: {hit.entity.get('document_id')}")
            print(f"    Document Name: {hit.entity.get('document_name')}")
            print(f"    Chunk ID: {hit.entity.get('chunk_id')}")
            print(f"    Page: {hit.entity.get('page_number')}, Chunk: {hit.entity.get('chunk_number')}")
            text = hit.entity.get('text') or ''
            print(f"    Text length: {len(text)}")
            print(f"    Text content: {text[:500]}...")
            if len(text) > 500:
                print(f"    ... (truncated, full length: {len(text)})")
            print()

if __name__ == "__main__":
    main()