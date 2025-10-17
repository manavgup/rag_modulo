"""Elasticsearch vector store implementation.

This module provides an Elasticsearch-based implementation of the VectorStore interface,
enabling document storage, retrieval, and search operations using Elasticsearch.
"""

import logging
from typing import Any

from elasticsearch import Elasticsearch, NotFoundError

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
from .error_types import CollectionError, DocumentError
from .vector_store import VectorStore

# Remove module-level constants - use dependency injection instead


class ElasticSearchStore(VectorStore):
    """Elasticsearch implementation of the VectorStore interface.

    This class provides Elasticsearch-based vector storage and retrieval capabilities,
    including document management, collection operations, and similarity search.
    """

    def __init__(self, host: str | None = None, port: int | None = None, settings: Settings = get_settings()) -> None:
        # Call parent constructor for proper dependency injection
        super().__init__(settings)

        # Configure logging
        logging.basicConfig(level=self.settings.log_level)

        # Use provided values or fall back to settings with proper defaults
        actual_host = host or self.settings.elastic_host or "localhost"
        actual_port = port or (int(self.settings.elastic_port) if self.settings.elastic_port else 9200)

        self.index_name = self.settings.collection_name
        if self.settings.elastic_cloud_id and self.settings.elastic_api_key:
            self.client = Elasticsearch(self.settings.elastic_cloud_id, api_key=self.settings.elastic_api_key)
        else:
            # Build client arguments dynamically to handle None values
            client_kwargs: dict[str, Any] = {
                "hosts": [{"host": actual_host, "port": actual_port, "scheme": "https"}],
                "verify_certs": False,  # Disable SSL verification
            }

            # Only add basic_auth if password is available
            if self.settings.elastic_password:
                client_kwargs["basic_auth"] = ("elastic", self.settings.elastic_password)

            # Only add ca_certs if path is available
            if hasattr(self.settings, "elastic_ca_certs") and self.settings.elastic_ca_certs:
                client_kwargs["ca_certs"] = self.settings.elastic_ca_certs

            self.client = Elasticsearch(**client_kwargs)

        # Test connection
        try:
            if not self.client.ping():
                raise ConnectionError("Failed to connect to Elasticsearch")
            logging.info("Connected to Elasticsearch")
        except Exception as e:
            logging.error("Failed to connect to Elasticsearch: %s", str(e))
            raise CollectionError(f"Failed to connect to Elasticsearch: {e}") from e

    def create_collection(self, collection_name: str, metadata: dict | None = None) -> None:
        """Create a collection (index) in Elasticsearch."""
        try:
            # Create index with mapping for vector search
            index_body = {
                "mappings": {
                    "properties": {
                        "text": {"type": "text"},
                        "embeddings": {
                            "type": "dense_vector",
                            "dims": 1536,
                        },  # Adjust dims based on your embedding model
                        "metadata": {"type": "object"},
                        "document_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                    }
                }
            }
            if metadata:
                index_body["settings"] = metadata

            self.client.indices.create(index=collection_name, body=index_body)
            logging.info("Collection '%s' created successfully", collection_name)
        except Exception as e:
            logging.error("Failed to create collection '%s': %s", collection_name, str(e))
            raise CollectionError(f"Failed to create collection '{collection_name}': {e}") from e

    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """Adds documents to the vector store."""
        self._create_collection_if_not_exists(collection_name)

        document_ids = []
        for document in documents:
            for chunk in document.chunks:
                doc_body = {
                    "text": chunk.text,
                    "embeddings": chunk.embeddings,
                    "metadata": {
                        "source": str(chunk.metadata.source) if chunk.metadata and chunk.metadata.source else "OTHER",
                        "document_id": chunk.document_id or "",
                    },
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                }

                try:
                    self.client.index(index=collection_name, id=chunk.chunk_id, body=doc_body)
                    document_ids.append(chunk.document_id)
                except Exception as e:
                    logging.error("Failed to add document to Elasticsearch: %s", str(e))
                    raise DocumentError(f"Failed to add document to Elasticsearch: {e}") from e

        return document_ids

    def retrieve_documents(self, query: str, collection_name: str, limit: int = 10) -> list[QueryResult]:
        """
        Retrieves documents based on a query string.

        Args:
            query (str): The query string.
            collection_name (str): The name of the collection to retrieve from.
            limit (int): The maximum number of results to return.

        Returns:
            List[QueryResult]: The list of query results.
        """
        query_embeddings = get_embeddings(query, settings=self.settings)
        if not query_embeddings:
            raise DocumentError("Failed to generate embeddings for the query string.")
        # get_embeddings returns list[list[float]], but we need list[float] for single query
        query_with_embedding = QueryWithEmbedding(text=query, embeddings=query_embeddings[0])
        return self.query(collection_name, query_with_embedding, number_of_results=limit)

    def query(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        metadata_filter: DocumentMetadataFilter | None = None,  # noqa: ARG002
    ) -> list[QueryResult]:
        """
        Queries the vector store with filtering and query mode options.

        Args:
            collection_name (str): The name of the collection to query.
            query (QueryWithEmbedding): The query with embedding to search for.
            number_of_results (int): The maximum number of results to return.
            metadata_filter (Optional[DocumentMetadataFilter]): Optional filter to apply to the query.

        Returns:
            List[QueryResult]: The list of query results.
        """
        try:
            # Elasticsearch vector search query
            search_body = {
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'embeddings') + 1.0",
                            "params": {"query_vector": query.embeddings[0]},
                        },
                    }
                },
                "size": number_of_results,
            }

            response = self.client.search(index=collection_name, body=search_body)
            logging.info("Query response: %s", response)
            return self._process_search_results(response, collection_name)
        except Exception as e:
            logging.error("Failed to query Elasticsearch collection '%s': %s", collection_name, str(e))
            raise DocumentError(f"Failed to query Elasticsearch collection '{collection_name}': {e}") from e

    def delete_collection(self, collection_name: str) -> None:
        """Deletes a collection (index) from the vector store."""
        try:
            self.client.indices.delete(index=collection_name)
            logging.info("Deleted collection '%s'", collection_name)
        except NotFoundError:
            logging.warning("Collection '%s' not found", collection_name)
        except Exception as e:
            logging.error("Failed to delete Elasticsearch collection: %s", str(e))
            raise CollectionError(f"Failed to delete Elasticsearch collection: {e}") from e

    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """Deletes documents by their IDs from the vector store."""
        try:
            for doc_id in document_ids:
                # Delete by document_id field
                query = {"query": {"term": {"document_id": doc_id}}}
                self.client.delete_by_query(index=collection_name, body=query)
            logging.info("Deleted %d documents from collection '%s'", len(document_ids), collection_name)
        except Exception as e:
            logging.error("Failed to delete documents from Elasticsearch collection '%s': %s", collection_name, str(e))
            raise DocumentError(
                f"Failed to delete documents from Elasticsearch collection '{collection_name}': {e}"
            ) from e

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
            # Use Elasticsearch count API with term query
            query = {"query": {"term": {"document_id": document_id}}}
            response = self.client.count(index=collection_name, body=query)
            chunk_count = response.get("count", 0)
            logging.debug("Found %d chunks for document %s in collection %s", chunk_count, document_id, collection_name)
            return chunk_count
        except NotFoundError as e:
            logging.warning("Collection '%s' not found", collection_name)
            raise CollectionError(f"Collection '{collection_name}' not found") from e
        except Exception as e:
            logging.warning(
                "Error counting chunks for document %s in collection %s: %s", document_id, collection_name, str(e)
            )
            raise DocumentError(
                f"Failed to count chunks for document '{document_id}' in collection '{collection_name}': {e}"
            ) from e

    def _create_collection_if_not_exists(self, collection_name: str) -> None:
        """Create a collection if it doesn't exist."""
        try:
            self.client.indices.get(index=collection_name)
        except NotFoundError:
            self.create_collection(collection_name)

    def _process_search_results(self, response: Any, collection_name: str) -> list[QueryResult]:  # noqa: ARG002
        """Process Elasticsearch search results into QueryResult objects."""
        results = []
        hits = response.get("hits", {}).get("hits", [])

        for hit in hits:
            source = hit["_source"]
            score = hit["_score"]

            # Create DocumentChunkWithScore
            chunk = DocumentChunkWithScore(
                chunk_id=source["chunk_id"],
                text=source["text"],
                embeddings=source["embeddings"],
                metadata=DocumentChunkMetadata(
                    source=Source(source["metadata"]["source"]) if source["metadata"]["source"] else Source.OTHER,
                    document_id=source["metadata"]["document_id"],
                ),
                document_id=source["document_id"],
                score=score,
            )

            results.append(QueryResult(chunk=chunk, score=score, embeddings=[]))

        return results
