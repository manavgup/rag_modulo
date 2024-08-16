import logging
import os

from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import settings
from backend.core.custom_exceptions import DocumentStorageError
from backend.rag_solution.data_ingestion.document_processor import DocumentProcessor
from backend.vectordbs.data_types import Document
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
        vector_store.add_documents(collection_name, [document])
        logger.info(f"Document {document.document_id} successfully stored in collection {collection_name}.")
    except Exception as e:
        logger.error(f"Error processing document {document.document_id}: {e}", exc_info=True)
        raise DocumentStorageError(f"error: {e}")

def ingest_documents(data_dir: List[str], vector_store: VectorStore, collection_name: str) -> None:
    """
    Ingest documents from the specified directory into the vector store.

    Args:
        data_dir (str): The directory containing the documents to ingest.
        vector_store (VectorStore): The vector store to use for storage.
        collection_name (str): The name of the collection to store the documents in.
    """
    processor = DocumentProcessor()

    for file in data_dir:
        logger.info(f"Trying to process {file}")
        for document in processor.process_document(file):
            process_and_store_document(document, vector_store, collection_name)

    logging.info(f"Completed ingestion for collection: {collection_name}")
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
