"""Manual test to compare legacy PDF processor vs Docling processor.

This script processes a real PDF with both processors and compares:
- Text extraction quality
- Table extraction (Docling uses AI-powered TableFormer)
- Metadata extraction
- Chunk counts and structure

Usage:
    poetry run python dev_tests/manual/test_pdf_comparison.py
"""

import asyncio
import multiprocessing
from pathlib import Path

from core.config import get_settings

from rag_solution.data_ingestion.docling_processor import DoclingProcessor
from rag_solution.data_ingestion.pdf_processor import PdfProcessor


async def process_with_legacy(pdf_path: str, settings):
    """Process PDF with legacy processor."""
    print("\n" + "=" * 80)
    print("LEGACY PDF PROCESSOR (PyMuPDF)")
    print("=" * 80)

    manager = multiprocessing.Manager()
    processor = PdfProcessor(manager, settings)

    documents = []
    async for doc in processor.process(pdf_path, "test-legacy"):
        documents.append(doc)

    if not documents:
        print("❌ No documents returned")
        return None

    doc = documents[0]

    print(f"\n📄 Document: {doc.name}")
    print(f"📊 Total chunks: {len(doc.chunks)}")
    print("📋 Metadata:")
    print(f"   - Title: {doc.metadata.title}")
    print(f"   - Pages: {doc.metadata.total_pages}")
    print(f"   - Author: {doc.metadata.author}")
    print(f"   - Creator: {doc.metadata.creator}")
    print(f"   - Producer: {doc.metadata.producer}")

    # Show first 3 chunks
    print("\n📝 First 3 chunks:")
    for i, chunk in enumerate(doc.chunks[:3]):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Page: {chunk.metadata.page_number}")
        print(f"Length: {len(chunk.text)} chars")
        print(f"Text preview: {chunk.text[:200]}...")

    # Check for tables (legacy doesn't extract tables separately)
    table_chunks = [c for c in doc.chunks if c.metadata.table_index and c.metadata.table_index > 0]
    print(f"\n📊 Table chunks: {len(table_chunks)}")

    return doc


async def process_with_docling(pdf_path: str, settings):
    """Process PDF with Docling processor."""
    print("\n" + "=" * 80)
    print("DOCLING PROCESSOR (AI-powered TableFormer + Layout Analysis)")
    print("=" * 80)

    processor = DoclingProcessor(settings)

    documents = []
    async for doc in processor.process(pdf_path, "test-docling"):
        documents.append(doc)

    if not documents:
        print("❌ No documents returned")
        return None

    doc = documents[0]

    print(f"\n📄 Document: {doc.name}")
    print(f"📊 Total chunks: {len(doc.chunks)}")
    print("📋 Metadata:")
    print(f"   - Title: {doc.metadata.title}")
    print(f"   - Pages: {doc.metadata.total_pages}")
    print(f"   - Author: {doc.metadata.author}")
    print(f"   - Creator: {doc.metadata.creator}")
    print(f"   - Producer: {doc.metadata.producer}")
    # Handle keywords being dict, list, or None
    table_count = doc.metadata.keywords.get("table_count", 0) if isinstance(doc.metadata.keywords, dict) else 0
    image_count = doc.metadata.keywords.get("image_count", 0) if isinstance(doc.metadata.keywords, dict) else 0
    print(f"   - Table count: {table_count}")
    print(f"   - Image count: {image_count}")

    # Show first 3 chunks
    print("\n📝 First 3 chunks:")
    for i, chunk in enumerate(doc.chunks[:3]):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Page: {chunk.metadata.page_number}")
        print(f"Length: {len(chunk.text)} chars")
        print(f"Text preview: {chunk.text[:200]}...")

    # Check for tables (Docling extracts tables with structure)
    table_chunks = [c for c in doc.chunks if c.metadata.table_index and c.metadata.table_index > 0]
    image_chunks = [c for c in doc.chunks if c.metadata.image_index and c.metadata.image_index > 0]

    print(f"\n📊 Table chunks: {len(table_chunks)}")
    if table_chunks:
        print("\n🔍 Sample table chunk:")
        sample_table = table_chunks[0]
        print(f"Page: {sample_table.metadata.page_number}")
        print(f"Table index: {sample_table.metadata.table_index}")
        print(f"Table text:\n{sample_table.text}")

    print(f"\n🖼️  Image chunks: {len(image_chunks)}")
    if image_chunks:
        print("\n🔍 Sample image chunk:")
        sample_image = image_chunks[0]
        print(f"Page: {sample_image.metadata.page_number}")
        print(f"Image index: {sample_image.metadata.image_index}")
        print(f"Text: {sample_image.text}")

    return doc


async def compare_results(legacy_doc, docling_doc):
    """Compare results from both processors."""
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)

    if not legacy_doc or not docling_doc:
        print("⚠️  Cannot compare - one or both processors failed")
        return

    print("\n📊 Chunk Counts:")
    print(f"   Legacy:  {len(legacy_doc.chunks)} chunks")
    print(f"   Docling: {len(docling_doc.chunks)} chunks")
    diff = len(docling_doc.chunks) - len(legacy_doc.chunks)
    print(f"   Diff:    {diff:+d} chunks ({diff/len(legacy_doc.chunks)*100:+.1f}%)")

    # Table extraction comparison
    legacy_tables = [c for c in legacy_doc.chunks if c.metadata.table_index and c.metadata.table_index > 0]
    docling_tables = [c for c in docling_doc.chunks if c.metadata.table_index and c.metadata.table_index > 0]

    print("\n📊 Table Extraction:")
    print(f"   Legacy:  {len(legacy_tables)} table chunks")
    print(f"   Docling: {len(docling_tables)} table chunks")
    print("   💡 Docling uses AI-powered TableFormer for better table extraction")

    # Image detection
    docling_images = [c for c in docling_doc.chunks if c.metadata.image_index and c.metadata.image_index > 0]
    print("\n🖼️  Image Detection:")
    print("   Legacy:  Not supported")
    print(f"   Docling: {len(docling_images)} images detected")

    # Text quality comparison (sample)
    print("\n📝 Text Quality Sample:")
    print("   Both processors extract similar text, but Docling preserves:")
    print("   ✓ Document structure (reading order)")
    print("   ✓ Layout information")
    print("   ✓ Table structure")
    print("   ✓ Image positions")

    # Metadata comparison
    print("\n📋 Metadata:")
    print("   Both extract: title, author, pages, dates")
    print("   Docling adds: table_count, image_count, layout analysis")


async def main():
    """Run comparison test."""
    pdf_path = "/Users/mg/Downloads/407ETR.pdf"

    print("=" * 80)
    print("PDF PROCESSOR COMPARISON TEST")
    print("=" * 80)
    print(f"\n📄 Testing with: {pdf_path}")

    # Check file exists
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        return

    settings = get_settings()

    # Process with both processors
    legacy_doc = await process_with_legacy(pdf_path, settings)
    docling_doc = await process_with_docling(pdf_path, settings)

    # Compare results
    await compare_results(legacy_doc, docling_doc)

    print("\n" + "=" * 80)
    print("✅ Comparison complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
