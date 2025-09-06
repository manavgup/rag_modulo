# ingestion.py

import logging
import multiprocessing
import uuid
from typing import Any

from core.config import Settings, get_settings
from core.custom_exceptions import DocumentStorageError
from rag_solution.data_ingestion.document_processor import DocumentProcessor
from vectordbs.data_types import Document
from vectordbs.vector_store import VectorStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Remove module-level constants - use dependency injection instead
MAX_RETRIES = 3  # Maximum number of retries for storing a document


class DocumentStore:
    def __init__(self: Any, vector_store: VectorStore, collection_name: str, settings: Settings = get_settings()) -> None:
        """Initialize document store with dependency injection."""
        self.settings = settings
        self.vector_store = vector_store
        self.collection_name = collection_name
        self.documents: list[Document] = []

    async def load_documents(self, data_source: list[str]) -> list[Document]:
        """Load documents from the specified data source and ingest them into the vector store."""
        try:
            processed_documents = await self.ingest_documents(data_source)
            self.documents.extend(processed_documents)
            logger.info(f"Ingested and processed {len(processed_documents)} documents into collection: {self.collection_name}")
            return processed_documents
        except Exception as e:
            logger.error(f"Error ingesting documents: {e!s}", exc_info=True)
            raise

    async def ingest_documents(self, file_paths: list[str]) -> list[Document]:
        """Ingest documents and store them in the vector store."""
        processed_documents: list[Document] = []
        with multiprocessing.Manager() as manager:
            processor = DocumentProcessor(manager, self.settings)

            for file_path in file_paths:
                logger.info(f"Processing file: {file_path}")
                try:
                    # Process the document
                    documents_iterator = processor.process_document(file_path, str(uuid.uuid4()))
                    async for document in documents_iterator:
                        processed_documents.append(document)
                        # Store document in vector store
                        self.store_documents_in_vector_store([document])
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e!s}", exc_info=True)
                    raise e
        return processed_documents

    def store_documents_in_vector_store(self, documents: list[Document]) -> None:
        """Store documents in the vector store."""
        try:
            logger.info(f"Storing documents in collection {self.collection_name}")
            self.vector_store.add_documents(self.collection_name, documents)
            logger.info(f"Successfully stored documents in collection {self.collection_name}")
        except Exception as e:
            logger.error(f"Error storing documents: {e}", exc_info=True)
            raise DocumentStorageError(doc_id="", storage_path="", error_type="storage_failed", message=f"Error: {e}") from e

    def get_documents(self) -> list[Document]:
        """Get all documents in the document store."""
        return self.documents

    async def clear(self) -> None:
        """Clear all documents from the document store and vector store."""
        try:
            self.vector_store.delete_collection(self.collection_name)
            self.vector_store.create_collection(self.collection_name)
            self.documents.clear()
            logger.info(f"Cleared all documents from collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error clearing documents: {e}", exc_info=True)
            raise
