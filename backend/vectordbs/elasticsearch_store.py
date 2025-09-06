import logging
from typing import Any

from elasticsearch import Elasticsearch, NotFoundError

from core.config import Settings, get_settings
from vectordbs.utils.watsonx import get_embeddings

from .data_types import (
    Document,
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
    Source,
)
from .error_types import CollectionError, DocumentError
from .vector_store import VectorStore

# Remove module-level constants - use dependency injection instead


class ElasticSearchStore(VectorStore):
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
            if self.settings.elastic_cacert_path:
                client_kwargs["ca_certs"] = self.settings.elastic_cacert_path

            self.client = Elasticsearch(**client_kwargs)

    def create_collection(self, collection_name: str, metadata: dict | None = None) -> None:  # noqa: ARG002
        """
        Create a new Elasticsearch index.

        Args:
            name (str): The name of the index to create.
            embedding_model_id (str): The ID of the embedding model.
        """
        try:
            settings = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "knn": True,
                    "knn.algo_param.ef_search": 100,
                },
                "mappings": {
                    "properties": {
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": self.settings.embedding_dim,
                        },
                        "text": {"type": "text"},
                        "source": {"type": "keyword"},
                        "url": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "author": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                    }
                },
            }
            self.client.indices.create(index=collection_name, body=settings)
            logging.info(f"Collection '{collection_name}' created successfully")
        except Exception as e:
            logging.error(f"Failed to create collection '{collection_name}': {e}", exc_info=True)
            raise CollectionError(f"Failed to create collection '{collection_name}': {e}") from e

    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """
        Add documents to the specified Elasticsearch index.

        Args:
            collection_name (str): The name of the index to add documents to.
            documents (List[Document]): A list of documents to add.

        Returns:
            List[str]: The list of document IDs that were added.
        """
        try:
            document_ids = []
            for document in documents:
                # Get embeddings for the first chunk (assuming single chunk per document for now)
                if document.chunks:
                    chunk = document.chunks[0]
                    embeddings = get_embeddings(chunk.text, settings=self.settings)
                    body = {
                        "text": chunk.text,
                        "embedding": embeddings,
                        "source": chunk.metadata.source if chunk.metadata else "unknown",
                        "document_id": document.document_id,
                        "chunk_id": chunk.chunk_id,
                    }
                    # Index the document and get the response
                    response = self.client.index(index=collection_name, body=body)
                    # Elasticsearch returns the document ID in the response
                    if response and "_id" in response:
                        document_ids.append(response["_id"])
                    else:
                        document_ids.append(chunk.chunk_id)  # Fallback to chunk_id
                else:
                    continue
            logging.info(f"Documents added to collection '{collection_name}' successfully")
            return document_ids
        except Exception as e:
            logging.error(f"Failed to add documents to collection '{collection_name}': {e}", exc_info=True)
            raise DocumentError(f"Failed to add documents to collection '{collection_name}': {e}") from e

    def retrieve_documents(
        self,
        query: str,
        collection_name: str,
        limit: int = 10,
    ) -> list[QueryResult]:
        """
        Retrieve documents from the specified Elasticsearch index based on a query.

        Args:
            query (str): The query string.
            collection_name (Optional[str]): The name of the index to query.
            limit (int): The number of results to return.

        Returns:
            List[QueryResult]: A list of query results.
        """
        try:
            response = self.client.search(index=collection_name, body={"query": {"match": {"text": query}}, "size": limit})
            # Convert ObjectApiResponse to dict
            response_dict = response.body if hasattr(response, "body") else dict(response)
            return self._process_search_results(response_dict)
        except Exception as e:
            logging.error(f"Failed to retrieve documents from index '{collection_name}': {e}", exc_info=True)
            raise DocumentError(f"Failed to retrieve documents from index '{collection_name}': {e}") from e

    def query(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        filter: DocumentMetadataFilter | None = None,
    ) -> list[QueryResult]:
        """
        Query the specified Elasticsearch index using KNN.

        Args:
            collection_name (str): The name of the index to query.
            query (QueryWithEmbedding): The query embedding.
            number_of_results (int): The number of results to return.
            filter (Optional[DocumentMetadataFilter]): A filter to apply to the query.

        Returns:
            List[QueryResult]: A list of query results.
        """
        try:
            body = {
                "size": number_of_results,
                "query": {
                    "bool": {
                        "must": {
                            "knn": {
                                "field": "embedding",
                                "query_vector": query.embeddings,
                                "k": number_of_results,
                                "num_candidates": 100,
                            }
                        },
                        "filter": self._build_filters(filter),
                    }
                },
            }
            response = self.client.search(index=collection_name, body=body)
            # Convert ObjectApiResponse to dict
            response_dict = response.body if hasattr(response, "body") else dict(response)
            return self._process_search_results(response_dict)
        except Exception as e:
            logging.error(f"Failed to query documents from index '{collection_name}': {e}", exc_info=True)
            raise DocumentError(f"Failed to query documents from index '{collection_name}': {e}") from e

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete the specified Elasticsearch index.

        Args:
            collection_name (str): The name of the index to delete.
        """
        try:
            self.client.indices.delete(index=collection_name)
            logging.info(f"Collection '{collection_name}' deleted successfully")
        except NotFoundError:
            logging.warning(f"Collection '{collection_name}' not found")
        except Exception as e:
            logging.error(f"Failed to delete collection '{collection_name}': {e}", exc_info=True)
            raise CollectionError(f"Failed to delete collection '{collection_name}': {e}") from e

    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """
        Delete documents from the specified Elasticsearch index.

        Args:
            document_ids (List[str]): A list of document IDs to delete.
            collection_name (Optional[str]): The name of the index to delete documents from.
        """
        try:
            for document_id in document_ids:
                self.client.delete(index=collection_name, id=document_id)
            logging.info(f"Documents deleted from collection '{collection_name}' successfully")
        except Exception as e:
            logging.error(f"Failed to delete documents from collection '{collection_name}': {e}", exc_info=True)
            raise DocumentError(f"Failed to delete documents from collection '{collection_name}': {e}") from e

    def _build_filters(self, filter: DocumentMetadataFilter | None) -> dict[str, Any]:
        """Build Elasticsearch filters from a DocumentMetadataFilter."""
        if not filter:
            return {}
        filters = []
        if filter.operator.lower() in ["eq", "equals", "term"]:
            field_filter = {"term": {filter.field_name: filter.value}}
            filters.append(field_filter)
        elif filter.operator.lower() == "gte":
            range_filter = {"range": {filter.field_name: {"gte": filter.value}}}
            filters.append(range_filter)
        elif filter.operator.lower() == "lte":
            range_filter = {"range": {filter.field_name: {"lte": filter.value}}}
            filters.append(range_filter)
        return {"bool": {"filter": filters}}

    def _process_search_results(self, response: dict[str, Any]) -> list[QueryResult]:
        """Process Elasticsearch search results into QueryResult objects."""
        results = []
        hits = response.get("hits", {}).get("hits", [])

        for hit in hits:
            source = hit.get("_source", {})
            score = hit.get("_score", 0.0)

            # Create DocumentChunk from source
            chunk = DocumentChunk(
                chunk_id=source.get("chunk_id", ""),
                text=source.get("text", ""),
                embeddings=source.get("embedding", []),
                metadata=DocumentChunkMetadata(
                    source=Source(source.get("source", "unknown")),
                    document_id=source.get("document_id"),
                ),
                document_id=source.get("document_id"),
            )

            # Create QueryResult
            result = QueryResult(chunk=chunk, score=score, embeddings=source.get("embedding", []))
            results.append(result)

        return results
