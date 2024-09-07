import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dotenv import load_dotenv
from backend.vectordbs.utils.watsonx import generate_text
from backend.rag_solution.pipeline.pipeline import pipeline
load_dotenv()

class BaseGenerator(ABC):
    @abstractmethod
    def generate(self, query: str, documents: List[Dict[str, Any]]) -> str:
        pass

class HuggingFaceGenerator(BaseGenerator):
    def __init__(self, model_name: str = "gpt2"):
        self.generator = pipeline("text-generation", model=model_name)

    def generate(self, query: str, documents: List[Dict[str, Any]]) -> str:
        context = " ".join([doc['content'] for doc in documents])
        prompt = f"Query: {query}\nContext: {context}\nAnswer:"
        response = self.generator(prompt, max_length=150, num_return_sequences=1)[0]['generated_text']
        return response.split("Answer:")[1].strip()

class WatsonxGenerator(BaseGenerator):
    def generate(self, query: str, documents: List[Dict[str, Any]]) -> str:
        context = " ".join([doc['content'] for doc in documents])
        prompt = f"Query: {query}\nContext: {context}\nAnswer:"
        response = generate_text(prompt)
        return response

class Generator:
    def __init__(self, config: Dict[str, Any]):
        generator_type = config.get('type', 'huggingface')
        if generator_type == 'huggingface':
            model_name = config.get('model_name', 'gpt2')
            self.generator = HuggingFaceGenerator(model_name)
        elif generator_type == 'watsonx':
            self.generator = WatsonxGenerator()
        else:
            raise ValueError(f"Unsupported generator type: {generator_type}")

    def generate(self, query: str, documents: List[Dict[str, Any]]) -> str:
        return self.generator.generate(query, documents)

# Example usage
if __name__ == "__main__":
    config = {'type': 'huggingface', 'model_name': 'gpt2'}
    generator = Generator(config)
    query = "Explain the theory of relativity in simple terms."
    documents = [{"content": "Einstein's theory of relativity deals with space and time."}]
    response = generator.generate(query, documents)
    print(response)
