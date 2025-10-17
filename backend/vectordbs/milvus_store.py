"""Milvus vector store implementation.

This module provides a Milvus-based implementation of the VectorStore interface,
enabling document storage, retrieval, and search operations using Milvus.
"""

import json
import logging
import time
from typing import Any

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, MilvusException, connections, utility

from core.config import Settings, get_settings
from vectordbs.utils.watsonx import get_embeddings

from .data_types import (
    Document,
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
    Source,
)
from .error_types import CollectionError, DocumentError, VectorStoreError
from .vector_store import VectorStore

logger = logging.getLogger(__name__)

# Remove module-level constants - use dependency injection instead


def _create_schema(settings: Settings) -> list[FieldSchema]:
    """Create the schema for Milvus collection with injected settings."""
    return [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name=settings.embedding_field, dtype=DataType.FLOAT_VECTOR, dim=settings.embedding_dim),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100),
        # Document metadata fields
        FieldSchema(name="document_name", dtype=DataType.VARCHAR, max_length=65535),
        # Chunk metadata fields
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name="page_number", dtype=DataType.INT64),
        FieldSchema(name="chunk_number", dtype=DataType.INT64),
    ]


class MilvusStore(VectorStore):
    """Milvus implementation of the VectorStore interface.

    This class provides Milvus-based vector storage and retrieval capabilities,
    including document management, collection operations, and similarity search.
    """

    def __init__(self, settings: Settings = get_settings()) -> None:
        # Call parent constructor for proper dependency injection
        super().__init__(settings)

        # Configure logging
        logging.basicConfig(level=self.settings.log_level)

        # Initialize connection
        self._connect()

        # Initialize index and search parameters
        self.index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 1024}}
        self.search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

    def _connect(self, attempts: int = 3) -> None:
        """Connect to Milvus with retry logic."""
        host = self.settings.milvus_host or "localhost"
        port = self.settings.milvus_port or 19530

        # Disconnect any existing connection first to avoid using cached connection with old host
        try:
            connections.disconnect("default")
            logging.info("Disconnected existing Milvus connection")
        except Exception:
            pass  # No existing connection, continue

        for attempt in range(attempts):
            try:
                connections.connect("default", host=host, port=port)
                logging.info("Connected to Milvus at %s:%s", host, port)
                return
            except MilvusException as e:
                logging.error("Failed to connect to Milvus at %s:%s: %s", host, port, str(e))
                if attempt < attempts - 1:
                    logging.info("Retrying connection to Milvus... (Attempt %d/%d)", attempt + 2, attempts)
                    time.sleep(10)
                raise VectorStoreError(f"Failed to connect to Milvus after {attempts} attempts") from e

    def _get_collection(self, collection_name: str) -> Collection:
        """Retrieve a collection from Milvus.

        Args:
            collection_name: Name of the collection

        Returns:
            Collection: The Milvus collection

        Raises:
            CollectionError: If collection doesn't exist
        """
        if utility.has_collection(collection_name):
            return Collection(name=collection_name)
        raise CollectionError(f"Collection '{collection_name}' does not exist")

    def create_collection(self, collection_name: str, metadata: dict | None = None) -> Collection:  # noqa: ARG002
        """Create a new Milvus collection.

        Args:
            collection_name: Name of the collection to create
            metadata: Optional metadata for the collection

        Returns:
            Collection: The created collection

        Raises:
            CollectionError: If collection creation fails
        """
        try:
            if collection_name in utility.list_collections():
                logging.info("Collection '%s' already exists", collection_name)
                return Collection(name=collection_name)
            self._create_collection(collection_name)
            return Collection(name=collection_name)
        except Exception as e:
            logging.error("Failed to create collection '%s': %s", collection_name, str(e))
            raise CollectionError(f"Failed to create collection '{collection_name}': {e}") from e

    def _create_collection(self, collection_name: str) -> None:
        """Internal method to create collection."""
        try:
            schema = CollectionSchema(
                fields=_create_schema(self.settings), description=f"Collection for {collection_name}"
            )
            collection = Collection(name=collection_name, schema=schema)

            # Create index
            collection.create_index(field_name=self.settings.embedding_field, index_params=self.index_params)

            # Load collection
            collection.load()

            logging.info("Collection '%s' created successfully", collection_name)
        except Exception as e:
            logging.error("Failed to create collection '%s': %s", collection_name, str(e))
            raise CollectionError(f"Failed to create collection '{collection_name}': {e}") from e

    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """Add documents to the Milvus collection.

        Args:
            collection_name: Name of the collection
            documents: List of documents to add

        Returns:
            List[str]: List of document IDs that were added

        Raises:
            DocumentError: If document addition fails
        """
        try:
            collection = self._get_collection(collection_name)

            # Prepare data for insertion
            document_ids = []
            texts = []
            embeddings = []
            chunk_ids = []
            sources = []
            page_numbers = []
            chunk_numbers = []
            document_names = []

            for document in documents:
                for chunk in document.chunks:
                    document_ids.append(chunk.document_id or "")
                    texts.append(chunk.text)
                    embeddings.append(chunk.embeddings)
                    chunk_ids.append(chunk.chunk_id)
                    sources.append(str(chunk.metadata.source) if chunk.metadata and chunk.metadata.source else "OTHER")
                    page_numbers.append(
                        chunk.metadata.page_number if chunk.metadata and chunk.metadata.page_number is not None else 0
                    )
                    chunk_numbers.append(
                        chunk.metadata.chunk_number if chunk.metadata and chunk.metadata.chunk_number is not None else 0
                    )
                    document_names.append(document.metadata.title if document.metadata else "")

            # Insert data
            collection.insert(
                [
                    document_ids,
                    embeddings,
                    texts,
                    chunk_ids,
                    document_names,
                    sources,
                    page_numbers,
                    chunk_numbers,
                ]
            )

            # Flush to ensure data is written
            collection.flush()

            logging.info("Successfully added %d documents to collection '%s'", len(documents), collection_name)
            return document_ids
        except Exception as e:
            logging.error("Failed to add documents to Milvus collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to add documents to Milvus collection '{collection_name}': {e}") from e

    def retrieve_documents(self, query: str, collection_name: str, number_of_results: int = 10) -> list[QueryResult]:
        """Retrieve documents based on a query string.

        Args:
            query: The query string
            collection_name: Name of the collection to search
            number_of_results: Maximum number of results to return

        Returns:
            List[QueryResult]: List of query results

        Raises:
            DocumentError: If retrieval fails
        """
        query_embeddings = get_embeddings(query, settings=self.settings)
        if not query_embeddings:
            raise DocumentError("Failed to generate embeddings for the query string.")

        query_with_embedding = QueryWithEmbedding(text=query, embeddings=query_embeddings[0])
        return self.query(collection_name, query_with_embedding, number_of_results=number_of_results)

    def query(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        metadata_filter: DocumentMetadataFilter | None = None,  # noqa: ARG002
    ) -> list[QueryResult]:
        """Query the Milvus collection.

        Args:
            collection_name: Name of the collection to query
            query: Query with embedding
            number_of_results: Maximum number of results to return
            metadata_filter: Optional metadata filter

        Returns:
            List[QueryResult]: List of query results

        Raises:
            DocumentError: If query fails
        """
        try:
            collection = self._get_collection(collection_name)

            # Perform search
            results = collection.search(
                data=[query.embeddings],  # Pass the full embedding vector, not just the first element
                anns_field=self.settings.embedding_field,
                param=self.search_params,
                limit=number_of_results,
                output_fields=[
                    "document_id",
                    "text",
                    "chunk_id",
                    "source",
                    "page_number",
                    "chunk_number",
                    "document_name",
                ],
            )

            logging.info("Query response: %s", results)
            return self._process_search_results(results, collection_name)
        except Exception as e:
            logging.error("Failed to query Milvus collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to query Milvus collection '{collection_name}': {e}") from e

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection from Milvus.

        Args:
            collection_name: Name of the collection to delete

        Raises:
            CollectionError: If deletion fails
        """
        try:
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                logging.info("Deleted collection '%s'", collection_name)
        except Exception as e:
            logging.error("Failed to delete Milvus collection: %s", str(e))
            raise CollectionError(f"Failed to delete Milvus collection: {e}") from e

    def list_collections(self) -> list[str]:
        """List all collections in Milvus.

        Returns:
            List of collection names

        Raises:
            CollectionError: If listing fails
        """
        try:
            collections = utility.list_collections()
            logging.info("Listed %d collections from Milvus", len(collections))
            return collections
        except Exception as e:
            logging.error("Failed to list Milvus collections: %s", str(e))
            raise CollectionError(f"Failed to list Milvus collections: {e}") from e

    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """Delete documents by their IDs from the Milvus collection.

        Args:
            collection_name: Name of the collection
            document_ids: List of document IDs to delete

        Raises:
            DocumentError: If deletion fails
        """
        try:
            collection = self._get_collection(collection_name)

            # Build filter expression
            filter_expr = f"document_id in {json.dumps(document_ids)}"

            # Delete documents
            collection.delete(filter_expr)

            # Flush to ensure deletion is applied
            collection.flush()

            logging.info("Deleted %d documents from collection '%s'", len(document_ids), collection_name)
        except Exception as e:
            logging.error("Failed to delete documents from Milvus collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to delete documents from Milvus collection '{collection_name}': {e}") from e

    def count_document_chunks(self, collection_name: str, document_id: str) -> int:
        """Count the number of chunks for a specific document.

        Args:
            collection_name: Name of the collection to search in
            document_id: The document ID to count chunks for

        Returns:
            Number of chunks found for the document

        Raises:
            CollectionError: If collection doesn't exist
            DocumentError: If counting fails
        """
        try:
            collection = self._get_collection(collection_name)

            # Escape document_id to prevent injection attacks
            # Use JSON encoding for proper string escaping
            escaped_doc_id = json.dumps(document_id)

            # Query with expression filter for document_id
            results = collection.query(
                expr=f"document_id == {escaped_doc_id}",
                output_fields=["id"],  # Only need count, minimal fields
                limit=10000,  # Max chunks per document
            )

            chunk_count = len(results) if results else 0
            logging.debug("Found %d chunks for document %s in collection %s", chunk_count, document_id, collection_name)
            return chunk_count

        except CollectionError:
            # Re-raise collection errors
            raise
        except Exception as e:
            logging.warning(
                "Error counting chunks for document %s in collection %s: %s", document_id, collection_name, str(e)
            )
            raise DocumentError(
                f"Failed to count chunks for document '{document_id}' in collection '{collection_name}': {e}"
            ) from e

    def _process_search_results(self, results: Any, collection_name: str) -> list[QueryResult]:  # noqa: ARG002
        """Process Milvus search results into QueryResult objects."""
        query_results = []

        for hit in results[0]:  # results is a list of hits for each query
            # Extract data from hit using proper Milvus Hit API
            entity = hit.entity
            document_id = getattr(entity, "document_id", "")
            text = getattr(entity, "text", "")
            chunk_id = getattr(entity, "chunk_id", "")
            source = getattr(entity, "source", "OTHER")
            page_number = getattr(entity, "page_number", 0)
            chunk_number = getattr(entity, "chunk_number", 0)

            # Create DocumentChunkWithScore
            chunk = DocumentChunkWithScore(
                chunk_id=chunk_id,
                text=text,
                embeddings=None,  # Milvus doesn't return embeddings in search results
                metadata=DocumentChunkMetadata(
                    source=Source(source.lower().replace("source.", "") if source else "other"),
                    document_id=document_id,
                    page_number=page_number,
                    chunk_number=chunk_number,
                ),
                document_id=document_id,
                score=float(hit.score),
            )

            query_results.append(QueryResult(chunk=chunk, score=float(hit.score), embeddings=[]))

        return query_results
