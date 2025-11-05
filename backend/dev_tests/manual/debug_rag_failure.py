"""Debug script for RAG failure in IBMIBM collection."""

import asyncio
import logging
from uuid import UUID

from core.config import get_settings
from rag_solution.repository.collection_repository import CollectionRepository
from rag_solution.repository.document_repository import DocumentRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_collection():
    """Debug the IBMIBM collection to understand the RAG failure."""
    settings = get_settings()
    collection_id = UUID("24607b4b-6338-4d9b-82e7-b878cb7a605f")

    print("=" * 80)
    print("🔍 DEBUG SCRIPT FOR RAG FAILURE")
    print("=" * 80)

    # Check 1: Is docling enabled?
    print(f"\n1. ENABLE_DOCLING setting: {settings.enable_docling}")
    print(f"   DOCLING_FALLBACK_ENABLED: {settings.docling_fallback_enabled}")

    # Check 2: What's in the collection?
    coll_repo = CollectionRepository()
    collection = await coll_repo.get_collection(collection_id)

    if not collection:
        print(f"\n❌ ERROR: Collection {collection_id} not found!")
        return

    print("\n2. Collection Info:")
    print(f"   Name: {collection.name}")
    print(f"   Description: {collection.description}")

    # Check 3: What documents are in the collection?
    doc_repo = DocumentRepository()
    documents = await doc_repo.get_documents_by_collection(collection_id)

    print(f"\n3. Documents in collection: {len(documents)}")

    for i, doc in enumerate(documents[:10], 1):  # Show first 10
        print(f"\n   Document {i}:")
        print(f"   - ID: {doc.document_id}")
        print(f"   - Name: {doc.name}")
        print(f"   - File type: {doc.file_type if hasattr(doc, 'file_type') else 'N/A'}")

        # Get full document with chunks
        full_doc = await doc_repo.get_document(doc.document_id)
        if full_doc and hasattr(full_doc, "chunks"):
            chunks = full_doc.chunks
            print(f"   - Chunks: {len(chunks)}")

            if chunks:
                # Show first chunk
                first_chunk = chunks[0]
                print("   - First chunk preview (200 chars):")
                print(f"     {first_chunk.text[:200]}...")

                # Check if chunks contain "revenue" or "IBM"
                revenue_chunks = [c for c in chunks if "revenue" in c.text.lower()]
                print(f"   - Chunks mentioning 'revenue': {len(revenue_chunks)}")

                if revenue_chunks:
                    print("   - First revenue chunk (300 chars):")
                    print(f"     {revenue_chunks[0].text[:300]}...")

    # Check 4: Check vector store (Milvus) connection
    print("\n4. Vector Store Configuration:")
    print(f"   Type: {settings.vector_db}")
    print(f"   Milvus Host: {settings.milvus_host}")
    print(f"   Milvus Port: {settings.milvus_port}")

    # Check 5: Check embedding model
    print("\n5. Embedding Configuration:")
    print(f"   Model: {settings.embedding_model}")
    print(f"   Provider: {settings.embedding_provider}")

    print("\n" + "=" * 80)
    print("DEBUG SCRIPT COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_collection())
