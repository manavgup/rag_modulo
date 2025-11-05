#!/usr/bin/env python3
"""Direct test of embedding model retrieval quality.

Bypasses the entire pipeline to test embeddings + Milvus directly.
"""
import sys
from pathlib import Path
from uuid import UUID

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from pymilvus import Collection, connections
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.file_management.database import get_db
from rag_solution.generation.providers.factory import LLMProviderFactory


def test_direct_retrieval():
    """Test retrieval directly against Milvus using embeddings."""

    # Initialize settings
    settings = Settings()

    # Configuration
    collection_id = "2cae53c2-4a7e-444a-a12c-ca6831a31426"
    collection_name = "collection_ff10bd809b964b8bbd1b2f86299e1e71"  # Milvus collection name for "IBM"

    # Test queries
    queries = [
        "What services did IBM offer for free during the COVID-19 pandemic?",
        "IBM Watson COVID-19 pandemic free services",
        "COVID-19 virtual agent",
        "IBM revenue 2020",  # Control query that should work
    ]

    print("=" * 80)
    print("DIRECT EMBEDDING + MILVUS RETRIEVAL TEST")
    print("=" * 80)
    print(f"\nCollection: {collection_name}")
    print(f"Collection ID: {collection_id}")
    print(f"Testing {len(queries)} queries\n")

    # Initialize WatsonX provider using factory
    print("Initializing WatsonX provider via factory...")
    try:
        db: Session = next(get_db())
        factory = LLMProviderFactory(db)
        provider = factory.get_provider("watsonx")
        print(f"✅ WatsonX provider initialized")
        print(f"   Provider: {provider._provider_name}")

    except Exception as e:
        print(f"❌ Failed to initialize provider: {e}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.close()
        return

    # Connect to Milvus
    print(f"Connecting to Milvus at {settings.milvus_host}:{settings.milvus_port}...")
    try:
        connections.connect(
            alias="default",
            host=settings.milvus_host,
            port=settings.milvus_port,
        )
    except Exception as e:
        print(f"❌ Failed to connect to Milvus: {e}")
        return

    # Load collection
    print(f"Loading collection '{collection_name}'...\n")
    try:
        collection = Collection(collection_name)
        collection.load()
    except Exception as e:
        print(f"❌ Failed to load collection: {e}")
        connections.disconnect("default")
        return

    # Test each query
    for i, query in enumerate(queries, 1):
        print("=" * 80)
        print(f"Query {i}: {query}")
        print("=" * 80)

        # Get embeddings for query
        print("Getting embeddings for query...")
        try:
            embeddings = provider.get_embeddings([query])
            query_embedding = embeddings[0] if isinstance(embeddings, list) else embeddings
        except Exception as e:
            print(f"❌ Failed to get embeddings: {e}")
            import traceback
            traceback.print_exc()
            continue

        print(f"Embedding dimension: {len(query_embedding)}")
        print(f"Embedding sample (first 5 values): {query_embedding[:5]}")

        # Search Milvus directly
        print("\nSearching Milvus...")
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }

        try:
            results = collection.search(
                data=[query_embedding],
                anns_field=settings.embedding_field,  # Use dynamic field name from settings
                param=search_params,
                limit=10,
                output_fields=["text", "document_name", "page_number", "chunk_number"],
            )
        except Exception as e:
            print(f"❌ Search failed: {e}")
            import traceback
            traceback.print_exc()
            continue

        # Display results
        print(f"\nTop 10 Results:")
        print("-" * 80)

        if not results or len(results) == 0 or len(results[0]) == 0:
            print("❌ NO RESULTS FOUND")
        else:
            for j, hit in enumerate(results[0], 1):
                # Use getattr() to access entity fields (correct pymilvus API)
                entity = hit.entity
                score = hit.score
                text = getattr(entity, "text", "")[:150]
                doc_name = getattr(entity, "document_name", "unknown")
                page = getattr(entity, "page_number", "?")
                chunk = getattr(entity, "chunk_number", "?")

                print(f"{j}. Score: {score:.4f} | Page: {page} | Chunk: {chunk}")
                print(f"   Doc: {doc_name}")
                print(f"   Text: {text}...")
                print()

        print("\n")

    # Cleanup
    print("=" * 80)
    print("Disconnecting from Milvus...")
    connections.disconnect("default")
    print("Closing database session...")
    db.close()
    print("✅ Test complete!")


if __name__ == "__main__":
    test_direct_retrieval()
