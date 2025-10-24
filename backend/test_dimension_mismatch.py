#!/usr/bin/env python3
"""Test script to reproduce and debug the embedding dimension mismatch issue."""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import get_settings
from rag_solution.data_ingestion.ingestion import DocumentStore
from vectordbs.milvus_store import MilvusStore

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_dimension_mismatch():
    """Test document upload to trigger dimension debugging."""
    try:
        settings = get_settings()

        logger.info("=" * 80)
        logger.info("DIMENSION MISMATCH TEST")
        logger.info("=" * 80)
        logger.info("Embedding Model: %s", settings.embedding_model)
        logger.info("Embedding Dimension: %d", settings.embedding_dim)
        logger.info("=" * 80)

        # Create test collection
        collection_name = "dimension_test_collection"
        vector_store = MilvusStore(settings)

        logger.info("Creating collection: %s", collection_name)
        vector_store.create_collection(collection_name)

        # Create document store
        doc_store = DocumentStore(vector_store, collection_name, settings)

        # Test with a small PDF file
        test_file = "/Users/mg/Downloads/5638-29440-1-SM.pdf"
        if not Path(test_file).exists():
            logger.error("Test file not found: %s", test_file)
            logger.info("Please provide a test PDF file path")
            return

        logger.info("Loading document: %s", test_file)

        # This should trigger the dimension debugging
        documents = await doc_store.load_documents([test_file])

        logger.info("=" * 80)
        logger.info("SUCCESS! Loaded %d documents", len(documents))
        logger.info("=" * 80)

        # Cleanup
        logger.info("Cleaning up test collection")
        vector_store.delete_collection(collection_name)

    except Exception as e:
        logger.error("=" * 80)
        logger.error("ERROR: %s", e, exc_info=True)
        logger.error("=" * 80)
        raise


if __name__ == "__main__":
    asyncio.run(test_dimension_mismatch())
