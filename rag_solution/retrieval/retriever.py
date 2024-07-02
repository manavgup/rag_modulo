# retriever.py
import sys
import os
from typing import List

# Ensure the base directory is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from vectordbs.vector_store import VectorStore
from vectordbs.data_types import QueryResult

class Retriever:
    def __init__(self, vector_store: VectorStore, top_k: int = 5, similarity_threshold: float = 0.8):
        self.vector_store = vector_store
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    async def retrieve(self, query: str) -> QueryResult:
        try:
            results = await self.vector_store.retrieve_documents_async(query, limit=self.top_k)

            # Apply similarity threshold filter
            filtered_results = [
                result for result in results.data
                if result.score >= self.similarity_threshold
            ]

            return QueryResult(data=filtered_results)
        except Exception as e:
            # Log the error
            print(f"Error retrieving documents: {e}")
            return QueryResult(data=[])

# Example usage
if __name__ == "__main__":
    import asyncio
    from vectordbs.factory import get_datastore

    async def main():
        vector_store = get_datastore('milvus')
        retriever = Retriever(vector_store)
        query = "What is the status of the Tesla project?"
        results = await retriever.retrieve(query)
        for result in results.data:
            print(result.text)

    asyncio.run(main())
