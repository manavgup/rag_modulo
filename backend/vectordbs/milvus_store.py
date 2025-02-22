"""Milvus vector store implementation."""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from pymilvus import (Collection, CollectionSchema, DataType, FieldSchema,
                     MilvusException, connections, utility)

from core.config import settings
from vectordbs.utils.watsonx import get_embeddings

from .data_types import (Document, DocumentChunk, DocumentChunkMetadata,
                        DocumentMetadataFilter, Embedding, QueryResult,
                        QueryWithEmbedding, Source)
from .error_types import CollectionError, DocumentError, VectorStoreError
from .vector_store import VectorStore

logger = logging.getLogger(__name__)

# Configuration constants
MILVUS_COLLECTION = settings.collection_name
MILVUS_HOST = settings.milvus_host
MILVUS_PORT = settings.milvus_port
MILVUS_USER = settings.milvus_user
MILVUS_PASSWORD = settings.milvus_password
MILVUS_USE_SECURITY = False if MILVUS_PASSWORD is None else True
EMBEDDING_DIM = settings.embedding_dim
EMBEDDING_FIELD = settings.embedding_field
EMBEDDING_MODEL = settings.embedding_model
MILVUS_INDEX_PARAMS = settings.milvus_index_params
MILVUS_SEARCH_PARAMS = settings.milvus_search_params

# Schema definition
SCHEMA = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name=EMBEDDING_FIELD, dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100),
    # Document metadata fields
    FieldSchema(name="document_name", dtype=DataType.VARCHAR, max_length=65535),
    # Chunk metadata fields
    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=20),
    FieldSchema(name="page_number", dtype=DataType.INT64),
    FieldSchema(name="chunk_number", dtype=DataType.INT64),
    FieldSchema(name="start_index", dtype=DataType.INT64),
    FieldSchema(name="end_index", dtype=DataType.INT64),
]


class MilvusStore(VectorStore):
    """Milvus vector store implementation."""

    def __init__(self, host: str = MILVUS_HOST, port: str = MILVUS_PORT) -> None:
        """Initialize MilvusStore with connection parameters.

        Args:
            host: The host address for Milvus
            port: The port for Milvus
        """
        self._connect(host, port)

    def _connect(self, host: str, port: str) -> None:
        """Connect to the Milvus server.

        Args:
            host: Milvus server host
            port: Milvus server port

        Raises:
            VectorStoreError: If connection fails after retries
        """
        attempts = 3
        for attempt in range(attempts):
            try:
                connections.connect(
                    "default",
                    host=host,
                    port=port
                )
                logging.info(f"Connected to Milvus at {host}:{port}")
                return
            except MilvusException as e:
                logging.error(f"Failed to connect to Milvus at {host}:{port}: {e}")
                if attempt < attempts - 1:
                    logging.info(f"Retrying connection to Milvus... (Attempt {attempt + 2}/{attempts})")
                    time.sleep(10)
                raise VectorStoreError(f"Failed to connect to Milvus after {attempts} attempts")

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
        else:
            raise CollectionError(f"Collection '{collection_name}' does not exist")

    def create_collection(self, collection_name: str, metadata: Optional[dict] = None) -> Collection:
        """Create a new Milvus collection.

        Args:
            collection_name: Name of the collection to create
            metadata: Optional metadata for the collection

        Returns:
            Collection: The created collection

        Raises:
            CollectionError: If creation fails
        """
        try:
            if utility.has_collection(collection_name):
                raise CollectionError(f"Collection {collection_name} already exists.")
            
            schema = CollectionSchema(fields=SCHEMA)
            collection = Collection(name=collection_name, schema=schema)
            logging.info(f"Created Milvus collection '{collection_name}' with schema {schema}")
            
            self._create_index(collection)
            collection.load()
            return collection
            
        except MilvusException as e:
            logging.error(f"Failed to create collection '{collection_name}': {e}")
            raise CollectionError(f"Failed to create collection '{collection_name}': {e}")

    def _create_index(self, collection: Collection) -> None:
        """Create an index for the Milvus collection.

        Args:
            collection: The collection to create an index for

        Raises:
            CollectionError: If index creation fails
        """
        try:
            self.index_params = (json.loads(MILVUS_INDEX_PARAMS) if MILVUS_INDEX_PARAMS else None)
            self.search_params = (json.loads(MILVUS_SEARCH_PARAMS) if MILVUS_SEARCH_PARAMS else None)

            if len(collection.indexes) == 0:
                index_params = self.index_params or {
                    "metric_type": "IP",
                    "index_type": "HNSW",
                    "params": {"M": 8, "efConstruction": 64},
                }
                collection.create_index(field_name=EMBEDDING_FIELD, index_params=index_params)
                logging.info(f"Created index for collection '{collection.name}' with params {index_params}")
            else:
                logging.info(f"Index already exists for collection '{collection.name}'")
                
        except MilvusException as e:
            logging.error(f"Failed to create index for collection '{collection.name}': {e}")
            raise CollectionError(f"Failed to create index for collection '{collection.name}': {e}")

    def add_documents(self, collection_name: str, documents: List[Document]) -> List[str]:
        """Add documents to the collection.

        Args:
            collection_name: Name of the collection
            documents: List of documents to add

        Returns:
            List[str]: List of added document IDs

        Raises:
            DocumentError: If document addition fails
        """
        collection = self._get_collection(collection_name)
        try:
            data = []
            for document in documents:
                for chunk in document.chunks:
                    chunk_data = {
                        "document_id": document.document_id,
                        EMBEDDING_FIELD: chunk.embeddings,
                        "text": chunk.text,
                        "chunk_id": chunk.chunk_id,
                        "document_name": document.name,
                         # VARCHAR fields get empty string as default
                        "source": chunk.metadata.source.value if chunk.metadata else Source.OTHER.value,
                        # INT64 fields get 0 as default
                        "page_number": chunk.metadata.page_number if chunk.metadata else 0,
                        "chunk_number": chunk.metadata.chunk_number if chunk.metadata else 0,
                        "start_index": chunk.metadata.start_index if chunk.metadata else 0,
                        "end_index": chunk.metadata.end_index if chunk.metadata else 0,
                    }
                    data.append(chunk_data)                   
            collection.insert(data)
            collection.load()
            return [doc.document_id for doc in documents]
            
        except MilvusException as e:
            logging.error(f"Failed to add documents to collection {collection_name}: {e}", exc_info=True)
            raise DocumentError(f"Failed to add documents to collection {collection_name}: {e}")

    def retrieve_documents(
            self,
            query: str,
            collection_name: str,
            number_of_results: int = 10,
    ) -> List[QueryResult]:
        """Retrieve documents from the collection.

        Args:
            query: Query string
            collection_name: Name of the collection
            number_of_results: Maximum number of results to return

        Returns:
            List[QueryResult]: List of query results

        Raises:
            VectorStoreError: If retrieval fails
        """
        collection = self._get_collection(collection_name)

        embeddings = get_embeddings(texts=query)
        if not embeddings:
            raise VectorStoreError("Failed to generate embeddings for the query string.")
        query_embeddings = QueryWithEmbedding(text=query, embeddings=embeddings[0])

        try:
            logger.info(f"Retrieving for query: {query}")
            search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
            search_results = collection.search(
                data=[query_embeddings.embeddings],
                anns_field=EMBEDDING_FIELD,
                param=search_params,
                output_fields=[field.name for field in SCHEMA if field.name != "id"],
                limit=number_of_results,
            )
            return self._process_search_results(search_results)
            
        except MilvusException as e:
            logging.error(f"Failed to retrieve documents from collection '{collection_name}': {e}")
            raise CollectionError(f"Failed to retrieve documents from collection '{collection_name}': {e}")

    def _process_search_results(self, results: Any) -> List[QueryResult]:
        """Process search results from Milvus.

        Args:
            results: Raw search results from Milvus

        Returns:
            List[QueryResult]: Processed query results
        """
        if not results:
            logger.info("No search results. Returning empty list.")
            return []  # Return empty list instead of list with empty QueryResult

        query_results: List[QueryResult] = []
        for result in results:
            # Process each hit in the result separately to create individual QueryResults
            for hit in result:
                try:
                    chunk = DocumentChunk(
                        chunk_id=str(hit.id),
                        text=hit.entity.get("text") or "",
                        embeddings=hit.entity.get(EMBEDDING_FIELD),
                        metadata=DocumentChunkMetadata(
                            source=Source(hit.entity.get("source")) if hit.entity.get("source") else Source.OTHER,
                            page_number=hit.entity.get("page_number") if hit.entity.get("page_number") else 0,
                            chunk_number=hit.entity.get("chunk_number") if hit.entity.get("chunk_number") else 0,
                            start_index=hit.entity.get("start_index") if hit.entity.get("start_index") else 0,
                            end_index=hit.entity.get("end_index") if hit.entity.get("end_index") else 0,
                            document_id=hit.entity.get("document_id")
                        ),
                        document_id=hit.entity.get("document_id")
                    )
                    
                    # Create a single QueryResult for each hit
                    query_results.append(QueryResult(
                        chunk=chunk,
                        score=float(hit.distance),  # Single float score
                        embeddings=hit.entity.get(EMBEDDING_FIELD)  # List of embeddings
                    ))

                except Exception as e:
                    logger.error(f"Error processing hit: {e}", exc_info=True)
                    continue

        logger.info(f"Returning {len(query_results)} QueryResult objects")
        return query_results

    def delete_collection(self, name: str) -> None:
        """Delete a Milvus collection.

        Args:
            name: Name of the collection to delete

        Raises:
            CollectionError: If deletion fails
        """
        if utility.has_collection(name):
            try:
                utility.drop_collection(name)
                logging.info(f"Deleted collection '{name}'")
            except MilvusException as e:
                logging.error(f"Failed to delete collection '{name}': {e}")
                raise CollectionError(f"Failed to delete collection '{name}': {e}")
        else:
            logging.debug(f"Collection '{name}' does not exist.")

    def delete_documents(self, document_ids: List[str], collection_name: str) -> int:
        """Delete documents from the collection.

        Args:
            document_ids: List of document IDs to delete
            collection_name: Name of the collection

        Returns:
            int: Number of documents deleted

        Raises:
            CollectionError: If deletion fails
        """
        collection = self._get_collection(collection_name)
        try:
            expr = f"document_id in {tuple(document_ids)}"
            collection.delete(expr)
            logging.info(f"Deleted documents with IDs {document_ids} from collection '{collection_name}'")
            return len(document_ids)
        except MilvusException as e:
            logging.error(f"Failed to delete documents from collection '{collection_name}': {e}")
            raise CollectionError(f"Failed to delete documents from collection '{collection_name}': {e}")

    def query(
            self,
            collection_name: str,
            query: QueryWithEmbedding,
            number_of_results: int = 10,
            filter: Optional[DocumentMetadataFilter] = None,
    ) -> List[QueryResult]:
        """Query the collection with an embedding.

        Args:
            collection_name: Name of the collection to query
            query: Query with embedding
            number_of_results: Maximum number of results to return
            filter: Optional metadata filter

        Returns:
            List[QueryResult]: Query results

        Raises:
            CollectionError: If query fails
        """
        collection = self._get_collection(collection_name)

        try:
            search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
            result = collection.search(
                data=[query.embedding],
                anns_field=EMBEDDING_FIELD,
                param=search_params,
                output_fields=[field.name for field in SCHEMA if field.name != "id"],
                limit=number_of_results,
            )
            return self._process_search_results(result)
            
        except MilvusException as e:
            logging.error(f"Failed to query collection '{collection_name}': {e}")
            raise CollectionError(f"Failed to query collection '{collection_name}': {e}")
