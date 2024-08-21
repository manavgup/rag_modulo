import logging
import os
import multiprocessing
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import settings
from backend.core.custom_exceptions import DocumentStorageError
from backend.rag_solution.data_ingestion.document_processor import DocumentProcessor
from backend.vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source
from backend.vectordbs.factory import get_datastore
from backend.vectordbs.vector_store import VectorStore
from typing import List
from concurrent.futures import ProcessPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = settings.data_dir
VECTOR_DB = settings.vector_db
COLLECTION_NAME = settings.collection_name
MAX_RETRIES = 3  # Maximum number of retries for storing a document


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def process_and_store_document(document: Document, vector_store: VectorStore, collection_name: str) -> None:
    """
    Process and store a document in the vector store.

    Args:
        document (Document): The document to process and store.
        vector_store (VectorStore): The vector store to use for storage.
        collection_name (str): The name of the collection to store the document in.

    Raises:
        DocumentStorageError: If there is an error processing or storing the document.
    """
    try:
        logger.info(f"Attempting to store documents in collection {collection_name}")
        vector_store.add_documents(collection_name, [document])
    except Exception as e:
        logger.error(f"Error processing document {e}", exc_info=True)
        raise DocumentStorageError(f"error: {e}")

def ingest_documents(data_dir: List[str], vector_store: VectorStore, collection_name: str) -> None:
    with multiprocessing.Manager() as manager:
        processor = DocumentProcessor(manager)
        
        for file_path in data_dir:
            logger.info(f"Trying to process {file_path}")
            try:
                # Process the document
                documents_iterator = processor.process_document(file_path)
                logger.info("*** Finished processing and chunking. Now store in VectorDB")

                for document in documents_iterator:
                    process_and_store_document(document, vector_store, collection_name)

                logger.info(f"Successfully processed {file_path}")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
    
    logger.info(f"Completed ingestion for collection: {collection_name}")
    # TO-DO: Add multithreading


def main() -> None:
    """
    Main function to orchestrate the document ingestion process.
    """
    vector_store = get_datastore(settings.vector_db)
    vector_store.delete_collection(settings.collection_name)
    vector_store.create_collection(settings.collection_name)
    ingest_documents(settings.data_dir, vector_store, settings.collection_name)
    logger.info("Ingestion process completed successfully.")


if __name__ == "__main__":
    main()
