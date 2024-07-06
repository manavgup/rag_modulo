import os
import sys
from dotenv import load_dotenv

# Ensure the base directory is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from vectordbs.utils.watsonx import generate_text  # Import the function from watsonx

load_dotenv()


class Generator:
    def __init__(self, api_key: str = "None", model_name: str = "meta/llama3-8b-v1"):
        self.api_key = api_key or os.getenv("GENAI_KEY")
        self.model_name = model_name
        if not self.api_key:
            raise ValueError("API key for WatsonX is required")

    def generate(
        self, prompt: str, max_tokens: int = 150, temperature: float = 0.7
    ) -> str:
        return generate_text(prompt, max_tokens, temperature)


# Example usage
if __name__ == "__main__":
    generator = Generator()
    prompt = "Explain the theory of relativity in simple terms."
    response = generator.generate(prompt)
    print(response)
