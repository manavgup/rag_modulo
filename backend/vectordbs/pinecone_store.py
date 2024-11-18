import logging
from typing import Any, Dict, List, Optional

from pinecone import Pinecone, ServerlessSpec

from core.config import settings
from vectordbs.utils.watsonx import get_embeddings

from .data_types import (Document, DocumentChunk, DocumentChunkMetadata,
                         DocumentMetadataFilter, QueryResult,
                         QueryWithEmbedding, Source)
from .error_types import CollectionError, VectorStoreError
from .vector_store import VectorStore

PINECONE_API_KEY = settings.pinecone_api_key
PINECONE_CLOUD = settings.pinecone_cloud
PINECONE_REGION = settings.pinecone_region
EMBEDDING_DIM = settings.embedding_dim

logging.basicConfig(level=logging.INFO)


class PineconeStore(VectorStore):
    def __init__(self) -> None:
        try:
            self.client = Pinecone(api_key=PINECONE_API_KEY, pool_threads=30)
            logging.info("Pinecone client initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize Pinecone client: {e}")
            self.client = None
        self.index: Optional[Any] = None

    def create_collection(self, collection_name: str, metadata: Optional[dict] = None) -> None:
        """
        Create a new Pinecone collection.

        Args:
            collection_name (str): The name of the collection to create.
            metadata: Optional metadata for the collection.
        """
        try:
            if collection_name in self.client.list_indexes():
                self.index = self.client.Index(collection_name)
                logging.info(f"Pinecone index '{collection_name}' already exists")
            else:
                self.client.create_index(
                    name=collection_name,
                    dimension=EMBEDDING_DIM,
                    metric="cosine",
                    spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
                )
                self.index = self.client.Index(collection_name)
                logging.info(f"Pinecone index '{collection_name}' created successfully")
        except Exception as e:
            logging.error(f"Failed to create Pinecone index: {e}")
            self.index = None

    def add_documents(self, collection_name: str, documents: List[Document]) -> List[str]:
        """
        Add documents to the specified Pinecone collection.

        Args:
            collection_name (str): The name of the collection to add documents to.
            documents (List[Document]): The list of documents to add.

        Returns:
            List[str]: The list of document IDs that were added.
        """
        if self.client is None:
            logging.error("Pinecone client is not initialized")
            return []
        if collection_name not in self.client.list_indexes():
            logging.error(f"Pinecone index '{collection_name}' does not exist")
            return []

        vectors = []
        document_ids = []
        for document in documents:
            for chunk in document.chunks:
                vector = {
                    "id": chunk.chunk_id,
                    "values": chunk.vectors,
                    "metadata": {
                        "text": chunk.text,
                        "document_id": document.document_id if document.document_id is not None else "",
                        "source": chunk.metadata.source.value if chunk.metadata else "",
                        "source_id": chunk.metadata.source_id if chunk.metadata else "",
                        "url": chunk.metadata.url if chunk.metadata else "",
                        "created_at": chunk.metadata.created_at if chunk.metadata else "",
                        "author": chunk.metadata.author if chunk.metadata else "",
                    },
                }
                vectors.append(vector)
                document_ids.append(chunk.chunk_id)
        self.client.Index(collection_name).upsert(vectors=vectors, async_req=False)
        logging.info(f"Successfully added documents to index '{collection_name}'")
        return document_ids

    def retrieve_documents(self, query: str, collection_name: str, number_of_results: int = 10) -> List[QueryResult]:
        """
        Retrieve documents from the specified Pinecone collection.

        Args:
            query (str): The query string.
            collection_name (str): The name of the collection to retrieve documents from.
            number_of_results (int): The number of results to return.

        Returns:
            List[QueryResult]: The list of query results.
        """
        if collection_name not in self.client.list_indexes():
            raise CollectionError(f"Collection '{collection_name}' does not exist")

        embeddings = get_embeddings(query)
        if not embeddings:
            raise VectorStoreError("Failed to generate embeddings for the query string.")
        query_embeddings = QueryWithEmbedding(text=query, vectors=embeddings)

        results = self.query(collection_name, query_embeddings, number_of_results=number_of_results)
        return results

    def query(self, collection_name: str, query: QueryWithEmbedding, number_of_results: int = 10,
              filter: Optional[DocumentMetadataFilter] = None) -> List[QueryResult]:
        """
        Query the specified Pinecone collection using an embedding.

        Args:
            collection_name (str): The name of the collection to query.
            query (QueryWithEmbedding): The query embedding.
            number_of_results (int): The number of results to return.
            filter (Optional[DocumentMetadataFilter]): Optional filter for the query.

        Returns:
            List[QueryResult]: The list of query results.
        """
        try:
            response = self.client.Index(collection_name).query(
                vector=query.vectors,
                top_k=number_of_results,  # Pinecone API uses top_k, but we maintain our consistent interface
                include_metadata=True,
                include_values=True,
            )
            return self._process_search_results(response)
        except Exception as e:
            logging.error(f"Failed to query Pinecone index '{collection_name}': {e}")
            raise CollectionError(f"Failed to query Pinecone index '{collection_name}': {e}")

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete the specified Pinecone collection.

        Args:
            collection_name (str): The name of the collection to delete.
        """
        try:
            self.client.delete_index(collection_name)
            self.index = None
            logging.info(f"Pinecone index '{collection_name}' deleted successfully")
        except Exception as e:
            logging.error(f"Failed to delete Pinecone index '{collection_name}': {e}")

    def delete_documents(self, document_ids: List[str], collection_name: str) -> int:
        """
        Delete documents from the specified Pinecone collection.

        Args:
            document_ids (List[str]): The list of document IDs to delete.
            collection_name (str): The name of the collection to delete documents from.

        Returns:
            int: The number of documents deleted.
        """
        if collection_name not in self.client.list_indexes():
            logging.error(f"Pinecone index '{collection_name}' does not exist")
            return 0

        if not document_ids:
            logging.error("No document IDs provided for deletion")
            return 0

        try:
            self.client.Index(collection_name).delete(ids=document_ids)
            logging.info(f"Deleted documents from index '{collection_name}'")
            return len(document_ids)
        except Exception as e:
            logging.error(f"Failed to delete documents from Pinecone index '{collection_name}': {e}")
            raise CollectionError(f"Failed to delete documents from Pinecone index '{collection_name}': {e}")

    def _convert_to_chunk(self, data: Dict) -> DocumentChunk:
        """
        Convert data to a DocumentChunk.

        Args:
            data (Dict): The data to convert.

        Returns:
            DocumentChunk: The converted DocumentChunk.
        """
        return DocumentChunk(
            chunk_id=data["id"],
            text=data["metadata"]["text"],
            vectors=data["values"],
            metadata=DocumentChunkMetadata(
                source=Source(data["metadata"]["source"]) if data["metadata"]["source"] else Source.OTHER,
                source_id=data["metadata"]["source_id"],
                url=data["metadata"]["url"],
                created_at=data["metadata"]["created_at"],
                author=data["metadata"]["author"],
            ),
            document_id=data["metadata"]["document_id"],
        )

    def _process_search_results(self, response: Dict) -> List[QueryResult]:
        """
        Process search results from Pinecone.

        Args:
            response (Dict): The search results to process.

        Returns:
            List[QueryResult]: The list of query results.
        """
        results = []
        for match in response["matches"]:
            chunk = self._convert_to_chunk(match)
            results.append(
                QueryResult(
                    data=[chunk], similarities=[match["score"]], ids=[match["id"]]
                )
            )
        return results

    def _build_filters(self, filter: Optional[DocumentMetadataFilter]) -> Dict[str, Any]:
        """
        Build filters for Pinecone queries.

        Args:
            filter (Optional[DocumentMetadataFilter]): The metadata filter to build.

        Returns:
            Dict[str, Any]: The built filter dictionary.
        """
        raise NotImplementedError("Filter building is not supported in PineconeStore.")
