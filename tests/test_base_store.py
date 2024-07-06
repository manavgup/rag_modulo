import asyncio
from datetime import datetime

import pytest

from vectordbs.data_types import (Document, DocumentChunk,
                                  DocumentChunkMetadata, QueryWithEmbedding,
                                  Source)
from vectordbs.error_types import CollectionError
from vectordbs.utils.watsonx import get_embeddings


class BaseStoreTest:
    """
    Test class for the BaseStore.
    """

    @pytest.fixture
    async def store(self):
        """
        Fixture to provide an instance of the vector store for testing.
        Subclasses must either implement this fixture or define a `store_class` attribute.
        """
        if hasattr(self, "store_class"):
            async with self.store_class() as store:
                yield store
        else:
            raise NotImplementedError(
                "Subclasses must either implement the 'store' fixture or define a 'store_class' attribute."
            )

    def create_test_documents(self):
        text1 = "Hello world"
        text2 = "Hello Jello"
        text3 = "Tic Tac Toe"
        return [
            Document(
                document_id="doc1",
                name="Doc 1",
                chunks=[
                    DocumentChunk(
                        chunk_id="1",
                        text=text1,
                        vectors=get_embeddings(text1),
                        metadata=DocumentChunkMetadata(
                            source=Source.WEBSITE,
                            created_at=datetime.now().isoformat() + "Z",
                        ),
                    )
                ],
            ),
            Document(
                document_id="doc2",
                name="Doc 2",
                chunks=[
                    DocumentChunk(
                        chunk_id="2",
                        text=text2,
                        vectors=get_embeddings(text2),
                        metadata=DocumentChunkMetadata(
                            source=Source.WEBSITE,
                            created_at=datetime.now().isoformat() + "Z",
                        ),
                    )
                ],
            ),
            Document(
                document_id="doc3",
                name="Doc 3",
                chunks=[
                    DocumentChunk(
                        chunk_id="3",
                        text=text3,
                        vectors=get_embeddings(text3),
                        metadata=DocumentChunkMetadata(
                            source=Source.WEBSITE,
                            created_at=datetime.now().isoformat() + "Z",
                        ),
                    )
                ],
            ),
        ]

    @pytest.mark.asyncio
    async def test_add_documents(self, store):
        documents = self.create_test_documents()
        async with store as s:
            result = await s.add_documents_async(s.collection_name, documents)
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_query_documents(self, store):
        async with store as s:
            documents = self.create_test_documents()
            await s.add_documents_async(s.collection_name, documents)
            await asyncio.sleep(5)  # Delay to allow Pinecone to index documents
            embeddings = get_embeddings("Hello world")
            query_result = await s.query_async(
                s.collection_name,
                QueryWithEmbedding(text="Hello world", vectors=embeddings),
            )
            assert query_result is not None
            assert len(query_result) > 0

    @pytest.mark.asyncio
    async def test_retrieve_documents_with_string_query(self, store):
        async with store as s:
            documents = self.create_test_documents()
            await s.add_documents_async(s.collection_name, documents)
            await asyncio.sleep(5)  # Delay to allow Pinecone to index documents
            query_results = await s.retrieve_documents_async(
                "Hello world", s.collection_name
            )
            assert query_results is not None
            assert len(query_results) > 0
            for query_result in query_results:
                assert query_result.data is not None
                assert len(query_result.data) > 0

    @pytest.mark.asyncio
    async def test_delete_all_documents(self, store):
        async with store as s:
            documents = self.create_test_documents()
            await s.add_documents_async(s.collection_name, documents)
            await s.delete_collection_async(s.collection_name)
            with pytest.raises(CollectionError):
                await s.retrieve_documents_async(
                    "Hello world", collection_name=s.collection_name
                )

    @pytest.mark.asyncio
    async def test_aenter_aexit(self):
        async with self.store_class() as store:
            assert isinstance(store, self.store_class)
