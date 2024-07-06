import logging
import os
import sys

from genai.client import Client
from genai.credentials import Credentials
from genai.schema import (TextTokenizationParameters,
                          TextTokenizationReturnOptions)
from genai.text.tokenization import CreateExecutionOptions

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import settings

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


class QueryRewriter:
    def __init__(self):
        # Initialize the WatsonX client
        credentials = Credentials(settings.genai_key, settings.api_endpoint)
        self.client = Client(credentials=credentials)
        self.model_id = settings.tokenizer
        print("model_id: ", self.model_id)

    def rewrite_query(self, query: str) -> str:
        try:
            # Perform the tokenization and retrieve the tokens
            response = next(
                self.client.text.tokenization.create(
                    model_id=self.model_id,
                    input=[query],
                    execution_options=CreateExecutionOptions(),
                    parameters=TextTokenizationParameters(
                        return_options=TextTokenizationReturnOptions(
                            tokens=True  # We want to return the tokens
                        )
                    ),
                )
            )
            tokens = response.results[0].tokens
            rewritten_query = (
                " ".join(tokens).replace(" </s>", "").strip()
            )  # Remove end-of-sentence token
            return rewritten_query
        except Exception as e:
            logger.error(f"Error rewriting query: {e}")
            return query  # Fallback to original query in case of an error


# Example usage
if __name__ == "__main__":
    rewriter = QueryRewriter()
    original_query = "How long fry pork chop?"
    rewritten_query = rewriter.rewrite_query(original_query)
    print(f"Original Query: {original_query}")
    print(f"Rewritten Query: {rewritten_query}")
