#!/usr/bin/env python3
"""
Simple test script to debug embedding generation issues.
This script tests the embedding generation pipeline in isolation.
"""

import logging
import sys
import os
from typing import List

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from core.config import get_settings
from core.custom_exceptions import LLMProviderError
from rag_solution.file_management.database import create_session_factory
from rag_solution.generation.providers.factory import LLMProviderFactory
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, DocumentMetadata, Source

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_embedding_generation():
    """Test embedding generation with WatsonX provider."""
    logger.info("Starting embedding generation test...")

    try:
        # Get settings
        settings = get_settings()
        logger.info("Settings loaded successfully")
        logger.info("WatsonX URL: %s", settings.watsonx_url)
        logger.info("WatsonX Project ID: %s", settings.watsonx_project_id)
        logger.info("WatsonX API Key: %s", "***" if settings.watsonx_api_key else "None")

        # Create database session
        session_factory = create_session_factory()
        db = session_factory()
        logger.info("Database session created")

        try:
            # Create LLM provider factory
            factory = LLMProviderFactory(db)
            logger.info("LLM provider factory created")

            # Get WatsonX provider
            provider = factory.get_provider("watsonx")
            logger.info("WatsonX provider retrieved: %s", type(provider))

            # Test embedding generation with simple text
            test_texts = [
                "This is a test document about artificial intelligence.",
                "Machine learning is a subset of AI.",
                "Natural language processing helps computers understand text."
            ]

            logger.info("Testing embedding generation with %d texts", len(test_texts))
            logger.info("Test texts: %s", test_texts)

            # Generate embeddings
            embeddings = provider.get_embeddings(test_texts)

            logger.info("Embeddings generated successfully!")
            logger.info("Number of embeddings: %d", len(embeddings))

            # Check each embedding
            for i, embedding in enumerate(embeddings):
                if embedding:
                    logger.info("Embedding %d: length=%d, type=%s", i, len(embedding), type(embedding))
                    logger.info("First 5 values: %s", embedding[:5] if len(embedding) >= 5 else embedding)
                else:
                    logger.error("Embedding %d is None or empty!", i)

            # Test with single text
            logger.info("\nTesting single text embedding...")
            single_embedding = provider.get_embeddings("Single test text")
            logger.info("Single embedding: length=%d, type=%s", len(single_embedding), type(single_embedding))

            return True

        finally:
            db.close()
            logger.info("Database session closed")

    except LLMProviderError as e:
        logger.error("LLM Provider Error: %s", e)
        return False
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return False


def test_document_creation():
    """Test creating a document with embeddings."""
    logger.info("\nTesting document creation with embeddings...")

    try:
        # Create a simple document
        doc_metadata = DocumentMetadata(
            document_id="test-doc-1",
            file_name="test.txt",
            file_path="/tmp/test.txt",
            file_type=".txt",
            file_size=100,
            creation_date=None,
            last_modified_date=None,
            page_number=None,
        )

        chunk_metadata = DocumentChunkMetadata(
            source=Source.OTHER,
            document_id="test-doc-1"
        )

        # Create a chunk with empty embeddings (like our processors do)
        chunk = DocumentChunk(
            chunk_id="test-chunk-1",
            text="This is a test chunk for embedding generation.",
            embeddings=[],  # Empty embeddings like our processors create
            document_id="test-doc-1",
            metadata=chunk_metadata,
        )

        document = Document(
            name="test.txt",
            document_id="test-doc-1",
            chunks=[chunk],
            metadata=doc_metadata,
        )

        logger.info("Document created with %d chunks", len(document.chunks))
        logger.info("First chunk embeddings: %s", document.chunks[0].embeddings)

        # Now test the embedding generation process
        session_factory = create_session_factory()
        db = session_factory()

        try:
            factory = LLMProviderFactory(db)
            provider = factory.get_provider("watsonx")

            # Collect all text chunks
            all_texts = []
            chunk_mapping = []

            for doc_idx, doc in enumerate([document]):
                for chunk_idx, chunk in enumerate(doc.chunks):
                    all_texts.append(chunk.text)
                    chunk_mapping.append((doc_idx, chunk_idx))

            logger.info("Collected %d texts for embedding", len(all_texts))

            if all_texts:
                # Generate embeddings
                all_embeddings = provider.get_embeddings(all_texts)
                logger.info("Generated %d embeddings", len(all_embeddings))

                # Assign embeddings back to chunks
                for embedding_idx, (doc_idx, chunk_idx) in enumerate(chunk_mapping):
                    if embedding_idx < len(all_embeddings):
                        document.chunks[chunk_idx].embeddings = all_embeddings[embedding_idx]
                        logger.info("Assigned embedding %d to chunk %d", embedding_idx, chunk_idx)
                        logger.info("Chunk embeddings length: %d", len(document.chunks[chunk_idx].embeddings))
                    else:
                        logger.error("No embedding available for index %d", embedding_idx)

            logger.info("Document processing complete!")
            logger.info("Final chunk embeddings: %s", document.chunks[0].embeddings)

            return True

        finally:
            db.close()

    except Exception as e:
        logger.error("Error in document creation test: %s", e, exc_info=True)
        return False


def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("EMBEDDING GENERATION TEST")
    logger.info("=" * 60)

    # Test 1: Basic embedding generation
    logger.info("\nTEST 1: Basic Embedding Generation")
    logger.info("-" * 40)
    success1 = test_embedding_generation()

    # Test 2: Document creation with embeddings
    logger.info("\nTEST 2: Document Creation with Embeddings")
    logger.info("-" * 40)
    success2 = test_document_creation()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info("Test 1 (Basic Embedding): %s", "PASSED" if success1 else "FAILED")
    logger.info("Test 2 (Document Creation): %s", "PASSED" if success2 else "FAILED")

    if success1 and success2:
        logger.info("All tests PASSED! Embedding generation is working correctly.")
        return 0
    else:
        logger.error("Some tests FAILED! Check the logs above for details.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
