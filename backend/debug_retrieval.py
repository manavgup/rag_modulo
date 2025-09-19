#!/usr/bin/env python3
"""Debug script to examine retrieval results for collection 40."""

import asyncio
import os
import sys

# Add the backend directory to sys.path to enable imports
backend_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, backend_dir)

from core.config import get_settings
from core.database import get_database_url
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.search_service import SearchService


async def main():
    """Debug retrieval for collection 40."""

    settings = get_settings()

    # Create database session
    engine = create_engine(get_database_url(settings))
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # Initialize search service
    search_service = SearchService(db, settings)

    # Create search input for the problematic query
    search_input = SearchInput(
        question="What are the restrictions on the use and distribution of the information provided?",
        collection_id="af04fe36-ecd2-42c4-b7c6-a13a6e1327d2",
        user_id="00000000-0000-0000-0000-000000000001",  # Mock user ID
    )

    try:
        print("=== DEBUGGING RETRIEVAL FOR COLLECTION 40 ===")
        print(f"Question: {search_input.question}")
        print(f"Collection ID: {search_input.collection_id}")
        print()

        # Initialize pipeline manually to examine components
        collection_name = await search_service._initialize_pipeline(search_input.collection_id)
        print(f"Collection name: {collection_name}")

        # Get pipeline service and examine retrieved documents
        pipeline_service = search_service.pipeline_service

        # Prepare query and retrieve documents
        clean_query = pipeline_service._prepare_query(search_input.question)
        print(f"Clean query: {clean_query}")

        rewritten_query = pipeline_service.query_rewriter.rewrite(clean_query)
        print(f"Rewritten query: {rewritten_query}")

        # Retrieve documents
        query_results = pipeline_service._retrieve_documents(rewritten_query, collection_name)

        print(f"\n=== RETRIEVED {len(query_results)} CHUNKS ===")

        for i, result in enumerate(query_results, 1):
            print(f"\n--- CHUNK {i} ---")
            print(f"Score: {result.score:.4f}")
            print(f"Document ID: {result.document_id}")
            print(f"Chunk ID: {result.chunk_id}")
            print(f"Text length: {len(result.chunk.text)}")
            print("Text content:")
            print("-" * 50)
            print(result.chunk.text)
            print("-" * 50)
            print()

        # Show final context assembly
        print("\n=== CONTEXT ASSEMBLY ===")
        template_id = pipeline_service._get_templates(search_input.user_id)[0].id
        context_text = pipeline_service._format_context(template_id, query_results)

        print(f"Final context length: {len(context_text)}")
        print("Final context:")
        print("=" * 80)
        print(context_text)
        print("=" * 80)

    except Exception as e:
        print(f"Error during debugging: {e}")
        import traceback

        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
