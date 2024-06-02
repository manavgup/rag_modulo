from typing import List, Optional, Union, Dict, Any
from vectordbs.data_types import (
    Document,
    DocumentChunk,
    DocumentMetadataFilter,
    QueryWithEmbedding,
    QueryResult,
    Source,
    DocumentChunkMetadata,
)
from vectordbs.vector_store import VectorStore
import logging
from pinecone import Pinecone, ServerlessSpec, QueryResponse
from dotenv import load_dotenv
from vectordbs.utils.watsonx import get_embeddings
import os

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "your-pinecone-api-key")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

logging.basicConfig(level=logging.INFO)


class PineconeStore(VectorStore):
    def __init__(self) -> None:
        try:
            self.client = Pinecone(api_key=PINECONE_API_KEY)
        except Exception as e:
            logging.error(f"Failed to initialize Pinecone client: {e}")
            self.client = None

    def create_collection(
        self,
        collection_name: str,
        embedding_model: str = "sentence-transformers/all-minilm-l6-v2",
    ) -> None:
        try:
            if collection_name in self.client.list_indexes().names():
                print("*** Index already exists", collection_name)
                self.index = self.client.Index(collection_name)
            elif collection_name not in self.client.list_indexes().names():
                self.client.create_index(
                    name=collection_name,
                    dimension=384,
                    metric="cosine",
                    spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
                )
                self.index = self.client.Index(
                    collection_name
                )  # store the index object for later use
        except Exception as e:
            logging.error(f"Failed to create Pinecone index: {e}")
            self.index = None

    def add_documents(
        self, collection_name: str, documents: List[Document]
    ) -> List[str]:
        if self.client is None:
            logging.error("Pinecone client is not initialized")
            return []
        if collection_name not in self.client.list_indexes().names():
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
                        "document_id": chunk.document_id,
                        "source": chunk.metadata.source.value if chunk.metadata else "",
                        "source_id": chunk.metadata.source_id if chunk.metadata else "",
                        "url": chunk.metadata.url if chunk.metadata else "",
                        "created_at": (
                            chunk.metadata.created_at if chunk.metadata else ""
                        ),
                        "author": chunk.metadata.author if chunk.metadata else "",
                    },
                }
                vectors.append(vector)
                document_ids.append(chunk.chunk_id)
        self.index.upsert(vectors=vectors)
        logging.info(f"Successfully added documents to index '{collection_name}'")
        return document_ids

    def retrieve_documents(
        self,
        query: Union[str, QueryWithEmbedding],
        collection_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[QueryResult]:
        if isinstance(query, str):
            query_embeddings = get_embeddings(query)
            if not query_embeddings:
                raise ValueError("Failed to generate embeddings for the query string.")
            query = QueryWithEmbedding(text=query, vectors=query_embeddings)

        collection_name = collection_name or self.index_name
        return self.query(collection_name, query, number_of_results=limit)

    def query(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        filter: Optional[DocumentMetadataFilter] = None,
    ) -> List[QueryResult]:
        response = self.index.query(
            vector=query.vectors,
            top_k=number_of_results,
            include_metadata=True,
            include_values=True,
        )
        return self._process_search_results(response)

    def delete_collection(self, collection_name: str) -> None:
        try:
            self.client.Index(collection_name).delete(collection_name)
            self.index = None
        except Exception as e:
            logging.error(f"Failed to delete Pinecone index: {e}")

    def delete_documents(
        self, document_ids: List[str], collection_name: Optional[str] = None
    ) -> int:
        collection_name = collection_name or self.index_name

        if self.index is None:
            self.index = self.client.Index(collection_name)

        if collection_name not in self.client.list_indexes().names():
            logging.error(f"Pinecone index '{collection_name}' does not exist")
            return 0

        if not document_ids:
            logging.error("No document IDs provided for deletion")
            return 0

        try:
            self.index.delete(ids=document_ids)
            deleted_count = len(
                document_ids
            )  # Assuming deletion attempt on all ids passed
            logging.info(f"Deleted documents from index '{collection_name}'")
            return deleted_count
        except Exception as e:
            logging.error(f"Failed to delete documents from Pinecone index: {e}")
            return 0

    def _convert_to_chunk(self, data: Dict) -> DocumentChunk:
        return DocumentChunk(
            chunk_id=data["id"],
            text=data["metadata"]["text"],
            vectors=data["values"],
            metadata=DocumentChunkMetadata(
                source=(
                    Source(data["metadata"]["source"])
                    if data["metadata"]["source"]
                    else Source.OTHER
                ),
                source_id=data["metadata"]["source_id"],
                url=data["metadata"]["url"],
                created_at=data["metadata"]["created_at"],
                author=data["metadata"]["author"],
            ),
            document_id=data["metadata"]["document_id"],
        )

    def _process_search_results(self, response: Dict) -> List[QueryResult]:
        results = []
        # Adjust the structure to navigate through 'results' to 'matches'
        for match in response["matches"]:
            chunk = self._convert_to_chunk(match)
            results.append(
                QueryResult(
                    data=[chunk], similarities=[match["score"]], ids=[match["id"]]
                )
            )
        return results

    def _build_filters(
        self, filter: Optional[DocumentMetadataFilter]
    ) -> Dict[str, Any]:
        # Pinecone does not natively support filters in the same way as Elasticsearch, but you can implement custom filtering here if needed
        raise NotImplementedError("Filter building is not supported in PineconeStore.")

    async def __aenter__(self) -> "PineconeStore":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        pass
