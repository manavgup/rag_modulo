import logging
import os
import multiprocessing
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
import concurrent.futures

from core.config import settings
from core.custom_exceptions import DocumentStorageError, DocumentIngestionError
from rag_solution.data_ingestion.document_processor import DocumentProcessor
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source
from vectordbs.factory import get_datastore
from vectordbs.vector_store import VectorStore
from typing import List, Iterable, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = settings.data_dir
VECTOR_DB = settings.vector_db
COLLECTION_NAME = settings.collection_name
MAX_RETRIES = 3  # Maximum number of retries for storing a document

class DocumentStore:
    def __init__(self, vector_store: VectorStore, collection_name: str):
        self.vector_store = vector_store
        self.collection_name = collection_name
        self.documents = []

    async def load_documents(self, data_source: List[str]) -> List[Document]:
        """
        Load documents from the specified data source and ingest them into the vector store.

        Args:
            data_source (List[str]): List of file paths to ingest.

        Returns:
            List[Document]: List of loaded and processed documents.
        """
        try:
            processed_documents = await ingest_documents(data_source, self.vector_store, self.collection_name)
            self.documents.extend(processed_documents)
            logger.info(f"Ingested and processed {len(processed_documents)} documents into collection: {self.collection_name}")
            return processed_documents
        except Exception as e:
            logger.error(f"Error ingesting documents: {str(e)}")
            raise

    def add_documents(self, documents: List[Document]):
        """
        Add new documents to the document store and vector store.

        Args:
            documents (List[Document]): The list of documents to add.
        """
        try:
            process_and_store_document(documents, self.vector_store, self.collection_name)
            self.documents.extend(documents)
            logger.info(f"Added {len(documents)} documents to the document store and vector store")
        except Exception as e:
            logger.error(f"Error adding documents to document store: {e}")
            raise

    def get_documents(self) -> List[Document]:
        """
        Get all documents in the document store.

        Returns:
            List[Document]: List of all documents.
        """
        return self.documents

    def clear(self):
        """
        Clear all documents from the document store and vector store.
        """
        try:
            self.vector_store.delete_collection(self.collection_name)
            self.vector_store.create_collection(self.collection_name)
            self.documents.clear()
            logger.info(f"Cleared all documents from collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error clearing documents: {e}")
            raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def process_and_store_document(documents: List[Document], vector_store: VectorStore, collection_name: str) -> None:
    """
    Process and store documents in the vector store.

    Args:
        documents (List[Document]): The documents to process and store.
        vector_store (VectorStore): The vector store to use for storage.
        collection_name (str): The name of the collection to store the documents in.

    Raises:
        DocumentStorageError: If there is an error processing or storing the documents.
    """
    try:
        logger.info(f"Attempting to store documents in collection {collection_name}")
        # Use ThreadPoolExecutor to handle sync method call
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(vector_store.add_documents, collection_name, documents)
            future.result()  # Wait for the result
        logger.info(f"Successfully added documents to collection {collection_name}")
    except Exception as e:
        logger.error(f"Error processing documents: {e}", exc_info=True)
        raise DocumentStorageError(f"Error: {e}")

async def ingest_documents(data_dir: List[str], vector_store: VectorStore, collection_name: str) -> List[Document]:
    processed_documents = []
    with multiprocessing.Manager() as manager:
        processor = DocumentProcessor(manager)
        
        for file_path in data_dir:
            logger.info(f"Trying to process {file_path}")
            try:
                # Process the document
                documents_iterator = processor.process_document(file_path)
                logger.info("*** Finished processing and chunking. Now store in VectorDB")

                async for document in documents_iterator:
                    try:
                        process_and_store_document([document], vector_store, collection_name)
                        processed_documents.append(document)
                    except Exception as e:
                        logger.error(f"Unexpected error while storing document: {e}", exc_info=True)
                        raise e

                logger.info(f"Successfully processed {file_path}")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}", exc_info=True)
                raise e
    
    logger.info(f"Completed ingestion for collection: {collection_name}")
    return processed_documents

async def main() -> None:
    """
    Main function to orchestrate the document ingestion process.
    """
    vector_store = get_datastore(settings.vector_db)
    document_store = DocumentStore(vector_store, settings.collection_name)
    try:
        await document_store.clear()
        processed_documents = await document_store.load_documents(settings.data_dir)
        logger.info(f"Ingestion process completed successfully. Processed {len(processed_documents)} documents.")
    except Exception as e:
        logger.error(f"Error during ingestion process: {e}", exc_info=True)
    finally:
        await vector_store.close()

if __name__ == "__main__":
    asyncio.run(main())
