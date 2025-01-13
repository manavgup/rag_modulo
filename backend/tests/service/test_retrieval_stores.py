"""Tests for retrieval service with different vector stores."""
import pytest
from typing import Dict, Any, List
import numpy as np

from rag_solution.retrieval.retriever import Retriever
from rag_solution.services.search_service import SearchService
from vectordbs.milvus_store import MilvusStore
from vectordbs.chroma_store import ChromaStore
from vectordbs.elasticsearch_store import ElasticsearchStore
from vectordbs.vector_store import VectorStore

@pytest.mark.retrieval
class TestRetrievalStores:
    """Test retrieval service with different vector stores."""

    @pytest.fixture
    def search_service(self, db_session) -> SearchService:
        """Create search service fixture."""
        return SearchService(db_session)

    @pytest.fixture
    def test_documents(self) -> List[Dict[str, Any]]:
        """Test documents for indexing."""
        return [
            {
                "id": "1",
                "content": "Python is a high-level programming language.",
                "metadata": {"source": "test.txt", "page": 1}
            },
            {
                "id": "2",
                "content": "Python was created by Guido van Rossum.",
                "metadata": {"source": "test.txt", "page": 1}
            },
            {
                "id": "3",
                "content": "Python supports multiple programming paradigms.",
                "metadata": {"source": "test.txt", "page": 2}
            }
        ]

    @pytest.fixture
    def test_embeddings(self) -> List[List[float]]:
        """Test embeddings for documents."""
        # Simulate 384-dimensional embeddings
        return [
            list(np.random.rand(384)) for _ in range(3)
        ]

    @pytest.mark.integration
    async def test_milvus_retrieval(
        self,
        search_service: SearchService,
        test_documents: List[Dict[str, Any]],
        test_embeddings: List[List[float]]
    ):
        """Test retrieval with Milvus store."""
        # Initialize Milvus store
        store = MilvusStore(
            collection_name="test_collection",
            dimension=384,
            host="localhost",
            port=19530
        )

        # Index documents
        await store.add_documents(
            documents=test_documents,
            embeddings=test_embeddings
        )

        # Search with test query
        query = "Who created Python?"
        query_embedding = list(np.random.rand(384))
        results = await store.search(
            query_embedding=query_embedding,
            limit=2
        )

        # Verify results
        assert len(results) == 2
        assert any("Guido van Rossum" in doc["content"] for doc in results)
        assert all("source" in doc["metadata"] for doc in results)

    @pytest.mark.integration
    async def test_chroma_retrieval(
        self,
        search_service: SearchService,
        test_documents: List[Dict[str, Any]],
        test_embeddings: List[List[float]]
    ):
        """Test retrieval with Chroma store."""
        # Initialize Chroma store
        store = ChromaStore(
            collection_name="test_collection",
            persist_directory="./data/chroma"
        )

        # Index documents
        await store.add_documents(
            documents=test_documents,
            embeddings=test_embeddings
        )

        # Search with test query
        query = "What is Python?"
        query_embedding = list(np.random.rand(384))
        results = await store.search(
            query_embedding=query_embedding,
            limit=2
        )

        # Verify results
        assert len(results) == 2
        assert any("high-level programming language" in doc["content"] for doc in results)
        assert all("source" in doc["metadata"] for doc in results)

    @pytest.mark.integration
    async def test_elasticsearch_retrieval(
        self,
        search_service: SearchService,
        test_documents: List[Dict[str, Any]],
        test_embeddings: List[List[float]]
    ):
        """Test retrieval with Elasticsearch store."""
        # Initialize Elasticsearch store
        store = ElasticsearchStore(
            index_name="test_index",
            hosts=["http://localhost:9200"]
        )

        # Index documents
        await store.add_documents(
            documents=test_documents,
            embeddings=test_embeddings
        )

        # Search with test query
        query = "What paradigms does Python support?"
        query_embedding = list(np.random.rand(384))
        results = await store.search(
            query_embedding=query_embedding,
            limit=2
        )

        # Verify results
        assert len(results) == 2
        assert any("programming paradigms" in doc["content"] for doc in results)
        assert all("source" in doc["metadata"] for doc in results)

    @pytest.mark.performance
    async def test_retrieval_performance(
        self,
        search_service: SearchService,
        test_documents: List[Dict[str, Any]],
        test_embeddings: List[List[float]]
    ):
        """Test performance across different vector stores."""
        import time

        stores: Dict[str, VectorStore] = {
            "milvus": MilvusStore(
                collection_name="test_collection",
                dimension=384,
                host="localhost",
                port=19530
            ),
            "chroma": ChromaStore(
                collection_name="test_collection",
                persist_directory="./data/chroma"
            ),
            "elasticsearch": ElasticsearchStore(
                index_name="test_index",
                hosts=["http://localhost:9200"]
            )
        }

        results = {}
        query_embedding = list(np.random.rand(384))

        for name, store in stores.items():
            # Index documents
            index_start = time.time()
            await store.add_documents(
                documents=test_documents,
                embeddings=test_embeddings
            )
            index_time = time.time() - index_start

            # Measure search performance
            search_times = []
            for _ in range(10):
                search_start = time.time()
                await store.search(
                    query_embedding=query_embedding,
                    limit=2
                )
                search_times.append(time.time() - search_start)

            results[name] = {
                "index_time": index_time,
                "avg_search_time": sum(search_times) / len(search_times),
                "min_search_time": min(search_times),
                "max_search_time": max(search_times)
            }

        # Verify performance metrics
        for store_name, metrics in results.items():
            assert metrics["index_time"] < 5.0  # Indexing should complete within 5 seconds
            assert metrics["avg_search_time"] < 1.0  # Average search should complete within 1 second
            assert metrics["max_search_time"] < 2.0  # Max search should complete within 2 seconds

    @pytest.mark.error
    async def test_retrieval_error_handling(
        self,
        search_service: SearchService,
        test_documents: List[Dict[str, Any]],
        test_embeddings: List[List[float]]
    ):
        """Test error handling for different vector stores."""
        # Test with invalid Milvus connection
        with pytest.raises(Exception) as exc:
            store = MilvusStore(
                collection_name="test_collection",
                dimension=384,
                host="invalid-host",
                port=19530
            )
            await store.add_documents(
                documents=test_documents,
                embeddings=test_embeddings
            )
            assert "connection failed" in str(exc.value).lower()

        # Test with invalid document format
        with pytest.raises(ValueError) as exc:
            store = ChromaStore(
                collection_name="test_collection",
                persist_directory="./data/chroma"
            )
            await store.add_documents(
                documents=[{"invalid": "document"}],  # Missing required fields
                embeddings=[list(np.random.rand(384))]
            )
            assert "invalid document format" in str(exc.value).lower()

        # Test with mismatched dimensions
        with pytest.raises(ValueError) as exc:
            store = ElasticsearchStore(
                index_name="test_index",
                hosts=["http://localhost:9200"]
            )
            await store.add_documents(
                documents=test_documents,
                embeddings=[list(np.random.rand(128))]  # Wrong embedding dimension
            )
            assert "dimension mismatch" in str(exc.value).lower()
