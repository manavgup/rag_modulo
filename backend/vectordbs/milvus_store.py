import json
import logging
import time
from typing import Any, Dict, List, Optional

import asyncio
from pymilvus import (Collection, CollectionSchema, DataType, FieldSchema,
                      MilvusException, connections, utility)

from backend.vectordbs.data_types import (Document, DocumentChunk,
                                          DocumentChunkMetadata,
                                          DocumentChunkWithScore,
                                          DocumentMetadataFilter, Embeddings,
                                          QueryResult, QueryWithEmbedding, Source)
from backend.vectordbs.utils.watsonx import get_embeddings
from backend.vectordbs.vector_store import VectorStore
from backend.vectordbs.error_types import VectorStoreError, CollectionError, DocumentError
from backend.core.config import settings

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

SCHEMA = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name=EMBEDDING_FIELD, dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="source_id", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="url", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="author", dtype=DataType.VARCHAR, max_length=65535),
]


class MilvusStore(VectorStore):
    def __init__(self, host: str = MILVUS_HOST,
                 port: str = MILVUS_PORT) -> None:
        """
        Initialize MilvusStore with connection parameters.

        Args:
            host (str): The host address for Milvus.
            port (str): The port for Milvus.
        """
        self.collection_name = None
        self._connect(host, port)
        self.collection: Optional[Collection] = None

    def _connect(self, host: str, port: str) -> None:
        """
        Connect to the Milvus server.
        """
        attempts = 3
        for attempt in range(attempts):
            try:
                connections.connect(
                    "default",
                    host=host,
                    port=port,
                    user=MILVUS_USER,
                    password=MILVUS_PASSWORD,
                )
                logging.info(f"Connected to Milvus at {host}:{port}")
            except MilvusException as e:
                logging.error(f"Failed to connect to Milvus: {e}")
                if attempt < attempts - 1:
                    logging.info(f"Retrying connection to Milvus... (Attempt {attempt + 2}/{attempts})")
                    time.sleep(10)  # Add a delay between retries
                raise VectorStoreError(f"Failed to connect to Milvus: {e}")

    async def create_collection_async(self, collection_name: str,
                                      metadata: Optional[dict] = None) -> Collection:
        """
        Create a new Milvus collection.

        Args:
            collection_name (str): The name of the collection to create.
            metadata: Optional metadata for the collection.
        Returns:
            Collection: The created or loaded Milvus collection.
        """
        try:
            if await asyncio.to_thread(utility.has_collection, collection_name):
                raise CollectionError(f"Collection {collection_name} already exists.")
            else:
                schema = CollectionSchema(fields=SCHEMA)
                self.collection = Collection(name=collection_name, schema=schema)
                logging.info(f"Created Milvus collection '{collection_name}' with schema {schema}")
                print(f"Created Milvus collection '{collection_name}' with schema {schema}")
                self._create_index()
                self.collection_name = collection_name
                await asyncio.to_thread(self.collection.load)
        except MilvusException as e:
            logging.error(f"Failed to create collection '{collection_name}': {e}")
            raise CollectionError(f"Failed to create collection '{collection_name}': {e}")
        return self.collection

    def _create_index(self) -> None:
        """
        Create an index for the Milvus collection.
        """
        if self.collection is None:
            logging.error("Collection is not initialized")
            return

        try:
            self.index_params = (json.loads(MILVUS_INDEX_PARAMS) if MILVUS_INDEX_PARAMS else None)
            self.search_params = (json.loads(MILVUS_SEARCH_PARAMS) if MILVUS_SEARCH_PARAMS else None)

            if len(self.collection.indexes) == 0:
                if self.index_params:
                    self.collection.create_index(
                        field_name=EMBEDDING_FIELD,
                        index_params=self.index_params)
                    logging.info(
                        f"Created index for collection '{self.collection.name}' with params {self.index_params}")
                else:
                    i_p = {
                        "metric_type": "IP",
                        "index_type": "HNSW",
                        "params": {"M": 8, "efConstruction": 64},
                    }
                    self.collection.create_index(field_name=EMBEDDING_FIELD, index_params=i_p)
                    logging.info(f"Created default index for collection '{self.collection.name}'")
            else:
                logging.info(f"Index already exists for collection '{self.collection.name}'")
        except MilvusException as e:
            logging.error(f"Failed to create index for collection '{self.collection.name}': {e}")
            raise CollectionError(f"Failed to create index for collection '{self.collection.name}': {e}")

    async def add_documents_async(
        self, collection_name: str, documents: List[Document]
    ) -> List[str]:
        """
        Add a list of documents to the collection.

        Args:
            collection_name (str): The name of the collection to add documents to.
            documents (List[Document]): The list of documents to add.

        Returns:
            List[str]: The list of document IDs that were added.
        """
        if self.collection is None:
            raise ValueError("Collection is not initialized")

        try:
            data = []
            for document in documents:
                for chunk in document.chunks:
                    chunk.document_id = document.document_id
                    data.append(
                        {
                            "document_id": chunk.document_id,
                            "embedding": chunk.vectors,
                            "text": chunk.text,
                            "chunk_id": chunk.chunk_id,
                            "source_id": chunk.metadata.source_id if chunk.metadata else "",
                            "source": chunk.metadata.source.value if chunk.metadata else "",
                            "url": chunk.metadata.url if chunk.metadata else "",
                            "created_at": chunk.metadata.created_at if chunk.metadata else "",
                            "author": chunk.metadata.author if chunk.metadata else "",
                        }
                    )
            logging.debug(f"Inserting data: {data}")
            await asyncio.to_thread(self.collection.insert, data)
            await asyncio.to_thread(self.collection.load)
            logging.info(f"Successfully added documents to collection {collection_name}")
        except MilvusException as e:
            logging.error(f"Failed to add documents to collection {collection_name}: {e}", exc_info=True)
            raise DocumentError(f"Failed to add documents to collection {collection_name}: {e}")
        return [doc.document_id for doc in documents]

    async def retrieve_documents_async(
        self,
        query: str,
        collection_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[QueryResult]:
        """
        Retrieve documents from the collection.

        Args:
            query (Union[str, QueryWithEmbedding]): The query string or query with embedding.
            collection_name (Optional[str]): The name of the collection to retrieve documents from.
            limit (int): The maximum number of results to return.

        Returns:
            List[QueryResult]: The list of query results.
        """
        if self.collection is None:
            raise CollectionError("Collection is not initialized")

        if not collection_name:
            collection_name = self.collection_name

        if not await asyncio.to_thread(utility.has_collection, self.collection_name):
            raise CollectionError(f"Collection '{self.collection_name}' does not exist")

        embeddings = get_embeddings(query)
        if not embeddings:
            raise VectorStoreError("Failed to generate embeddings for the query string.")
        query_embeddings = QueryWithEmbedding(text=query, vectors=embeddings)

        try:
            search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
            search_results = await asyncio.to_thread(self.collection.search,
                                                     data=[query_embeddings.vectors],
                                                     anns_field=EMBEDDING_FIELD,
                                                     param=search_params,
                                                     output_fields=[
                                                         "chunk_id",
                                                         "text",
                                                         "document_id",
                                                         "embedding",
                                                         "source",
                                                         "source_id",
                                                         "url",
                                                         "created_at",
                                                         "author",
                                                         ],
                                                     limit=limit,
            )
            return self._process_search_results(search_results)
        except MilvusException as e:
            logging.error(f"Failed to retrieve documents from collection '{collection_name}': {e}")
            raise CollectionError(f"Failed to retrieve documents from collection '{collection_name}': {e}")

    async def delete_documents_async(self, document_ids: List[str],
                                     collection_name: Optional[str] = None) -> int:
        """
        Delete documents from the collection by their IDs.

        Args:
            document_ids (List[str]): The list of document IDs to delete.
            collection_name (Optional[str]): The name of the collection to delete documents from.

        Returns:
            int: The number of documents deleted.
        """
        if self.collection is None:
            raise CollectionError("Collection is not initialized")
        try:
            expr = f"document_id in {tuple(document_ids)}"
            await asyncio.to_thread(self.collection.delete, expr)
            logging.info(f"Deleted documents with IDs {document_ids} from collection '{collection_name}'")
            return len(document_ids)
        except MilvusException as e:
            logging.error(f"Failed to delete documents from collection '{collection_name}': {e}")
            raise CollectionError(f"Failed to delete documents from collection '{collection_name}': {e}")

    async def delete_collection_async(self, name: str) -> None:
        """
        Delete an existing Milvus collection.

        Args:
            name (str): The name of the collection to delete.
        """
        if not name and self.collection_name is not None:
            name = self.collection_name

        try:
            if await asyncio.to_thread(utility.has_collection, name):
                await asyncio.to_thread(utility.drop_collection, name)
                logging.info(f"Deleted collection '{name}'")
            else:
                logging.debug(f"Collection '{name}' does not exist.")
        except MilvusException as e:
            logging.error(f"Failed to delete collection '{name}': {e}")
            raise CollectionError(f"Failed to delete collection '{name}': {e}")

    def get_document(self, document_id: str, collection_name: Optional[str] = None) -> Optional[Document]:
        """
        Get a document by its ID from the collection.

        Args:
            document_id (str): The ID of the document to retrieve.
            collection_name (Optional[str]): The name of the collection to retrieve the document from.

        Returns:
            Optional[Document]: The retrieved document or None if not found.
        """
        if self.collection is None:
            raise CollectionError("Collection is not initialized")

        try:
            expr = f"document_id == '{document_id}'"
            results = self.collection.query(expr=expr, output_fields=["*"])
            if results:
                chunks = [self._convert_to_chunk(result) for result in results]
                return Document(document_id=document_id, name=document_id, chunks=chunks)
            return None
        except MilvusException as e:
            logging.error(f"Failed to get document '{document_id}' from collection '{collection_name}': {e}")
            raise CollectionError(f"Failed to get document '{document_id}' from collection '{collection_name}': {e}")

    async def query_async(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        filter: Optional[DocumentMetadataFilter] = None,
    ) -> List[QueryResult]:
        """
        Query the collection with an embedding query.

        Args:
            collection_name (str): The name of the collection to query.
            query (QueryWithEmbedding): The query with embedding to search for.
            number_of_results (int): The maximum number of results to return.
            filter (Optional[DocumentMetadataFilter]): Optional filter to apply to the query.

        Returns:
            List[QueryResult]: The list of query results.
        """
        if self.collection is None:
            raise CollectionError("Collection is not initialized")

        try:
            search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
            result = self.collection.search(
                data=[query.vectors],
                anns_field=EMBEDDING_FIELD,
                param=search_params,
                limit=number_of_results,
            )
            return self._process_search_results(result)
        except MilvusException as e:
            logging.error(f"Failed to query collection '{collection_name}': {e}")
            raise CollectionError(f"Failed to query collection '{collection_name}': {e}")

    def _convert_to_chunk(self, data: Dict[str, Any]) -> DocumentChunk:
        """
        Convert data to a DocumentChunk.

        Args:
            data (Dict[str, Any]): The data to convert.

        Returns:
            DocumentChunk: The converted DocumentChunk.
        """
        return DocumentChunk(
            chunk_id=str(data["chunk_id"]),
            text=data["text"],
            vectors=data["embedding"],
            metadata=DocumentChunkMetadata(
                source=Source(data["source"]),
                source_id=data.get("source_id"),
                url=data.get("url"),
                created_at=data.get("created_at"),
                author=data.get("author"),
            ),
            document_id=data["document_id"],
        )

    def _process_search_results(self, results: Any) -> List[QueryResult]:
        """
        Process search results from Milvus.

        Args:
            results (Any): The search results to process.

        Returns:
            List[QueryResult]: The list of query results.
        """
        if not results:
            return [QueryResult(data=[], similarities=[[]], ids=[])]

        chunks_with_scores = []
        similarities = []
        ids = []
        for result in results:
            for hit in result:
                chunks_with_scores.append(
                    DocumentChunkWithScore(
                        chunk_id=hit.entity.get("chunk_id"),
                        text=hit.entity.get("text"),
                        vectors=hit.entity.get("embedding"),
                        metadata=DocumentChunkMetadata(
                            source=(Source(hit.entity.get("source")) if hit.entity.get("source") else Source.OTHER),
                            source_id=(hit.entity.get("source_id") if hit.entity.get("source_id") else ""),
                            url=hit.entity.get("url") if hit.entity.get("url") else "",
                            created_at=(hit.entity.get("created_at") if hit.entity.get("created_at") else ""),
                            author=(hit.entity.get("author") if hit.entity.get("author") else ""),
                        ),
                        score=hit.distance,
                    )
                )
                ids.append(hit.entity.get("chunk_id"))
            similarities.append(result.distances)
        return [QueryResult(data=chunks_with_scores, similarities=similarities, ids=ids)]

    def save_embeddings_to_file(self, embeddings: Embeddings, file_path: str, file_format: str = "json") -> None:
        """
        Save embeddings to a file.

        Args:
            embeddings (Embeddings): The list of embeddings to save.
            file_path (str): The path to the output file.
            file_format (str): The file format ("json" or "txt").

        Raises:
            ValueError: If an unsupported file format is provided.
        """
        if file_format not in {"json", "txt"}:
            raise ValueError(f"Unsupported file format: {file_format}")

        try:
            if file_format == "json":
                with open(file_path, "w") as f:
                    json.dump(embeddings, f)
            elif file_format == "txt":
                with open(file_path, "w") as f:
                    for embedding in embeddings:
                        f.write(" ".join(map(str, embedding)) + "\n")
            logging.info(f"Saved embeddings to file '{file_path}' in format '{file_format}'")
        except Exception as e:
            logging.error(f"Failed to save embeddings to file '{file_path}': {e}")
            raise VectorStoreError(f"Failed to save embeddings to file '{file_path}': {e}")

    async def __aenter__(self) -> "MilvusStore":
        """
        Enter the runtime context related to this object.
        """
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """
        Exit the runtime context related to this object.
        """
        pass
