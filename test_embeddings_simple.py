#!/usr/bin/env python3
"""
Simple test script to debug embedding generation issues without database dependencies.
This script tests the WatsonX embedding generation directly.
"""

import logging
import sys
import os
from typing import List

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_watsonx_embeddings_direct():
    """Test WatsonX embeddings directly without database dependencies."""
    logger.info("Testing WatsonX embeddings directly...")
    
    try:
        # Import WatsonX components directly
        from ibm_watsonx_ai.foundation_models import Embeddings as wx_Embeddings
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
        
        # Get settings
        from core.config import get_settings
        settings = get_settings()
        
        logger.info("Settings loaded successfully")
        logger.info("WatsonX URL: %s", settings.wx_url)
        logger.info("WatsonX Project ID: %s", settings.wx_project_id)
        logger.info("WatsonX API Key: %s", "***" if settings.wx_api_key else "None")
        logger.info("Embedding Model: %s", settings.embedding_model)
        
        # Create embeddings client directly
        logger.info("Creating WatsonX embeddings client...")
        
        embeddings_client = wx_Embeddings(
            model_id=settings.embedding_model,
            project_id=settings.wx_project_id,
            credentials=Credentials(
                api_key=settings.wx_api_key,
                url=settings.wx_url
            ),
            params={EmbedParams.RETURN_OPTIONS: {"input_text": True}},
        )
        
        logger.info("Embeddings client created successfully")
        
        # Test embedding generation
        test_texts = [
            "This is a test document about artificial intelligence.",
            "Machine learning is a subset of AI.",
            "Natural language processing helps computers understand text."
        ]
        
        logger.info("Testing embedding generation with %d texts", len(test_texts))
        logger.info("Test texts: %s", test_texts)
        
        # Generate embeddings
        embeddings = embeddings_client.embed_documents(texts=test_texts)
        
        logger.info("Embeddings generated successfully!")
        logger.info("Type of embeddings: %s", type(embeddings))
        logger.info("Number of embeddings: %d", len(embeddings) if embeddings else 0)
        
        # Check each embedding
        if embeddings:
            for i, embedding in enumerate(embeddings):
                if embedding:
                    logger.info("Embedding %d: length=%d, type=%s", i, len(embedding), type(embedding))
                    logger.info("First 5 values: %s", embedding[:5] if len(embedding) >= 5 else embedding)
                else:
                    logger.error("Embedding %d is None or empty!", i)
        else:
            logger.error("No embeddings returned!")
        
        # Test with single text
        logger.info("\nTesting single text embedding...")
        single_embedding = embeddings_client.embed_documents(texts=["Single test text"])
        logger.info("Single embedding: length=%d, type=%s", len(single_embedding), type(single_embedding))
        
        return True
        
    except Exception as e:
        logger.error("Error in direct WatsonX test: %s", e, exc_info=True)
        return False


def test_embedding_data_types():
    """Test the data types and structures used in our system."""
    logger.info("\nTesting embedding data types...")
    
    try:
        # Create minimal data structures without importing vectordbs
        from dataclasses import dataclass
        from typing import List, Optional
        from datetime import datetime
        from enum import Enum
        
        class Source(Enum):
            PDF = "pdf"
            OTHER = "other"
        
        @dataclass
        class DocumentMetadata:
            document_id: str
            file_name: str
            file_path: str
            file_type: str
            file_size: int
            creation_date: Optional[datetime]
            last_modified_date: Optional[datetime]
            page_number: Optional[int]
        
        @dataclass
        class DocumentChunkMetadata:
            source: Source
            document_id: str
        
        @dataclass
        class DocumentChunk:
            chunk_id: str
            text: str
            embeddings: List[float]
            document_id: str
            metadata: DocumentChunkMetadata
        
        @dataclass
        class Document:
            name: str
            document_id: str
            chunks: List[DocumentChunk]
            metadata: DocumentMetadata
        
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
        
        logger.info("Document created successfully")
        logger.info("Document has %d chunks", len(document.chunks))
        logger.info("First chunk text: %s", document.chunks[0].text)
        logger.info("First chunk embeddings: %s", document.chunks[0].embeddings)
        logger.info("First chunk embeddings type: %s", type(document.chunks[0].embeddings))
        
        # Test assigning embeddings
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # Mock embedding
        document.chunks[0].embeddings = test_embedding
        
        logger.info("After assigning embedding:")
        logger.info("First chunk embeddings: %s", document.chunks[0].embeddings)
        logger.info("First chunk embeddings type: %s", type(document.chunks[0].embeddings))
        logger.info("First chunk embeddings length: %d", len(document.chunks[0].embeddings))
        
        return True
        
    except Exception as e:
        logger.error("Error in data types test: %s", e, exc_info=True)
        return False


def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("SIMPLE EMBEDDING GENERATION TEST")
    logger.info("=" * 60)
    
    # Test 1: Direct WatsonX embedding generation
    logger.info("\nTEST 1: Direct WatsonX Embedding Generation")
    logger.info("-" * 50)
    success1 = test_watsonx_embeddings_direct()
    
    # Test 2: Data types and structures
    logger.info("\nTEST 2: Data Types and Structures")
    logger.info("-" * 50)
    success2 = test_embedding_data_types()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info("Test 1 (Direct WatsonX): %s", "PASSED" if success1 else "FAILED")
    logger.info("Test 2 (Data Types): %s", "PASSED" if success2 else "FAILED")
    
    if success1 and success2:
        logger.info("All tests PASSED! Embedding generation is working correctly.")
        return 0
    else:
        logger.error("Some tests FAILED! Check the logs above for details.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
