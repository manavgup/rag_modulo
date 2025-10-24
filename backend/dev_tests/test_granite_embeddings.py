#!/usr/bin/env python3
"""Test IBM Granite embedding models for token limits."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import Embeddings

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")


def test_granite_model(model_id: str) -> None:
    """Test a Granite embedding model."""
    print(f"\n{'=' * 80}")
    print(f"Testing: {model_id}")
    print(f"{'=' * 80}")

    # Initialize client
    credentials = Credentials(
        url=os.getenv("WATSONX_URL"),
        api_key=os.getenv("WATSONX_APIKEY"),
    )

    client = APIClient(
        credentials=credentials,
        project_id=os.getenv("WATSONX_INSTANCE_ID"),
    )

    try:
        embeddings = Embeddings(
            model_id=model_id,
            credentials=credentials,
            project_id=os.getenv("WATSONX_INSTANCE_ID"),
        )

        # Test with short text first
        short_text = "This is a test."
        print(f"\n1. Testing with short text ({len(short_text)} chars)...")
        result = embeddings.embed_documents(texts=[short_text])
        print(f"   ✅ Success! Embedding dimension: {len(result[0])}")

        # Test with progressively longer texts
        test_lengths = [100, 500, 1000, 2000, 4000, 8000, 16000, 32000]

        max_working_length = 0
        for length in test_lengths:
            test_text = "a" * length  # Simple repeated text
            try:
                print(f"\n2. Testing {length} characters...", end=" ")
                embeddings.embed_documents(texts=[test_text])
                print("✅ Success!")
                max_working_length = length
            except Exception as e:
                error_msg = str(e)
                if "Token sequence length" in error_msg or "exceeds" in error_msg:
                    print("❌ Hit token limit!")
                    print(f"   Error: {error_msg[:200]}")
                    break
                else:
                    print(f"❌ Other error: {error_msg[:200]}")
                    break

        print("\n📊 RESULTS:")
        print(f"   Max working character length: {max_working_length}")
        print(f"   Estimated max tokens: ~{max_working_length // 4}")

    except Exception as e:
        print(f"\n❌ FAILED TO INITIALIZE: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Test both Granite embedding models."""
    granite_models = [
        "ibm/granite-embedding-107m-multilingual",
        "ibm/granite-embedding-278m-multilingual",
    ]

    print("\n" + "=" * 80)
    print("🌟 TESTING IBM GRANITE EMBEDDING MODELS")
    print("=" * 80)

    for model_id in granite_models:
        test_granite_model(model_id)

    print("\n" + "=" * 80)
    print("✅ TESTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
