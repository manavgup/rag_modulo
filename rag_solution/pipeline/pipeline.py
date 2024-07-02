# rag_pipeline.py
import sys
import os

# Ensure the base directory is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from rag_solution.retrieval.retriever import Retriever
from rag_solution.generation.generator import Generator

class RAGPipeline:
    def __init__(self, retriever: Retriever, generator: Generator):
        self.retriever = retriever
        self.generator = generator

    async def generate_response(self, query: str) -> str:
        retrieved_docs = await self.retriever.retrieve(query)
        combined_text = ' '.join([doc.text for doc in retrieved_docs.data])
        response = self.generator.generate(combined_text)
        return response
