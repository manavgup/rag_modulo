#!/usr/bin/env python3
"""
Direct Milvus embedding model comparison test.

This bypasses the entire RAG pipeline and tests embedding models directly
using their native APIs (WatsonX or sentence-transformers). This isolates
whether the issue is with the embedding models themselves or our pipeline.

Uses PRODUCTION chunking from backend/rag_solution/data_ingestion/chunking.py
with settings from .env to ensure realistic comparison.

Tests multiple embedding models:
- WatsonX models: IBM Slate 125M, IBM Slate 30M (via WatsonX API)
- Sentence Transformers: all-MiniLM-L6-v2, all-mpnet-base-v2, etc. (local)
"""

import json
import sys
from pathlib import Path

import numpy as np

# Add backend to path so we can import chunking
sys.path.insert(0, str(Path(__file__).parent.parent))

from ibm_watsonx_ai.foundation_models import Embeddings as wx_Embeddings
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)
from pymilvus.model.dense import SentenceTransformerEmbeddingFunction

from core.config import get_settings
from rag_solution.data_ingestion.chunking import get_chunking_method

# Test configuration
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
TEST_FILE = "/Users/mg/Downloads/2022-ibm-annual-report.txt"
TEST_QUERY = "What was IBM revenue in 2022?"
EXPECTED_TEXT = "60.5 billion"

# Embedding models to test
EMBEDDING_MODELS = [
    # WatsonX models
    {
        "name": "ibm-slate-125m-english-rtrvr",
        "type": "watsonx",
        "model_name": "ibm/slate-125m-english-rtrvr",
        "dimension": 768,
        "description": "IBM Slate 125M retriever (PRODUCTION)",
    },
    {
        "name": "ibm-slate-30m-english-rtrvr",
        "type": "watsonx",
        "model_name": "ibm/slate-30m-english-rtrvr",
        "dimension": 384,
        "description": "IBM Slate 30M retriever (smaller)",
    },
    # Sentence transformer models
    {
        "name": "all-MiniLM-L6-v2",
        "type": "sentence_transformer",
        "model_name": "all-MiniLM-L6-v2",
        "dimension": 384,
        "description": "Fast, lightweight model",
    },
    {
        "name": "all-mpnet-base-v2",
        "type": "sentence_transformer",
        "model_name": "all-mpnet-base-v2",
        "dimension": 768,
        "description": "High quality general purpose",
    },
    {
        "name": "multi-qa-MiniLM-L6-cos-v1",
        "type": "sentence_transformer",
        "model_name": "multi-qa-MiniLM-L6-cos-v1",
        "dimension": 384,
        "description": "Optimized for Q&A",
    },
    {
        "name": "paraphrase-multilingual-MiniLM-L12-v2",
        "type": "sentence_transformer",
        "model_name": "paraphrase-multilingual-MiniLM-L12-v2",
        "dimension": 384,
        "description": "Multilingual support",
    },
    {
        "name": "all-distilroberta-v1",
        "type": "sentence_transformer",
        "model_name": "all-distilroberta-v1",
        "dimension": 768,
        "description": "DistilRoBERTa based",
    },
]


def create_collection_schema(dimension: int) -> CollectionSchema:
    """Create Milvus collection schema matching our milvus_store.py schema."""
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=255),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension),
    ]
    return CollectionSchema(fields=fields, description="Direct embedding test collection")


def test_embedding_model(model_config: dict) -> dict:
    """Test a single embedding model."""
    print("\n" + "=" * 80)
    print(f"🧪 Testing: {model_config['name']}")
    print(f"   Type: {model_config['type']}")
    print(f"   Dimension: {model_config['dimension']}")
    print(f"   Description: {model_config['description']}")
    print("=" * 80)

    # Initialize embedding function
    print("📥 Loading embedding model...")
    embedding_fn = None
    wx_embed_client = None

    if model_config["type"] == "sentence_transformer":
        embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=model_config["model_name"],
            device="cpu",  # Use CPU for compatibility
        )
    elif model_config["type"] == "watsonx":
        # Create WatsonX embedding client
        settings = get_settings()
        embed_params = {
            EmbedParams.TRUNCATE_INPUT_TOKENS: 512,
            EmbedParams.RETURN_OPTIONS: {"input_text": False},
        }
        wx_embed_client = wx_Embeddings(
            persistent_connection=True,
            model_id=model_config["model_name"],
            params=embed_params,
            project_id=settings.wx_project_id,
            credentials={
                "apikey": settings.wx_api_key,
                "url": settings.wx_url,
            },
        )
        print(f"   ✅ WatsonX client created for {model_config['model_name']}")
    else:
        print(f"   ❌ Unsupported model type: {model_config['type']}")
        return None

    # Connect to Milvus
    print("🔌 Connecting to Milvus...")
    connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)

    collection_name = f"test_{model_config['name'].replace('-', '_')}"

    # Drop existing collection if exists
    if utility.has_collection(collection_name):
        print(f"   🗑️  Dropping existing collection: {collection_name}")
        utility.drop_collection(collection_name)

    # Create collection schema
    print(f"📚 Creating collection: {collection_name}")
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=255),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=model_config["dimension"]),
    ]
    schema = CollectionSchema(fields=fields, description=f"Test collection for {model_config['name']}")

    collection = Collection(name=collection_name, schema=schema)

    # Read and chunk document
    print("📄 Reading test document...")
    text = Path(TEST_FILE).read_text()

    # Get chunking settings from .env (production configuration)
    settings = get_settings()

    print("✂️  Chunking document using production chunking.py...")
    print(f"   Strategy: {settings.chunking_strategy}")
    print(f"   Max chunk size: {settings.max_chunk_size} chars")
    print(f"   Min chunk size: {settings.min_chunk_size} chars")
    print(f"   Overlap: {settings.chunk_overlap} chars")

    # Use production chunking method
    chunking_method = get_chunking_method(settings)
    chunks = chunking_method(text)
    print(f"   Created {len(chunks)} chunks")

    # Embed chunks
    print("🔢 Embedding chunks...")
    if model_config["type"] == "sentence_transformer":
        embeddings = embedding_fn.encode_documents(chunks)
    elif model_config["type"] == "watsonx":
        # Use WatsonX API to generate embeddings
        embeddings_list = wx_embed_client.embed_documents(texts=chunks, concurrency_limit=8)
        # Convert to numpy arrays
        embeddings = [np.array(emb) for emb in embeddings_list]
    print(f"   Generated {len(embeddings)} embeddings")

    # Insert data
    print("💾 Inserting data into Milvus...")
    entities = [
        [f"chunk_{i}" for i in range(len(chunks))],  # chunk_id
        chunks,  # text
        [embedding.tolist() for embedding in embeddings],  # vector
    ]

    collection.insert(entities)
    print(f"   ✅ Inserted {len(chunks)} vectors")

    # Flush to persist data
    print("💾 Flushing collection...")
    collection.flush()

    # Create index (matching milvus_store.py configuration)
    print("🔍 Creating IVF_FLAT index...")
    index_params = {
        "index_type": "IVF_FLAT",
        "metric_type": "COSINE",
        "params": {"nlist": 1024},
    }
    collection.create_index(field_name="vector", index_params=index_params)

    # Load collection
    print("📋 Loading collection...")
    collection.load()

    # Verify data count
    print(f"   ✅ Collection has {collection.num_entities} entities")

    if collection.num_entities == 0:
        print("   ❌ WARNING: Collection is empty! No data was inserted.")
        collection.release()
        utility.drop_collection(collection_name)
        connections.disconnect("default")
        return None

    # Search for query (matching milvus_store.py search params)
    print(f"🔎 Searching for: '{TEST_QUERY}'")
    if model_config["type"] == "sentence_transformer":
        query_embedding = embedding_fn.encode_queries([TEST_QUERY])[0]
    elif model_config["type"] == "watsonx":
        # Use WatsonX API to generate query embedding
        query_embeddings_list = wx_embed_client.embed_query(text=TEST_QUERY)
        query_embedding = np.array(query_embeddings_list)

    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    results = collection.search(
        data=[query_embedding.tolist()],
        anns_field="vector",
        param=search_params,
        limit=20,
        output_fields=["chunk_id", "text"],
    )

    # Debug: check what we got
    print(f"   🔍 Search returned {len(results)} hits")

    # Analyze results
    print("\n📊 Search Results:")
    revenue_chunk_rank = None
    revenue_chunk_score = None

    # Save all top 20 results to file
    results_file = Path(f"/tmp/milvus_direct_{model_config['name'].replace('-', '_')}_top20.txt")
    with open(results_file, "w") as f:
        f.write(f"Embedding Model: {model_config['name']}\n")
        f.write(f"Query: {TEST_QUERY}\n")
        f.write(f"Expected: {EXPECTED_TEXT}\n")
        f.write("=" * 80 + "\n\n")

        for rank, hit in enumerate(results[0], 1):
            chunk_text = hit.entity.get("text")
            score = hit.distance
            chunk_id = hit.entity.get("chunk_id")

            # Write to file
            f.write(f"RANK #{rank} - Score: {score:.4f} - Chunk ID: {chunk_id}\n")
            f.write(f"{chunk_text}\n")
            f.write("-" * 80 + "\n\n")

            # Check if this is the revenue chunk
            if EXPECTED_TEXT in chunk_text:
                revenue_chunk_rank = rank
                revenue_chunk_score = score
                print(f"   🎯 FOUND at rank #{rank} - Score: {score:.4f}")
                print(f"      Text preview: {chunk_text[:100]}...")
                f.write("*** REVENUE CHUNK FOUND ***\n\n")
            elif rank <= 5:
                print(f"   {rank}. Score: {score:.4f} - {chunk_text[:80]}...")

    print(f"   💾 Saved top 20 results to: {results_file}")

    if revenue_chunk_rank is None:
        print("   ❌ Revenue chunk NOT found in top 20 results")

    # Cleanup
    print("🧹 Cleaning up...")
    collection.release()
    utility.drop_collection(collection_name)
    connections.disconnect("default")

    return {
        "model": model_config["name"],
        "dimension": model_config["dimension"],
        "revenue_rank": revenue_chunk_rank,
        "revenue_score": revenue_chunk_score,
        "description": model_config["description"],
    }


def main():
    """Run direct Milvus embedding comparison test."""
    print("=" * 80)
    print("🔬 DIRECT MILVUS EMBEDDING MODEL COMPARISON")
    print("=" * 80)
    print(f"📄 Test Document: {TEST_FILE}")
    print(f"❓ Test Query: {TEST_QUERY}")
    print(f"✅ Expected Text: {EXPECTED_TEXT}")
    print(f"🔢 Testing {len(EMBEDDING_MODELS)} models")
    print(f"🔌 Milvus: {MILVUS_HOST}:{MILVUS_PORT}")
    print("=" * 80)

    # Check if test file exists
    if not Path(TEST_FILE).exists():
        print(f"❌ Test file not found: {TEST_FILE}")
        return

    # Test each model
    results = []
    for model_config in EMBEDDING_MODELS:
        try:
            result = test_embedding_model(model_config)
            if result:
                results.append(result)
        except Exception as e:
            print(f"   ❌ Error testing {model_config['name']}: {e}")
            import traceback

            traceback.print_exc()

    # Print summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY - RANKING COMPARISON")
    print("=" * 80)

    # Sort by rank (None comes last)
    results.sort(key=lambda x: (x["revenue_rank"] is None, x["revenue_rank"] or 999))

    print("\n🏆 Models that FOUND the revenue chunk:")
    found_count = 0
    for result in results:
        if result["revenue_rank"] is not None:
            found_count += 1
            print(
                f"   {found_count}. {result['model']:<40} Rank: #{result['revenue_rank']:<3} Score: {result['revenue_score']:.4f}"
            )
            print(f"      {result['description']}")

    if found_count == 0:
        print("   ❌ NO models found the revenue chunk!")

    print(f"\n❌ Models that DID NOT find the revenue chunk ({len(results) - found_count}):")
    for result in results:
        if result["revenue_rank"] is None:
            print(f"   • {result['model']} - {result['description']}")

    # Save results to JSON
    output_file = Path(__file__).parent.parent / "milvus_direct_embedding_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

    # Recommendation
    if found_count > 0:
        best = results[0]
        print("\n" + "=" * 80)
        print("💡 RECOMMENDATION")
        print("=" * 80)
        print(f"   Best model: {best['model']}")
        print(f"   Revenue chunk rank: #{best['revenue_rank']}")
        print(f"   Score: {best['revenue_score']:.4f}")
        print(f"   Dimension: {best['dimension']}")
        print(f"   Description: {best['description']}")
        print("\n   This model should be considered for production use.")


if __name__ == "__main__":
    main()
