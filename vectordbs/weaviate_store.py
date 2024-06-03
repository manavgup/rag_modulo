# TODO
import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional, Union

import weaviate
import weaviate.classes as wvc
from weaviate import WeaviateClient
from weaviate.classes.config import DataType, Property
from weaviate.classes.query import Filter
from weaviate.data import DataObject
from weaviate.util import generate_uuid5

from vectordbs.data_types import (
    Document,
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    Embeddings,
    QueryResult,
    QueryWithEmbedding,
    Source,
)
from vectordbs.utils.watsonx import get_embeddings
from vectordbs.vector_store import VectorStore  # Ensure this import is correct

WEAVIATE_HOST = os.environ.get("WEAVIATE_HOST", "localhost")
WEAVIATE_PORT = os.environ.get("WEAVIATE_PORT", "8080")
WEAVIATE_GRPC_PORT = os.environ.get("WEAVIATE_GRPC_PORT", "50051")
WEAVIATE_USERNAME = os.environ.get("WEAVIATE_USERNAME", None)
WEAVIATE_PASSWORD = os.environ.get("WEAVIATE_PASSWORD", None)
WEAVIATE_SCOPES = os.environ.get("WEAVIATE_SCOPES", None)
WEAVIATE_INDEX = os.environ.get("WEAVIATE_INDEX", "DocumentChunk")

WEAVIATE_BATCH_SIZE = int(os.environ.get("WEAVIATE_BATCH_SIZE", 20))
WEAVIATE_BATCH_DYNAMIC = os.environ.get("WEAVIATE_BATCH_DYNAMIC", False)
WEAVIATE_BATCH_TIMEOUT_RETRIES = int(
    os.environ.get("WEAVIATE_TIMEOUT_RETRIES", 3))
WEAVIATE_BATCH_NUM_WORKERS = int(
    os.environ.get("WEAVIATE_BATCH_NUM_WORKERS", 1))


class WeaviateDataStore(VectorStore):

    def __init__(self) -> None:
        self.client: Optional[WeaviateClient] = None
        self.tokenizer_model: str = "sentence-transformers/all-minilm-l6-v2"
        self.collection: Optional[DataObject] = None
        auth_credentials = self._build_auth_credentials()

        logging.debug(f"Connecting to weaviate instance at {WEAVIATE_HOST} & {
            WEAVIATE_PORT} with credential type {type(auth_credentials).__name__}")
        self.client = weaviate.connect_to_custom(
            http_host=WEAVIATE_HOST,
            http_port=WEAVIATE_PORT,
            http_secure=False,
            grpc_host=WEAVIATE_HOST,
            grpc_port=WEAVIATE_GRPC_PORT,
            grpc_secure=False,
            auth_credentials=auth_credentials,
        )

    def handle_errors(
            self, results: Optional[List[Dict[str, Any]]]) -> List[str]:
        if not self or not results:
            return []

        error_messages = []
        for result in results:
            if (
                "result" not in result
                or "errors" not in result["result"]
                or "error" not in result["result"]["errors"]
            ):
                continue
            for message in result["result"]["errors"]["error"]:
                error_messages.append(message["message"])
                logging.exception(message["message"])

        return error_messages

    @staticmethod
    def _build_auth_credentials() -> Optional[weaviate.auth.AuthCredentials]:
        if WEAVIATE_USERNAME and WEAVIATE_PASSWORD:
            return weaviate.auth.AuthClientPassword(
                WEAVIATE_USERNAME, WEAVIATE_PASSWORD, WEAVIATE_SCOPES
            )
        else:
            return None

    async def add_documents(
        self, collection_name: str, documents: List[Document]
    ) -> List[str]:
        chunks: Dict[str, List[DocumentChunk]] = {}
        for document in documents:
            if document.document_id is None:
                raise ValueError("Document ID is cannot be none")
            for doc_chunk in document.chunks:
                doc_chunk.document_id = (
                    document.document_id
                )  # Ensure each chunk references its parent document
                if document.document_id not in chunks:
                    chunks[document.document_id] = []
                chunks[document.document_id].append(doc_chunk)

        doc_ids = await self._upsert(collection_name, chunks)
        return doc_ids

    async def _upsert(
        self, collection_name: str, chunks: Dict[str, List[DocumentChunk]]
    ) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        doc_ids = []
        question_objs = list()
        collection: DataObject = self.get_collection(collection_name)
        if collection is None:
            raise ValueError(f"Collection {collection_name} does not exist")

        with collection.batch.dynamic():
            for doc_id, doc_chunks in chunks.items():
                logging.debug(
                    f"Upserting {doc_id} with {
                        len(doc_chunks)} chunks")
                for doc_chunk in doc_chunks:
                    # generate a unique id for weaviate to store each chunk
                    doc_uuid = generate_uuid5(doc_chunk, collection_name)
                    question_objs.append(
                        wvc.data.DataObject(
                            properties={
                                "chunk_id": doc_chunk.chunk_id,
                                "document_id": doc_id,
                                "text": doc_chunk.text,
                                "source": (
                                    doc_chunk.metadata.source.value
                                    if doc_chunk.metadata and doc_chunk.metadata.source
                                    else ""
                                ),
                                "source_id": (
                                    doc_chunk.metadata.source_id
                                    if doc_chunk.metadata
                                    and doc_chunk.metadata.source_id
                                    else ""
                                ),
                                "url": (
                                    doc_chunk.metadata.url
                                    if doc_chunk.metadata and doc_chunk.metadata.url
                                    else ""
                                ),
                                "created_at": (
                                    doc_chunk.metadata.created_at
                                    if doc_chunk.metadata
                                    and doc_chunk.metadata.created_at
                                    else None
                                ),
                                "author": (
                                    doc_chunk.metadata.author
                                    if doc_chunk.metadata and doc_chunk.metadata.author
                                    else None
                                ),
                            },
                            uuid=doc_uuid,
                            vector=doc_chunk.vectors,
                        )
                    )

                doc_ids.append(doc_id)
            self.get_collection(
                collection_name).data.insert_many(question_objs)
        return doc_ids

    def get_collection(self, name: str) -> DataObject:
        if self.client and self.client.collections.exists(name):
            return self.client.collections.get(name)
        raise ValueError(f"Collection {name} does not exist")

    def create_collection(self, name: str) -> None:
        if self.client and self.client.collections.exists(name):
            logging.debug(f"Index {name} already exists")
            return
        else:
            try:
                if self.client:
                    self.collection = self.client.collections.create(
                        name=name,
                        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
                        properties=[
                            Property(name="document_id", data_type=DataType.TEXT),
                            Property(name="chunk_id", data_type=DataType.TEXT),
                            Property(
                                name="text",
                                data_type=DataType.TEXT,
                                vectorize_property_name=True,
                            ),
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
                else:
                    logging.error(
                        "Failed to create index because the client is not initialized"
                    )
            except Exception as e:
                logging.error(f"Failed to create index {name}: {e}")
                raise e

    def delete_collection(self, collection_name: str) -> None:
        if self.client and self.client.collections:
            self.client.collections.delete(collection_name)
        else:
            logging.debug(f"Collection {collection_name} does not exist")

    def query(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        filter: Optional[DocumentMetadataFilter] = None,
    ) -> List[QueryResult]:
        if not self.client or not self.client.collections:
            logging.error("Check if the client and collection are initialized")
            return []

        logging.debug(f"****Query: {query.text}")

        result = self.client.collections.get(collection_name).query.near_vector(
            near_vector=query.vectors, limit=number_of_results)

        query_results: List[QueryResult] = []
        response_objects = result.objects

        for obj in response_objects:
            properties = obj.properties
            document_chunk_with_score = DocumentChunkWithScore(
                chunk_id=properties["chunk_id"],
                text=properties["text"],
                metadata=DocumentChunkMetadata(
                    source=Source(
                        properties["source"]),
                    source_id=(
                        properties["source_id"] if "source_id" in properties else ""),
                    url=properties["url"] if "url" in properties else "",
                    created_at=(
                        properties["created_at"] if "created_at" in properties else ""),
                    author=properties["author"] if "author" in properties else "",
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

    async def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        delete_id_count: Optional[int] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything in the datastore.
        Returns whether the operation was successful.
        """
        collection: Optional[DataObject] = None

        if not self.client:
            logging.error("Client not initialized or collection not found.")
            return False

        try:
            collection = self.get_collection(collection_name)
        except ValueError as e:
            logging.error(f"Failed to get collection {collection_name}: {e}")
            return False

        if delete_all:
            logging.debug(f"Deleting all vectors in index {collection_name}")
            self.client.collections.delete(collection_name)
            return True

        if ids:
            response = collection.query.fetch_objects(limit=delete_id_count)
            uuids = [object.uuid for object in response.objects]
            logging.debug(
                f"Deleting vectors from index {collection_name} with ids {ids}"
            )
            collection.data.delete_many(
                where=Filter.by_id().contains_any(uuids))
            return True

        return True

    @staticmethod
    def build_filters(filter: DocumentMetadataFilter) -> Dict[str, Any]:
        return {}

    @staticmethod
    def _is_valid_weaviate_id(candidate_id: str) -> bool:
        """
        Check if candidate_id is a valid UUID for weaviate's use

        Weaviate supports UUIDs of version 3, 4 and 5. This function checks if the candidate_id is a valid UUID of one of these versions.
        See https://weaviate.io/developers/weaviate/more-resources/faq#q-are-there-restrictions-on-uuid-formatting-do-i-have-to-adhere-to-any-standards
        for more information.
        """
        acceptable_version = [3, 4, 5]

        try:
            result = uuid.UUID(candidate_id)
            if result.version not in acceptable_version:
                return False
            else:
                return True
        except ValueError:
            return False

    def save_embeddings_to_file(
        self, embeddings: Embeddings, file_path: str, file_format: str = "json"
    ):
        """Saves embeddings to a file in the specified format.

        Args:
            embeddings: The list of embeddings to save.
            file_path: The path to the output file.
            file_format: The file format ("json" or "txt"). Defaults to "json".

        Raises:
            ValueError: If an unsupported file format is provided.
        """

        if file_format == "json":
            with open(file_path, "w") as f:
                # Convert embeddings to JSON and write
                json.dump(embeddings, f)
        elif file_format == "txt":
            with open(file_path, "w") as f:
                for embedding in embeddings:
                    f.write(
                        " ".join(map(str, embedding)) + "\n"
                    )  # Space-separated values
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

    def delete_documents(
        self, document_ids: List[str], collection_name: Optional[str] = None
    ):
        pass

    def get_document(
        self, document_id: str, collection_name: Optional[str] = None
    ) -> Optional[Document]:
        pass

    def retrieve_documents(
        self,
        query: Union[str, QueryWithEmbedding],
        collection_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[QueryResult]:
        if collection_name is None:
            collection_name = WEAVIATE_INDEX

        if isinstance(query, str):
            # Assuming you have some method to generate embeddings from text
            embeddings = get_embeddings(query)
            query_with_embedding = QueryWithEmbedding(
                text=query, vectors=embeddings)
            logging.debug(f"Query with embedding: {query_with_embedding}")
        elif isinstance(query, QueryWithEmbedding):
            query_with_embedding = query
        else:
            raise ValueError(
                "Query must be either a string or an instance of QueryWithEmbedding"
            )

        query_results = self.query(
            collection_name, query_with_embedding, number_of_results=limit
        )

        # Assuming the query method returns a list of QueryResult objects
        if not query_results:
            return [QueryResult(data=[], similarities=[], ids=[])]

        return query_results

    def print_collection(self, collection_name: str):
        collection = self.get_collection(collection_name)
        if collection is not None:
            for item in collection.iterator():
                print(item)
        else:
            print(f"Collection {collection_name} does not exist")

    async def __aenter__(self) -> "WeaviateDataStore":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        # Ensure that the client is closed properly
        if self.client:
            self.client.close()


async def main():
    store = WeaviateDataStore()
    print(store)
    store.delete_collection(WEAVIATE_INDEX)
    store.create_collection(WEAVIATE_INDEX)
    print("Collection created", store.get_collection(WEAVIATE_INDEX))
    await store.add_documents(
        WEAVIATE_INDEX,
        [
            DocumentChunk(
                chunk_id="1",
                text="Hello world",
                vectors=[0.1, 0.2, 0.3],
                metadata=DocumentChunkMetadata(
                    source=Source.WEBSITE,
                ),
            ),
            DocumentChunk(
                chunk_id="2",
                text="This is different",
                vectors=[4, 4, 6],
                metadata=DocumentChunkMetadata(
                    source=Source.WEBSITE,
                ),
            ),
            DocumentChunk(
                chunk_id="3",
                text="A THIRD STATEMENT",
                vectors=[6, 7, 6],
                metadata=DocumentChunkMetadata(
                    source=Source.WEBSITE,
                ),
            ),
        ],
    )
    store.print_collection(WEAVIATE_INDEX)
    store.query(
        WEAVIATE_INDEX,
        QueryWithEmbedding(
            text="world",
            vectors=[
                0.1,
                0.2,
                0.3]))
    store.delete_collection(WEAVIATE_INDEX)


if __name__ == "__main__":
    asyncio.run(main())
