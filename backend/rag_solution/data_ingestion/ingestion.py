# ingestion.py
import asyncio
import logging
import os

from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from error_handling import handle_errors
from custom_exceptions import DocumentStorageError
from vectordbs.data_types import Document
from vectordbs.factory import get_datastore
from vectordbs.vector_store import VectorStore

from .document_processor import DocumentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = settings.data_dir
VECTOR_DB = settings.vector_db
COLLECTION_NAME = settings.collection_name
MAX_RETRIES = 3  # Maximum number of retries for storing a document
CONCURRENCY_LEVEL = 5  # Number of concurrent tasks


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def process_and_store_document(
    document: Document, vector_store: VectorStore, collection_name: str
) -> None:
    """
    Process and store a document in the vector store.

    Args:
        document (Document): The document to process and store.
        vector_store (VectorStore): The vector store to use for storage.
        collection_name (str): The name of the collection to store the document in.
    """
    try:
        await vector_store.add_documents_async(collection_name, [document])
        logger.info(
            f"Document {document.document_id} successfully stored in collection {collection_name}."
        )
    except Exception as e:
        logger.error(
            f"Error processing document {document.document_id}: {e}", exc_info=True
        )
        raise DocumentStorageError(f"error: {e}")


# @handle_errors
async def ingest_documents(
    data_dir: str, vector_store: VectorStore, collection_name: str
) -> None:
    """
    Ingest documents from the specified directory into the vector store.

    Args:
        data_dir (str): The directory containing the documents to ingest.
        vector_store (VectorStore): The vector store to use for storage.
    """
    processor = DocumentProcessor()
    tasks = []

    for root, _, files in os.walk(data_dir):
        for file in files:
            file_path = os.path.join(root, file)
            async for document in processor.process_document(file_path):
                tasks.append(
                    process_and_store_document(document, vector_store, collection_name)
                )

    await asyncio.gather(*tasks)


@handle_errors
async def main() -> None:
    """
    Main function to orchestrate the document ingestion process.
    """
    vector_store = get_datastore(settings.vector_db)
    await vector_store.delete_collection_async(settings.collection_name)
    await vector_store.create_collection_async(settings.collection_name)
    await ingest_documents(settings.data_dir, vector_store, settings.collection_name)
    logger.info("Ingestion process completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
