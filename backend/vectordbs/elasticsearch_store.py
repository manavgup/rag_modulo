import logging
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch, NotFoundError

from core.config import settings
from vectordbs.utils.watsonx import get_embeddings

from .data_types import (Document, DocumentChunk, DocumentChunkMetadata,
                         DocumentMetadataFilter, QueryResult,
                         QueryWithEmbedding, Source)
from .error_types import CollectionError, DocumentError
from .vector_store import VectorStore

logging.basicConfig(level=settings.log_level)

ELASTICSEARCH_HOST = settings.elastic_host
ELASTICSEARCH_PORT = settings.elastic_port
ELASTICSEARCH_INDEX = settings.collection_name
EMBEDDING_MODEL = settings.embedding_model
EMBEDDING_DIM = settings.embedding_dim
ELASTIC_PASSWORD = settings.elastic_password
ELASTIC_CACERT_PATH = settings.elastic_cacert_path
ELASTIC_CLOUD_ID = settings.elastic_cloud_id
ELASTIC_API_KEY = settings.elastic_api_key


class ElasticSearchStore(VectorStore):
    def __init__(self, host: str = ELASTICSEARCH_HOST, port: int = int(ELASTICSEARCH_PORT)) -> None:
        self.index_name = ELASTICSEARCH_INDEX
        if ELASTIC_CLOUD_ID:
            self.client = Elasticsearch(ELASTIC_CLOUD_ID, api_key=ELASTIC_API_KEY)
        else:
            self.client = Elasticsearch(
                hosts=[{"host": host, "port": int(port), "scheme": "https"}],
                ca_certs=ELASTIC_CACERT_PATH,
                basic_auth=("elastic", ELASTIC_PASSWORD),
                verify_certs=False  # Disable SSL verification
            )

    def create_collection(self, collection_name: str, metadata: Optional[dict] = None) -> None:
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
                            "dimension": EMBEDDING_DIM,
                        },
                        "text": {"type": "text"},
                        "source": {"type": "keyword"},
                        "url": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "author": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"}
                    }
                },
            }
            self.client.indices.create(index=collection_name, body=settings)
            logging.info(f"Collection '{collection_name}' created successfully")
        except Exception as e:
            logging.error(f"Failed to create collection '{collection_name}': {e}", exc_info=True)
            raise CollectionError(f"Failed to create collection '{collection_name}': {e}")

    def add_documents(self, collection_name: str, documents: List[Document]) -> None:
        """
        Add documents to the specified Elasticsearch index.

        Args:
            collection_name (str): The name of the index to add documents to.
            documents (List[Document]): A list of documents to add.
        """
        try:
            for document in documents:
                # Get embeddings for the first chunk (assuming single chunk per document for now)
                if document.chunks:
                    chunk = document.chunks[0]
                    embeddings = get_embeddings(chunk.text, EMBEDDING_MODEL)
                    body = {
                        "text": chunk.text,
                        "embedding": embeddings,
                        "source": chunk.metadata.source if chunk.metadata else "unknown",
                        "document_id": document.document_id,
                        "chunk_id": chunk.chunk_id,
                    }
                else:
                    continue
                self.client.index(index=collection_name, body=body)
            logging.info(f"Documents added to collection '{collection_name}' successfully")
        except Exception as e:
            logging.error(f"Failed to add documents to collection '{collection_name}': {e}", exc_info=True)
            raise DocumentError(f"Failed to add documents to collection '{collection_name}': {e}")

    def retrieve_documents(
        self,
        query: str,
        collection_name: str,
        limit: int = 10,
    ) -> List[QueryResult]:
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
            response = self.client.search(
                index=collection_name,
                body={
                    "query": {
                        "match": {
                            "text": query
                        }
                    },
                    "size": limit
                }
            )
            return self._process_search_results(response)
        except Exception as e:
            logging.error(f"Failed to retrieve documents from index '{collection_name}': {e}", exc_info=True)
            raise DocumentError(f"Failed to retrieve documents from index '{collection_name}': {e}")

    def query(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        filter: Optional[DocumentMetadataFilter] = None,
    ) -> List[QueryResult]:
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
                }
            }
            response = self.client.search(index=collection_name, body=body)
            return self._process_search_results(response)
        except Exception as e:
            logging.error(f"Failed to query documents from index '{collection_name}': {e}", exc_info=True)
            raise DocumentError(f"Failed to query documents from index '{collection_name}': {e}")

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
            raise CollectionError(f"Failed to delete collection '{collection_name}': {e}")

    def delete_documents(self, collection_name: str, document_ids: List[str]) -> None:
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
            raise DocumentError(f"Failed to delete documents from collection '{collection_name}': {e}")

    def _build_filters(
        self, filter: Optional[DocumentMetadataFilter]
    ) -> Dict[str, Any]:
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

    def _process_search_results(self, response: Dict[str, Any]) -> List[QueryResult]:
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
            result = QueryResult(
                chunk=chunk,
                score=score,
                embeddings=source.get("embedding", [])
            )
            results.append(result)
        
        return results
