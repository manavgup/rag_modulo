"""Pinecone vector store implementation.

This module provides a Pinecone-based implementation of the VectorStore interface,
enabling document storage, retrieval, and search operations using Pinecone.
"""

import logging
from typing import Any

from core.config import Settings, get_settings
from pinecone import Pinecone, ServerlessSpec

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
from .error_types import CollectionError, DocumentError
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class PineconeStore(VectorStore):
    """Pinecone implementation of the VectorStore interface.

    This class provides Pinecone-based vector storage and retrieval capabilities,
    including document management, collection operations, and similarity search.
    """

    def __init__(self, settings: Settings = get_settings()) -> None:
        # Call parent constructor for proper dependency injection
        super().__init__(settings)

        # Configure logging
        logging.basicConfig(level=self.settings.log_level)

        # Initialize Pinecone client
        try:
            self.pc = Pinecone(api_key=self.settings.pinecone_api_key)
            logging.info("Connected to Pinecone")
        except Exception as e:
            logging.error("Failed to connect to Pinecone: %s", str(e))
            raise CollectionError(f"Failed to connect to Pinecone: {e}") from e

    def create_collection(self, collection_name: str, metadata: dict | None = None) -> None:  # noqa: ARG002
        """Create a collection (index) in Pinecone.

        Args:
            collection_name: Name of the collection to create
            metadata: Optional metadata for the collection

        Raises:
            CollectionError: If collection creation fails
        """
        try:
            # Check if index already exists
            if collection_name in [index.name for index in self.pc.list_indexes()]:
                logging.info("Collection '%s' already exists", collection_name)
                return

            # Create index
            self.pc.create_index(
                name=collection_name,
                dimension=self.settings.embedding_dim,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

            logging.info("Collection '%s' created successfully", collection_name)
        except Exception as e:
            logging.error("Failed to create collection '%s': %s", collection_name, str(e))
            raise CollectionError(f"Failed to create collection '{collection_name}': {e}") from e

    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """Add documents to the Pinecone collection.

        Args:
            collection_name: Name of the collection
            documents: List of documents to add

        Returns:
            List[str]: List of document IDs that were added

        Raises:
            DocumentError: If document addition fails
        """
        try:
            index = self.pc.Index(collection_name)

            # Prepare vectors for upsert
            vectors = []
            document_ids = []

            for document in documents:
                for chunk in document.chunks:
                    vectors.append(
                        {
                            "id": chunk.chunk_id,
                            "values": chunk.embeddings,
                            "metadata": {
                                "text": chunk.text,
                                "document_id": chunk.document_id or "",
                                "source": str(chunk.metadata.source)
                                if chunk.metadata and chunk.metadata.source
                                else "OTHER",
                                "page_number": chunk.metadata.page_number if chunk.metadata else 0,
                                "chunk_number": chunk.metadata.chunk_number if chunk.metadata else 0,
                            },
                        }
                    )
                    document_ids.append(chunk.document_id)

            # Upsert vectors
            index.upsert(vectors=vectors)

            logging.info("Successfully added documents to collection '%s'", collection_name)
            return document_ids
        except Exception as e:
            logging.error("Failed to add documents to Pinecone collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to add documents to Pinecone collection '{collection_name}': {e}") from e

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
        """Query the Pinecone collection.

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
            index = self.pc.Index(collection_name)

            # Perform query
            results = index.query(vector=query.embeddings[0], top_k=number_of_results, include_metadata=True)

            logging.info("Query response: %s", results)
            return self._process_search_results(results, collection_name)
        except Exception as e:
            logging.error("Failed to query Pinecone collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to query Pinecone collection '{collection_name}': {e}") from e

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection from Pinecone.

        Args:
            collection_name: Name of the collection to delete

        Raises:
            CollectionError: If deletion fails
        """
        try:
            self.pc.delete_index(collection_name)
            logging.info("Deleted collection '%s'", collection_name)
        except Exception as e:
            logging.error("Failed to delete Pinecone collection: %s", str(e))
            raise CollectionError(f"Failed to delete Pinecone collection: {e}") from e

    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """Delete documents by their IDs from the Pinecone collection.

        Args:
            collection_name: Name of the collection
            document_ids: List of document IDs to delete

        Raises:
            DocumentError: If deletion fails
        """
        try:
            index = self.pc.Index(collection_name)

            # Get all vectors with the specified document_ids
            # Note: Pinecone doesn't support filtering by metadata in delete operations
            # We need to query first to get the vector IDs, then delete them
            for doc_id in document_ids:
                # Query for vectors with this document_id
                results = index.query(
                    vector=[0.0] * self.settings.embedding_dim,  # Dummy vector
                    top_k=10000,  # Large number to get all vectors
                    include_metadata=True,
                    filter={"document_id": doc_id},
                )

                # Extract vector IDs and delete them
                vector_ids = [match["id"] for match in results["matches"]]
                if vector_ids:
                    index.delete(ids=vector_ids)

            logging.info("Deleted documents from collection '%s'", collection_name)
        except Exception as e:
            logging.error("Failed to delete documents from Pinecone collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to delete documents from Pinecone collection '{collection_name}': {e}") from e

    def _process_search_results(self, results: Any, collection_name: str) -> list[QueryResult]:  # noqa: ARG002
        """Process Pinecone search results into QueryResult objects."""
        query_results = []

        for match in results["matches"]:
            metadata = match.get("metadata", {})

            # Create DocumentChunkWithScore
            chunk = DocumentChunkWithScore(
                chunk_id=match["id"],
                text=metadata.get("text", ""),
                embeddings=None,  # Pinecone doesn't return embeddings in search results
                metadata=DocumentChunkMetadata(
                    source=Source(metadata.get("source", "OTHER")),
                    document_id=metadata.get("document_id", ""),
                    page_number=metadata.get("page_number", 0),
                    chunk_number=metadata.get("chunk_number", 0),
                ),
                document_id=metadata.get("document_id", ""),
                score=float(match["score"]),
            )

            query_results.append(QueryResult(chunk=chunk, score=float(match["score"]), embeddings=[]))

        return query_results
