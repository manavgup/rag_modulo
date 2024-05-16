import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List
from weaviate_store import WeaviateDataStore
from data_types import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    QueryWithEmbedding,
    Source,
    QueryResult,
    DocumentChunkWithScore,
)


class TestWeaviateDataStore(unittest.TestCase):
    def setUp(self) -> None:
        self.weaviate_store = WeaviateDataStore()
    
    @patch("weaviate.connect_to_custom")
    def test_init(self, mock_connect):
        weaviate_store = WeaviateDataStore()
        mock_connect.assert_called_once()

    @patch.object(WeaviateDataStore, "_upsert", new_callable=AsyncMock)
    async def test_add_documents(self, mock_upsert):
        mock_upsert.return_value = ["doc1", "doc2"]
        documents = [
            DocumentChunk(
                document_id="chunk1",
                text="This is a test chunk",
                vector=[0.1, 0.2, 0.3],
                metadata=DocumentChunkMetadata(
                    document_id="doc1",
                    source=Source.WEBSITE,
                    source_id="source1",
                    url="https://example.com",
                    created_at="2023-04-01",
                    author="John Doe",
                ),
            ),
            DocumentChunk(
                document_id="chunk2",
                text="This is another test chunk",
                vector=[0.4, 0.5, 0.6],
                metadata=DocumentChunkMetadata(
                    document_id="doc2",
                    source=Source.PDF,
                    source_id="source2",
                    url="https://example.org",
                    created_at="2023-04-02",
                    author="Jane Doe",
                ),
            ),
        ]
        weaviate_store = WeaviateDataStore()
        doc_ids = await weaviate_store.add_documents(documents)
        mock_upsert.assert_awaited_once()
        self.assertEqual(doc_ids, ["doc1", "doc2"])

    @patch.object(WeaviateDataStore, "_upsert", new_callable=AsyncMock)
    async def test_add(self, mock_upsert):
        mock_upsert.return_value = ["doc1", "doc2"]
        data = [
            DocumentChunk(
                document_id="chunk1",
                text="This is a test chunk",
                vector=[0.1, 0.2, 0.3],
                metadata=DocumentChunkMetadata(
                    document_id="doc1",
                    source=Source.WEBSITE,
                    source_id="source1",
                    url="https://example.com",
                    created_at="2023-04-01",
                    author="John Doe",
                ),
            ),
            DocumentChunk(
                document_id="chunk2",
                text="This is another test chunk",
                vector=[0.4, 0.5, 0.6],
                metadata=DocumentChunkMetadata(
                    document_id="doc2",
                    source=Source.PDF,
                    source_id="source2",
                    url="https://example.org",
                    created_at="2023-04-02",
                    author="Jane Doe",
                ),
            ),
        ]
        weaviate_store = WeaviateDataStore()
        doc_ids = await weaviate_store.add(data)
        mock_upsert.assert_awaited_once()
        self.assertEqual(doc_ids, ["doc1", "doc2"])

    @patch.object(WeaviateDataStore, "client")
    def test_create_collection(self, mock_client):
        mock_client.collections.contains.return_value = False
        mock_client.collections.create.return_value = True
        weaviate_store = WeaviateDataStore()
        weaviate_store.create_collection("test_collection")
        mock_client.collections.contains.assert_called_once_with("DocumentChunk")
        mock_client.collections.create.assert_called_once()

    @patch.object(WeaviateDataStore, "client")
    def test_delete_collection(self, mock_client):
        weaviate_store = WeaviateDataStore()
        weaviate_store.delete_collection("test_collection")
        mock_client.collections.delete.assert_called_once_with("DocumentChunk")

    @patch.object(WeaviateDataStore, "client")
    def test_query(self, mock_client):
        mock_result = MagicMock()
        mock_client.query.get.return_value = mock_result
        mock_result.with_hybrid.return_value = mock_result
        mock_result.with_limit.return_value = mock_result
        mock_result.with_additional.return_value = mock_result
        mock_result.do.return_value = {
            "data": {
                "Get": {
                    "DocumentChunk": [
                        {
                            "chunk_id": "chunk1",
                            "text": "This is a test chunk",
                            "_additional": {
                                "vector": [0.1, 0.2, 0.3],
                                "score": 0.9,
                            },
                            "document_id": "doc1",
                            "source": "website",
                            "source_id": "source1",
                            "url": "https://example.com",
                            "created_at": "2023-04-01",
                            "author": "John Doe",
                        }
                    ]
                }
            }
        }

        queries = [
            QueryWithEmbedding(
                query="test query",
                embedding=[0.1, 0.2, 0.3],
                filter=DocumentMetadataFilter(source=Source.WEBSITE),
                top_k=10,
            )
        ]
        expected_result = [
            QueryResult(
                query="test query",
                results=[
                    DocumentChunkWithScore(
                        id="chunk1",
                        text="This is a test chunk",
                        embedding=[0.1, 0.2, 0.3],
                        score=0.9,
                        metadata=DocumentChunkMetadata(
                            document_id="doc1",
                            source=Source.WEBSITE,
                            source_id="source1",
                            url="https://example.com",
                            created_at="2023-04-01",
                            author="John Doe",
                        ),
                    )
                ],
            )
        ]

        weaviate_store = WeaviateDataStore()
        results = weaviate_store.query(queries)
        self.assertEqual(results, expected_result)

    @patch.object(WeaviateDataStore, "client")
    def test_delete(self, mock_client):
        mock_batch = MagicMock()
        mock_client.batch.delete_objects.return_value = {
            "results": {"successful": True}
        }
        mock_client.schema.delete_all.return_value = None

        weaviate_store = WeaviateDataStore()

        # Test delete by IDs
        ids = ["doc1", "doc2"]
        result = weaviate_store.delete(ids=ids)
        self.assertTrue(result)
        mock_client.batch.delete_objects.assert_called_once()

        # Test delete by filter
        mock_client.batch.delete_objects.reset_mock()
        filter_ = DocumentMetadataFilter(field='test_source', start_date='2022-01-01', end_date='2022-12-31')
        result = weaviate_store.delete(filter=filter_)
        self.assertTrue(result)
        mock_client.batch.delete_objects.assert_called_once()

        # Test delete all
        mock_client.batch.delete_objects.reset_mock()
        mock_client.schema.delete_all.reset_mock()
        result = weaviate_store.delete(delete_all=True)
        self.assertTrue(result)
        mock_client.schema.delete_all.assert_called_once()
        
    def test_build_filters(self):
        weaviate_store = WeaviateDataStore()

        # Test filter with source
        filter_ = DocumentMetadataFilter(source=Source.WEBSITE)
        expected_filter = {
            "operator": "And",
            "operands": [
                {
                    "path": ["source"],
                    "operator": "Equal",
                    "valueString": "website",
                }
            ],
        }
        built_filter = weaviate_store.build_filters(filter_)
        self.assertEqual(built_filter, expected_filter)

        # Test filter with start_date and end_date
        filter_ = DocumentMetadataFilter(
            start_date="2023-04-01", end_date="2023-04-30"
        )
        expected_filter = {
            "operator": "And",
            "operands": [
                {
                    "path": ["created_at"],
                    "operator": "GreaterThanEqual",
                    "valueDate": "2023-04-01",
                },
                {
                    "path": ["created_at"],
                    "operator": "LessThanEqual",
                    "valueDate": "2023-04-30",
                },
            ],
        }
        built_filter = weaviate_store.build_filters(filter_)
        self.assertEqual(built_filter, expected_filter)

        # Test filter with multiple conditions
        filter_ = DocumentMetadataFilter(
            source=Source.PDF, author="Jane Doe", start_date="2023-04-01"
        )
        expected_filter = {
            "operator": "And",
            "operands": [
                {
                    "path": ["source"],
                    "operator": "Equal",
                    "valueString": "pdf",
                },
                {
                    "path": ["author"],
                    "operator": "Equal",
                    "valueString": "Jane Doe",
                },
                {
                    "path": ["created_at"],
                    "operator": "GreaterThanEqual",
                    "valueDate": "2023-04-01",
                },
            ],
        }
        built_filter = weaviate_store.build_filters(filter_)
        self.assertEqual(built_filter, expected_filter)

def test_is_valid_weaviate_id(self):
    weaviate_store = WeaviateDataStore()

    # Test valid UUIDs
    valid_uuids = [
        "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",  # UUID version 4
        "6ba7b810-9dad-3203-0d92-c06861225dd8",  # UUID version 3
        "f3a54b36-714a-5377-8ac8-948bb7d55c2f",  # UUID version 5
    ]
    for uuid_str in valid_uuids:
        self.assertTrue(weaviate_store._is_valid_weaviate_id(uuid_str))

    # Test invalid UUIDs
    invalid_uuids = [
        "invalid_uuid",
        "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12",  # UUID version 2 (not supported)
        "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a",  # Incomplete UUID
    ]
    for uuid_str in invalid_uuids:
        self.assertFalse(weaviate_store._is_valid_weaviate_id(uuid_str))

if __name__ == "main":
    unittest.main()