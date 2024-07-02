# generator.py
import os
import sys

from genai import Client, Credentials
from genai.schema import TextEmbeddingParameters
from genai.text.generation import CreateExecutionOptions

# Ensure the base directory is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# generator.py
from dotenv import load_dotenv

load_dotenv()

class Generator:
    def __init__(self, api_key: str = "None", model_name: str = 'meta/llama3-8b-v1'):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name
        if not self.api_key:
            raise ValueError("API key for OpenAI is required")
        self.creds = Credentials.from_env()

    def generate(self, prompt: str, max_tokens: int = 150, temperature: float = 0.7) -> str:
        try:
            response = openai.Completion.create(
                engine=self.model_name,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].text.strip()
        except Exception as e:
            print(f"Error generating text: {e}")
            return ""

# Example usage
if __name__ == "__main__":
    generator = Generator()
    prompt = "Explain the theory of relativity in simple terms."
    response = generator.generate(prompt)
    print(response)

