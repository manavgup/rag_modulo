import logging
from abc import ABC, abstractmethod
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rag_solution.data_ingestion.ingestion import DocumentStore
from vectordbs.data_types import Document, DocumentChunk, QueryResult, VectorQuery

logger = logging.getLogger(__name__)


class BaseRetriever(ABC):
    @abstractmethod
    def retrieve(self, collection_name: str, query: VectorQuery) -> list[QueryResult]:
        """
        Retrieve relevant documents based on the query.

        Args:
            collection_name (str): The name of the collection to retrieve from.
            query (VectorQuery): The query object containing search parameters.

        Returns:
            List[QueryResult]: A list of retrieved documents with their relevance scores.
        """


class VectorRetriever(BaseRetriever):
    def __init__(self, document_store: DocumentStore):
        """
        Initialize the VectorRetriever. In our implementation this just calls the vector database.

        Args:
            document_store (DocumentStore): The document store to use for retrieval.
        """
        self.document_store = document_store

    def retrieve(self, collection_name: str, query: VectorQuery) -> list[QueryResult]:
        """
        Retrieve relevant documents based on the query using vector similarity.

        Args:
            collection_name (str): The name of the collection to retrieve from.
            query (VectorQuery): The query object containing search parameters.

        Returns:
            List[QueryResult]: A list of retrieved documents with their relevance scores.
        """
        try:
            results: list[QueryResult] = self.document_store.vector_store.retrieve_documents(
                query.text, collection_name, query.number_of_results
            )
            logger.info(f"Received {len(results)} documents for query: {query.text}")
            return results
        except ValueError as e:
            logger.warning(f"Vector retrieval failed: {e}")
            return []


class KeywordRetriever(BaseRetriever):
    def __init__(self, document_store: DocumentStore):
        """
        Initialize the KeywordRetriever.

        Args:
            document_store (DocumentStore): The document store to use for retrieval.
        """
        self.document_store = document_store
        self.vectorizer = TfidfVectorizer()
        self.tfidf_matrix: Any = None
        self.documents: list[DocumentChunk] | None = None

    def _update_tfidf(self) -> None:
        """
        Update the TF-IDF matrix with the current set of documents.
        """
        # Get documents and extract text from chunks
        docs = self.document_store.get_documents()
        self.documents = []
        texts = []
        for doc in docs:
            for chunk in doc.chunks:
                self.documents.append(chunk)
                texts.append(chunk.text)
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)

    def retrieve(self, collection_name: str, query: VectorQuery) -> list[QueryResult]:  # noqa: ARG002
        """
        Retrieve relevant documents based on the query using keyword matching.

        Args:
            collection_name (str): The name of the collection to retrieve from.
            query (VectorQuery): The query object containing search parameters.

        Returns:
            List[QueryResult]: A list of retrieved documents with their relevance scores.
        """
        try:
            if self.tfidf_matrix is None:
                self._update_tfidf()

            if not self.documents:
                logger.warning("No documents available for retrieval")
                return []

            try:
                query_vec = self.vectorizer.transform([query.text])
                similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
                top_k_indices = similarities.argsort()[-query.number_of_results :][::-1]

                # At this point self.documents is guaranteed to be a list due to the check above
                documents = self.documents  # type: ignore[misc]  # We know it's not None here
                results = [QueryResult(chunk=documents[i], score=float(similarities[i]), embeddings=[]) for i in top_k_indices]
            except ValueError as e:
                logger.warning(f"TF-IDF vectorization failed: {e}")
                return []
            logger.info(f"Retrieved {len(results)} documents for query: {query}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving documents for query '{query}': {e}")
            return []


class HybridRetriever(BaseRetriever):
    def __init__(self, document_store: DocumentStore, vector_weight: float = 0.7):
        """
        Initialize the HybridRetriever.

        Args:
            document_store (DocumentStore): The document store to use for retrieval.
            vector_weight (float): The weight to give to vector-based retrieval results.
        """
        self.vector_retriever = VectorRetriever(document_store)
        self.keyword_retriever = KeywordRetriever(document_store)
        self.vector_weight = vector_weight

    def retrieve(self, collection_name: str, query: VectorQuery) -> list[QueryResult]:
        """
        Retrieve relevant documents using both vector-based and keyword-based methods.

        Args:
            collection_name (str): The name of the collection to retrieve from.
            query (VectorQuery): The query object containing search parameters.

        Returns:
            List[QueryResult]: A list of retrieved documents with their relevance scores.
        """
        try:
            # Get results from both retrievers
            vector_results = self.vector_retriever.retrieve(collection_name, query)
            keyword_results = self.keyword_retriever.retrieve(collection_name, query)

            # If both retrievers return empty results, return early
            if not vector_results and not keyword_results:
                logger.warning("No results from either retriever")
                return []

            # Combine and re-rank results
            combined_results: dict[str, QueryResult] = {}
            for result in vector_results + keyword_results:
                if result.chunk.chunk_id in combined_results:
                    combined_results[result.chunk.chunk_id].score += self.vector_weight * result.score
                else:
                    combined_results[result.chunk.chunk_id] = result
                    combined_results[result.chunk.chunk_id].score *= self.vector_weight

            ranked_results = sorted(combined_results.values(), key=lambda x: x.score, reverse=True)
            logger.info(f"Retrieved {len(ranked_results)} documents for query: {query}")
            return ranked_results[: query.number_of_results]
        except Exception as e:
            logger.error(f"Error in hybrid retrieval for query '{query}': {e}")
            return []


# Example usage
if __name__ == "__main__":
    from vectordbs.factory import get_datastore

    from .factories import RetrieverFactory

    # Initialize vector store and documents
    vector_store = get_datastore("milvus")  # Or any other supported vector store
    document_store = DocumentStore(vector_store, "test_collection")
    config = {"type": "hybrid", "vector_weight": 0.7}
    retriever = RetrieverFactory.create_retriever(config, document_store)

    # Simulate document ingestion
    documents = [
        Document(
            name="relativity",
            document_id="1",
            chunks=[DocumentChunk(chunk_id="1_1", text="The theory of relativity was developed by Albert Einstein.")]
        ),
        Document(
            name="quantum",
            document_id="2",
            chunks=[DocumentChunk(chunk_id="2_1", text="Quantum mechanics describes the behavior of matter and energy at the atomic scale.")]
        ),
        Document(
            name="bigbang",
            document_id="3",
            chunks=[DocumentChunk(chunk_id="3_1", text="The Big Bang theory explains the origin of the universe.")]
        ),
    ]
    # Note: DocumentStore doesn't have add_documents method in this implementation
    # This is just example code

    # Create a vector query
    query = VectorQuery(text="Who developed the theory of relativity?", number_of_results=2)
    results = retriever.retrieve("test_collection", query)

    for result in results:
        print(f"ID: {result.chunk.chunk_id}, Score: {result.score}, Content: {result.chunk.text[:100]}...")
