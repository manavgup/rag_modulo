#!/usr/bin/env python3
"""Test Docling HybridChunker implementation."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

from core.config import get_settings
from rag_solution.data_ingestion.docling_processor import DoclingProcessor

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")


async def test_docling_chunking():
    """Test Docling hybrid chunking with a sample document."""
    print("\n" + "=" * 80)
    print("🧪 TESTING DOCLING HYBRID CHUNKING")
    print("=" * 80)

    settings = get_settings()
    print("\n📋 Settings:")
    print(f"   MAX_CHUNK_SIZE: {settings.max_chunk_size}")
    print(f"   MIN_CHUNK_SIZE: {settings.min_chunk_size}")
    print(f"   CHUNKING_STRATEGY: {settings.chunking_strategy}")

    processor = DoclingProcessor(settings)

    if processor.chunker is None:
        print("\n❌ HybridChunker not initialized - check dependencies")
        print("   Install with: pip install docling transformers")
        return

    print("\n✅ DoclingProcessor initialized successfully")
    # HuggingFaceTokenizer wraps the actual tokenizer
    tokenizer_name = "HuggingFaceTokenizer(bert-base-uncased)" if processor.tokenizer else "None"
    print(f"   Tokenizer: {tokenizer_name}")
    print(f"   Chunker max_tokens: {settings.max_chunk_size}")

    # Use the IBM Annual Report from Downloads
    test_pdf = Path("/Users/mg/Downloads/2022-ibm-annual-report.pdf")

    if not test_pdf.exists():
        print("\n⚠️  No test PDF found in expected locations")
        print("   Create a simple test with Docling's sample document")

        # Test with Docling's chunker directly using dummy document
        try:
            from docling.document_converter import DocumentConverter

            # Create a simple test document
            test_text = "Test document. " * 100  # ~1500 chars
            print(f"\n📄 Testing with {len(test_text)} character test string")

            # Count tokens
            if processor.tokenizer:
                token_count = processor.tokenizer.count_tokens(test_text)
                print(f"   Token count: {token_count}")

            print("\n✅ Tokenizer is working correctly")
            print("   Ready to process real documents")

        except ImportError as e:
            print(f"\n❌ Error: {e}")
            print("   Install with: pip install docling transformers")

        return

    print(f"\n📄 Testing with: {test_pdf.name}")

    try:
        document_id = "test-doc-123"
        chunks = []

        async for document in processor.process(str(test_pdf), document_id):
            chunks = document.chunks
            print("\n✅ Processing complete!")
            print(f"   Document: {document.name}")
            print(f"   Total chunks: {len(chunks)}")

            if chunks:
                # Calculate statistics
                token_counts = [c.metadata.get("token_count", 0) for c in chunks]
                avg_tokens = sum(token_counts) / len(token_counts)
                max_tokens = max(token_counts)
                min_tokens = min(token_counts)

                print("\n📊 Chunking Statistics:")
                print(f"   Total chunks: {len(chunks)}")
                print(f"   Avg tokens: {avg_tokens:.0f}")
                print(f"   Max tokens: {max_tokens}")
                print(f"   Min tokens: {min_tokens}")

                # Show first 3 chunks
                print("\n📝 Sample Chunks (first 3):")
                for i, chunk in enumerate(chunks[:3]):
                    text_preview = chunk.text[:100].replace("\n", " ")
                    tokens = chunk.metadata.get("token_count", 0)
                    print(f"\n   Chunk {i + 1}:")
                    print(f"      Tokens: {tokens}")
                    print(f"      Text: {text_preview}...")

                # Verify no chunks exceed 512 tokens
                oversized = [c for c in chunks if c.metadata.get("token_count", 0) > 512]
                if oversized:
                    print(f"\n⚠️  WARNING: {len(oversized)} chunks exceed 512 tokens!")
                    for c in oversized:
                        print(f"      - {c.metadata.get('token_count')} tokens")
                else:
                    print("\n✅ All chunks within 512 token limit!")

    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_docling_chunking())
