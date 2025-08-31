import logging
from typing import Any

import weaviate
import weaviate.classes as wvc
from weaviate.classes.config import DataType, Property
from weaviate.data import DataObject
from weaviate.exceptions import WeaviateConnectionError
from weaviate.util import generate_uuid5

from core.config import settings
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
from .error_types import CollectionError
from .vector_store import VectorStore  # Ensure this import is correct


class WeaviateDataStore(VectorStore):

    def __init__(self) -> None:
        auth_credentials = self._build_auth_credentials()
        try:
            logging.debug(f"Connecting to weaviate instance at {settings.weaviate_host} & \
                {settings.weaviate_port} with credential type {type(auth_credentials).__name__}")
            self.client = weaviate.connect_to_custom(
                http_host=settings.weaviate_host,
                http_port=settings.weaviate_port,
                http_secure=False,
                grpc_host=settings.weaviate_host,
                grpc_port=settings.weaviate_grpc_port,
                grpc_secure=False,
                auth_credentials=auth_credentials,
            )
        except WeaviateConnectionError as e:
            logging.error(f"Failed to connect to Weaviate: {e}")
            raise CollectionError(f"Failed to connect to Weaviate: {e}")

    def handle_errors(self, results: list[dict[str, Any]] | None) -> list[str]:
        if not self or not results:
            return []

        error_messages = []
        for result in results:
            if ("result" not in result or "errors" not in result["result"] or "error" not in result["result"]["errors"]):
                continue
            for message in result["result"]["errors"]["error"]:
                error_messages.append(message["message"])
                logging.exception(message["message"])

        return error_messages

    @staticmethod
    def _build_auth_credentials() -> weaviate.auth.AuthCredentials | None:
        if settings.weaviate_username and settings.weaviate_password:
            return weaviate.auth.AuthClientPassword(
                settings.weaviate_username, settings.weaviate_password, settings.weaviate_scopes
            )
        else:
            return None

    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        chunks: dict[str, list[DocumentChunk]] = {}
        for document in documents:
            if document.document_id is None:
                raise ValueError("Document ID cannot be none")
            for doc_chunk in document.chunks:
                doc_chunk.document_id = document.document_id  # Ensure each chunk references its parent document
                if document.document_id not in chunks:
                    chunks[document.document_id] = []
                chunks[document.document_id].append(doc_chunk)

        doc_ids = self._upsert(collection_name, chunks)
        return doc_ids

    def _upsert(self, collection_name: str, chunks: dict[str, list[DocumentChunk]]) -> list[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        doc_ids = []
        question_objs = []
        collection = self.get_collection(collection_name)

        with collection.batch.dynamic():
            for doc_id, doc_chunks in chunks.items():
                logging.debug(f"Upserting {doc_id} with {len(doc_chunks)} chunks")
                for doc_chunk in doc_chunks:
                    # generate a unique id for weaviate to store each chunk
                    doc_uuid = generate_uuid5(doc_chunk, collection_name)
                    question_objs.append(
                        wvc.data.DataObject(
                            properties={
                                "chunk_id": doc_chunk.chunk_id,
                                "document_id": doc_id,
                                "text": doc_chunk.text,
                                "source": doc_chunk.metadata.source.value if doc_chunk.metadata and doc_chunk.metadata.source else "",
                                "source_id": doc_chunk.metadata.source_id if doc_chunk.metadata and doc_chunk.metadata.source_id else "",
                                "url": doc_chunk.metadata.url if doc_chunk.metadata and doc_chunk.metadata.url else "",
                                "created_at": doc_chunk.metadata.created_at if doc_chunk.metadata and doc_chunk.metadata.created_at else None,
                                "author": doc_chunk.metadata.author if doc_chunk.metadata and doc_chunk.metadata.author else None,
                            },
                            uuid=doc_uuid,
                            vector=doc_chunk.vectors,
                        )
                    )

                doc_ids.append(doc_id)
            collection.data.insert_many(question_objs)
            return doc_ids

    def get_collection(self, name: str) -> DataObject:
        if self.client and self.client.collections.exists(name):
            return self.client.collections.get(name)
        raise ValueError(f"Collection {name} does not exist")

    def create_collection(self, collection_name: str, metadata: dict | None = None) -> None:
        if self.client and self.client.collections.exists(collection_name):
            logging.debug(f"Index {collection_name} already exists")
        else:
            try:
                self.client.collections.create(
                    name=collection_name,
                    vectorizer_config=wvc.config.Configure.Vectorizer.none(),
                    properties=[
                        Property(name="document_id", data_type=DataType.TEXT),
                        Property(name="chunk_id", data_type=DataType.TEXT),
                        Property(name="text", data_type=DataType.TEXT, vectorize_property_name=True),
                        Property(name="source", data_type=DataType.TEXT),
                        Property(name="source_id", data_type=DataType.TEXT),
                        Property(name="url", data_type=DataType.TEXT),
                        Property(name="created_at", data_type=DataType.DATE),
                        Property(name="author", data_type=DataType.TEXT),
                    ],
                    vector_index_config=wvc.config.Configure.VectorIndex.hnsw(
                        distance_metric=wvc.config.VectorDistances.COSINE
                    ),
                )
            except Exception as e:
                logging.error(f"Failed to create index {collection_name}: {e}")
                raise CollectionError(f"Failed to create collection '{collection_name}': {e}")

    def delete_collection_async(self, collection_name: str) -> None:
        if self.client and self.client.collections:
            self.client.collections.delete(collection_name)
        else:
            logging.error(f"Collection {collection_name} does not exist")

    def query(self, collection_name: str, query: QueryWithEmbedding, number_of_results: int = 10,
              filter: DocumentMetadataFilter | None = None) -> list[QueryResult]:

        result = self.client.collections.get(collection_name).query.near_vector(
            near_vector=query.vectors, number_of_results=number_of_results)

        query_results: list[QueryResult] = []
        response_objects = result.objects

        for obj in response_objects:
            properties = obj.properties
            document_chunk_with_score = DocumentChunk(
                chunk_id=properties["chunk_id"],
                text=properties["text"],
                metadata=DocumentChunkMetadata(
                    source=Source(properties["source"]),
                    source_id=(properties.get("source_id", "")),
                    url=properties.get("url", ""),
                    created_at=(properties.get("created_at", "")),
                    author=properties.get("author", ""),
                ),
            )

            # prepare QueryResult object to return
            query_result = QueryResult(
                data=[document_chunk_with_score],
                similarities=[obj.vector if obj.vector else 0.0],
                ids=[properties["chunk_id"]],
            )
            query_results.append(query_result)

        return query_results

    def delete_documents(self, collection_name: str, document_ids: list[str]):
        """
        Removes vectors by ids, filter, or everything in the datastore.
        Returns whether the operation was successful.
        """
        if not self.client.collections.exists(collection_name):
            logging.error(f"Collection {collection_name} does not exist")
            return False

        if not document_ids:
            logging.error("No document IDs provided for deletion")
            return False

        try:
            collection = self.get_collection(collection_name)
            for doc_id in document_ids:
                collection.data.delete_by_id(doc_id)
        except Exception as e:
            logging.error(f"Failed to delete documents from Weaviate index '{collection_name}': {e}")
            raise CollectionError(f"Failed to delete documents from Weaviate index '{collection_name}': {e}")

    def retrieve_documents(self, query: str, collection_name: str, number_of_results: int = 10) -> list[QueryResult]:
        if not self.client.collections.exists(collection_name):
            raise CollectionError(f"Collection '{collection_name}' does not exist")

        # Assuming you have some method to generate embeddings from text
        embeddings = get_embeddings(query)
        query_with_embedding = QueryWithEmbedding(
            text=query, vectors=embeddings)
        logging.debug(f"Query with embedding: {query_with_embedding}")
        return self.query(collection_name, query_with_embedding, number_of_results=number_of_results)
