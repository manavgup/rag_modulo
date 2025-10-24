#!/usr/bin/env python3
"""Verify that all chunks are within token limits for embedding models."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from transformers import AutoTokenizer

from core.config import get_settings
from rag_solution.data_ingestion.docling_processor import DoclingProcessor

load_dotenv(Path(__file__).parent.parent / ".env")


async def verify_chunks():
    """Process document and verify all chunks are within token limits."""
    print("\n" + "=" * 80)
    print("🔍 VERIFYING CHUNK TOKEN LIMITS")
    print("=" * 80)

    settings = get_settings()
    processor = DoclingProcessor(settings)

    if processor.chunker is None:
        print("\n❌ HybridChunker not initialized")
        return

    # Use IBM Annual Report
    test_pdf = Path("/Users/mg/Downloads/2022-ibm-annual-report.pdf")
    if not test_pdf.exists():
        print(f"\n❌ Test file not found: {test_pdf}")
        return

    print(f"\n📄 Processing: {test_pdf.name}")

    # Initialize our own tokenizer to double-check
    bert_tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

    document_id = "verify-test"
    all_chunks = []

    async for document in processor.process(str(test_pdf), document_id):
        all_chunks = document.chunks

    print(f"\n✅ Created {len(all_chunks)} chunks")

    # Verify each chunk with direct tokenization
    oversized_chunks = []
    warning_chunks = []  # Chunks > 400 tokens (safe limit)

    for idx, chunk in enumerate(all_chunks):
        # Count tokens using BERT tokenizer
        tokens = bert_tokenizer.encode(chunk.text, add_special_tokens=True)
        token_count = len(tokens)

        if token_count > 512:
            oversized_chunks.append((idx, token_count, chunk.text[:100]))
        elif token_count > 400:
            warning_chunks.append((idx, token_count, chunk.text[:100]))

    print("\n📊 Verification Results:")
    print(f"   Total chunks: {len(all_chunks)}")
    print(f"   Chunks > 512 tokens (WILL FAIL): {len(oversized_chunks)}")
    print(f"   Chunks > 400 tokens (WARNING): {len(warning_chunks)}")

    if oversized_chunks:
        print(f"\n❌ CRITICAL: {len(oversized_chunks)} chunks exceed 512 token limit!")
        print("   These will fail during embedding generation:")
        for idx, tokens, preview in oversized_chunks[:5]:
            print(f"   - Chunk {idx}: {tokens} tokens")
            print(f"     Preview: {preview}...")
    elif warning_chunks:
        print(f"\n⚠️  {len(warning_chunks)} chunks between 400-512 tokens (risky)")
        print("   These might occasionally fail with some tokenizers:")
        for idx, tokens, preview in warning_chunks[:5]:
            print(f"   - Chunk {idx}: {tokens} tokens")
            print(f"     Preview: {preview}...")
    else:
        print("\n✅ All chunks safely under 400 token limit!")

    # Calculate statistics
    if all_chunks:
        token_counts = [len(bert_tokenizer.encode(c.text, add_special_tokens=True)) for c in all_chunks]
        avg_tokens = sum(token_counts) / len(token_counts)
        max_tokens = max(token_counts)
        min_tokens = min(token_counts)

        print("\n📈 Token Statistics:")
        print(f"   Average: {avg_tokens:.1f} tokens")
        print(f"   Maximum: {max_tokens} tokens")
        print(f"   Minimum: {min_tokens} tokens")

        # Show distribution
        ranges = [
            (0, 100, "0-100"),
            (100, 200, "100-200"),
            (200, 300, "200-300"),
            (300, 400, "300-400"),
            (400, 512, "400-512"),
            (512, 10000, ">512"),
        ]

        print("\n📊 Distribution:")
        for low, high, label in ranges:
            count = sum(1 for t in token_counts if low <= t < high)
            if count > 0:
                pct = (count / len(token_counts)) * 100
                bar = "█" * int(pct / 2)
                print(f"   {label:>10}: {count:4d} ({pct:5.1f}%) {bar}")


if __name__ == "__main__":
    asyncio.run(verify_chunks())
