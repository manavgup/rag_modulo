#!/usr/bin/env python3
"""
Debug script to test chunking and embedding directly.

This bypasses the backend API and directly tests:
1. Reading the TXT file
2. Chunking the text
3. Calling WatsonX embedding API
4. Identifying which chunks fail
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

import os

from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import Embeddings

from core.config import get_settings

# Import our chunking code
from rag_solution.data_ingestion.chunking import sentence_chunker, simple_chunking


def read_txt_file(file_path: str) -> str:
    """Read text file."""
    with open(file_path, encoding="utf-8") as f:
        return f.read()


def test_chunking_and_embedding():
    """Test chunking and embedding step by step."""

    # Load settings
    load_dotenv()
    settings = get_settings()

    print("=" * 80)
    print("🔍 CHUNKING AND EMBEDDING DEBUG TEST")
    print("=" * 80)

    # Configuration
    txt_file = "/Users/mg/Downloads/2022-ibm-annual-report.txt"
    embedding_model = os.getenv("EMBEDDING_MODEL", "ibm/slate-125m-english-rtrvr-v2")

    # Chunking config from .env
    min_chunk_size = int(os.getenv("MIN_CHUNK_SIZE", "375"))
    max_chunk_size = int(os.getenv("MAX_CHUNK_SIZE", "750"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "100"))
    chunking_strategy = os.getenv("CHUNKING_STRATEGY", "sentence")

    print("\n📋 Configuration:")
    print(f"   File: {txt_file}")
    print(f"   Embedding Model: {embedding_model}")
    print(f"   Chunking Strategy: {chunking_strategy}")
    print(f"   MIN_CHUNK_SIZE: {min_chunk_size}")
    print(f"   MAX_CHUNK_SIZE: {max_chunk_size}")
    print(f"   CHUNK_OVERLAP: {chunk_overlap}")

    # Step 1: Read file
    print("\n📄 Step 1: Reading file...")
    text = read_txt_file(txt_file)
    print(f"   ✅ Read {len(text)} characters")
    print(f"   Preview: {text[:200]}...")

    # Step 2: Chunk the text
    print("\n✂️  Step 2: Chunking text...")

    if chunking_strategy == "sentence":
        try:
            chunks = sentence_chunker(
                text=text, min_chunk_size=min_chunk_size, max_chunk_size=max_chunk_size, overlap=chunk_overlap
            )
        except Exception as e:
            print(f"   ⚠️  sentence_chunker failed, falling back to simple_chunking: {e}")
            chunks = simple_chunking(
                text=text, min_chunk_size=min_chunk_size, max_chunk_size=max_chunk_size, overlap=chunk_overlap
            )
    else:
        chunks = simple_chunking(
            text=text, min_chunk_size=min_chunk_size, max_chunk_size=max_chunk_size, overlap=chunk_overlap
        )

    print(f"   ✅ Created {len(chunks)} chunks")
    print("\n   📊 Chunk size distribution:")
    chunk_sizes = [len(c) for c in chunks]
    print(f"      Min: {min(chunk_sizes)} chars")
    print(f"      Max: {max(chunk_sizes)} chars")
    print(f"      Avg: {sum(chunk_sizes) / len(chunk_sizes):.0f} chars")

    # Show first 3 chunks
    print("\n   📝 First 3 chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"      Chunk {i + 1} ({len(chunk)} chars): {chunk[:100]}...")

    # Step 3: Setup WatsonX client
    print("\n🔧 Step 3: Setting up WatsonX client...")
    credentials = Credentials(
        url=settings.wx_url,
        api_key=settings.wx_api_key,
    )
    client = APIClient(credentials=credentials, project_id=settings.wx_project_id)

    embeddings_client = Embeddings(
        model_id=embedding_model,
        credentials=credentials,
        project_id=settings.wx_project_id,
    )
    print("   ✅ Client initialized")

    # Step 4: Test embedding small batch
    print("\n🧪 Step 4: Testing embedding with first 5 chunks...")
    test_chunks = chunks[:5]

    try:
        embeddings = embeddings_client.embed_documents(texts=test_chunks)
        print(f"   ✅ Successfully embedded {len(test_chunks)} chunks")
        print(f"   Embedding dimension: {len(embeddings[0])}")
    except Exception as e:
        print("   ❌ Failed to embed first 5 chunks:")
        print(f"   Error: {e!s}")

        # Try to identify problematic chunks
        print("\n   🔍 Testing each chunk individually...")
        for i, chunk in enumerate(test_chunks):
            try:
                emb = embeddings_client.embed_documents(texts=[chunk])
                print(f"      Chunk {i + 1} ({len(chunk)} chars): ✅ OK")
            except Exception as chunk_error:
                print(f"      Chunk {i + 1} ({len(chunk)} chars): ❌ FAILED")
                print(f"         Error: {str(chunk_error)[:200]}")
                print(f"         Preview: {chunk[:200]}")
        return

    # Step 5: Test embedding ALL chunks in batches
    print(f"\n🚀 Step 5: Testing embedding ALL {len(chunks)} chunks...")
    batch_size = 10
    failed_chunks = []
    succeeded_count = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        try:
            embeddings = embeddings_client.embed_documents(texts=batch)
            succeeded_count += len(batch)
            print(f"   ✅ Batch {batch_num}/{total_batches}: {len(batch)} chunks OK")
        except Exception as e:
            print(f"   ❌ Batch {batch_num}/{total_batches} FAILED:")
            print(f"      Error: {str(e)[:200]}")

            # Test each chunk in the failed batch individually
            print("      🔍 Testing chunks individually in failed batch...")
            for j, chunk in enumerate(batch):
                chunk_idx = i + j
                try:
                    embeddings_client.embed_documents(texts=[chunk])
                    print(f"         Chunk {chunk_idx + 1} ({len(chunk)} chars): ✅ OK")
                except Exception as chunk_error:
                    print(f"         Chunk {chunk_idx + 1} ({len(chunk)} chars): ❌ FAILED")
                    error_msg = str(chunk_error)
                    if "Token sequence length" in error_msg:
                        print("            ⚠️  TOKEN LIMIT EXCEEDED")
                    print(f"            Error: {error_msg[:150]}")
                    failed_chunks.append(
                        {"index": chunk_idx, "size": len(chunk), "text": chunk[:200], "error": error_msg[:200]}
                    )

    # Summary
    print("\n" + "=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    print(f"Total chunks: {len(chunks)}")
    print(f"Successfully embedded: {succeeded_count}")
    print(f"Failed chunks: {len(failed_chunks)}")

    if failed_chunks:
        print("\n❌ FAILED CHUNKS DETAILS:")
        for fail in failed_chunks[:10]:  # Show first 10 failures
            print(f"\n   Chunk #{fail['index'] + 1} ({fail['size']} chars):")
            print(f"   Error: {fail['error']}")
            print(f"   Preview: {fail['text']}...")

        # Analyze patterns
        print("\n🔍 FAILURE ANALYSIS:")
        token_limit_failures = sum(1 for f in failed_chunks if "Token sequence length" in f["error"])
        if token_limit_failures > 0:
            print(f"   ⚠️  {token_limit_failures} chunks exceeded token limits")
            print(f"   💡 Current MAX_CHUNK_SIZE ({max_chunk_size} chars) is too large")
            print("   💡 Recommendation: Reduce MAX_CHUNK_SIZE to 500 or less")
    else:
        print("\n✅ ALL CHUNKS EMBEDDED SUCCESSFULLY!")
        print("   Current chunking configuration works well for this model.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_chunking_and_embedding()
