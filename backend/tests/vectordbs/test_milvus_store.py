import pytest
import asyncio
import json
import os
import logging
from backend.vectordbs.milvus_store import MilvusStore
from backend.vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source, QueryWithEmbedding
from backend.core.config import settings
from backend.vectordbs.utils.watsonx import get_embeddings
from backend.rag_solution.data_ingestion.ingestion import DocumentStore
from pymilvus import Collection, utility

MILVUS_COLLECTION = f"test_collection_canada_research"
TEST_PDF_PATH = "/Users/mg/Downloads/Canada_research_ecosystem_2024.pdf"
CACHE_FILE = "test_documents_cache.json"
QUERY_RESULTS_FILE = "query_results.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def milvus_store():
    store = MilvusStore(host=settings.milvus_host, port=settings.milvus_port)
    # Ensure the collection exists
    if not utility.has_collection(MILVUS_COLLECTION):
        store.create_collection(MILVUS_COLLECTION)
    yield store
    # Cleanup
    store.delete_collection(MILVUS_COLLECTION)

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

async def process_and_ingest_documents(milvus_store):
    if os.path.exists(CACHE_FILE):
        logger.info(f"Loading documents from cache file: {CACHE_FILE}")
        with open(CACHE_FILE, 'r') as f:
            cached_docs = json.load(f)
        documents = [Document.from_dict(doc) for doc in cached_docs]
    else:
        logger.info(f"Processing PDF file: {TEST_PDF_PATH}")
        document_store = DocumentStore(milvus_store, MILVUS_COLLECTION)
        try:
            documents = await document_store.load_documents([TEST_PDF_PATH])
            logger.info(f"Successfully processed {len(documents)} documents")
            with open(CACHE_FILE, 'w') as f:
                json.dump([doc.to_dict() for doc in documents], f)
            logger.info(f"Cached processed documents to {CACHE_FILE}")
        except Exception as e:
            logger.error(f"Error processing PDF file: {e}")
            raise
    
    # Add documents to the collection
    try:
        milvus_store.add_documents(MILVUS_COLLECTION, documents)
        logger.info(f"Added {len(documents)} documents to collection {MILVUS_COLLECTION}")
    except Exception as e:
        logger.error(f"Error adding documents to collection: {e}")
        raise
    
    return documents

@pytest.mark.asyncio
async def test_query(milvus_store):
    # Ensure the collection exists
    if not utility.has_collection(MILVUS_COLLECTION):
        milvus_store.create_collection(MILVUS_COLLECTION)

    # Process and ingest documents
    documents = await process_and_ingest_documents(milvus_store)
    
    # Perform query
    query_text = "funding for scientific research"
    query = QueryWithEmbedding(text=query_text, vectors=get_embeddings(query_text))
    result = milvus_store.query(MILVUS_COLLECTION, query)
    assert len(result) > 0, "Query returned no results"

    # Save query results to a file
    query_results = []
    for query_result in result:
        query_results.append({
            "similarities": query_result.similarities,
            "ids": query_result.ids,
            "data": [
                {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "score": chunk.score,
                    "metadata": {
                        "source": chunk.metadata.source.value if chunk.metadata.source else None,
                        "source_id": chunk.metadata.source_id,
                        "url": chunk.metadata.url,
                        "created_at": chunk.metadata.created_at,
                        "author": chunk.metadata.author
                    }
                }
                for chunk in query_result.data
            ]
        })

    with open(QUERY_RESULTS_FILE, 'w') as f:
        json.dump(query_results, f, indent=2)

    logger.info(f"Query results saved to {QUERY_RESULTS_FILE}")

    # Check relevance of results
    relevant_keywords = ["funding", "research", "science", "grant"]
    for query_result in result:
        for chunk in query_result.data:
            assert any(keyword in chunk.text.lower() for keyword in relevant_keywords), f"Result not relevant: {chunk.text}"


def test_create_collection(milvus_store):
    collection = milvus_store.create_collection(MILVUS_COLLECTION)
    assert isinstance(collection, Collection)
    assert utility.has_collection(MILVUS_COLLECTION)

@pytest.mark.asyncio
async def test_retrieve_documents(milvus_store):
    documents = await process_and_ingest_documents(milvus_store)
    result = milvus_store.retrieve_documents("research funding in Canada", MILVUS_COLLECTION)
    assert len(result) > 0
    assert all(isinstance(item, DocumentChunk) for item in result[0].data)

@pytest.mark.asyncio
async def test_delete_documents(milvus_store):
    documents = await process_and_ingest_documents(milvus_store)
    document_ids = [doc.document_id for doc in documents[:2]]
    result = milvus_store.delete_documents(document_ids, MILVUS_COLLECTION)
    assert result == len(document_ids)

def test_list_collections(milvus_store):
    collections = milvus_store.list_collections()
    assert MILVUS_COLLECTION in collections

@pytest.mark.asyncio
async def test_get_document(milvus_store):
    documents = await process_and_ingest_documents(milvus_store)
    doc_id = documents[0].document_id
    result = milvus_store.get_document(doc_id, MILVUS_COLLECTION)
    assert result is not None
    assert result.document_id == doc_id
    assert len(result.chunks) > 0

def test_error_handling(milvus_store):
    with pytest.raises(Exception):
        milvus_store.retrieve_documents("test", "non_existent_collection")

@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_keywords", [
    ("What are the main funding agencies for research in Canada?", ["NSERC", "SSHRC", "CIHR"]),
    ("How does Canada support international research collaboration?", ["international", "collaboration", "partnership"]),
    ("What is the role of the Canada Foundation for Innovation?", ["CFI", "infrastructure", "equipment"]),
])
async def test_relevant_document_retrieval(milvus_store, query, expected_keywords):
    documents = await process_and_ingest_documents(milvus_store)
    results = milvus_store.retrieve_documents(query, MILVUS_COLLECTION)
    assert len(results) > 0
    retrieved_text = " ".join([chunk.text for chunk in results[0].data])
    assert any(keyword.lower() in retrieved_text.lower() for keyword in expected_keywords)

@pytest.mark.asyncio
async def test_performance_milvus_store(benchmark, milvus_store):
    documents = await process_and_ingest_documents(milvus_store)
    def setup():
        return (documents[:100], MILVUS_COLLECTION)
    
    benchmark.pedantic(milvus_store.add_documents, setup=setup, iterations=5, rounds=3)

if __name__ == "__main__":
    pytest.main(["-v", "test_milvus_store.py::test_query"])
