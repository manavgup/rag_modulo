#!/usr/bin/env python3
"""List all available WatsonX models (text generation and embeddings).

This script queries WatsonX to discover all available foundation models,
including text generation and embedding models.

Usage:
    python3 list_watsonx_models.py

Documentation:
    https://ibm.github.io/watsonx-ai-python-sdk/v1.4.1/fm_model_inference.html#TextModels
"""

import os
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient, Credentials

# Load environment variables
env_file = backend_dir.parent / ".env"
load_dotenv(env_file)


def get_watsonx_client() -> APIClient:
    """Initialize WatsonX API client from .env settings."""
    api_key = os.getenv("WATSONX_APIKEY")
    instance_id = os.getenv("WATSONX_INSTANCE_ID")
    url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key or not instance_id:
        raise ValueError("Missing WatsonX credentials. Please set WATSONX_APIKEY and WATSONX_INSTANCE_ID in .env")

    credentials = Credentials(
        url=url,
        api_key=api_key,
    )

    return APIClient(credentials=credentials, project_id=instance_id)


def list_all_models() -> None:
    """List all available WatsonX models."""
    print("🔍 Discovering WatsonX Models...")
    print(f"Instance ID: {os.getenv('WATSONX_INSTANCE_ID')}")
    print(f"URL: {os.getenv('WATSONX_URL')}\n")

    client = get_watsonx_client()

    # Get all available models
    print("=" * 80)
    print("📋 ALL AVAILABLE MODELS")
    print("=" * 80)

    try:
        # List all foundation model specs
        # Note: Using _list() as list() is not available
        models_response = client.foundation_models.get_model_specs()
        models = models_response.get("resources", [])

        # Organize by type
        text_models = []
        embedding_models = []
        other_models = []

        for model in models:
            # Handle different response structures
            model_id = model.get("model_id", model.get("id", ""))
            model_name = model.get("label", model.get("name", model_id))

            # Functions is a list of dicts with 'id' keys
            functions_raw = model.get("functions", [])
            functions = [f.get("id") if isinstance(f, dict) else f for f in functions_raw]

            if "text_embedding" in functions or "embeddings" in functions:
                embedding_models.append((model_id, model_name, model))
            elif "text_generation" in functions or "text_chat" in functions:
                text_models.append((model_id, model_name, model))
            else:
                other_models.append((model_id, model_name, model))

        # Print Embedding Models
        print("\n🎯 EMBEDDING MODELS")
        print("-" * 80)
        if embedding_models:
            for model_id, model_name, model_info in sorted(embedding_models):
                max_seq_len = model_info.get("model_limits", {}).get("max_sequence_length", "Unknown")
                print(f"\nModel ID: {model_id}")
                print(f"  Name: {model_name}")
                print(f"  Max Sequence Length: {max_seq_len} tokens")
                print(f"  Functions: {', '.join(model_info.get('functions', []))}")

                # Check if it's a Granite model
                if "granite" in model_id.lower():
                    print("  🌟 GRANITE MODEL DETECTED!")
        else:
            print("No embedding models found")

        # Print Text Generation Models
        print("\n\n📝 TEXT GENERATION MODELS")
        print("-" * 80)
        if text_models:
            granite_llms = []
            other_llms = []

            for model_id, model_name, model_info in sorted(text_models):
                if "granite" in model_id.lower():
                    granite_llms.append((model_id, model_name, model_info))
                else:
                    other_llms.append((model_id, model_name, model_info))

            # Show Granite models first
            if granite_llms:
                print("\n🌟 IBM Granite Models:")
                for model_id, model_name, model_info in granite_llms:
                    max_tokens = model_info.get("model_limits", {}).get("max_sequence_length", "Unknown")
                    print(f"  • {model_id}")
                    print(f"    Name: {model_name}")
                    print(f"    Max Tokens: {max_tokens}")

            print(f"\nOther Models: {len(other_llms)} models available")
            print("  (Use verbose mode to see all)")
        else:
            print("No text generation models found")

        # Print summary
        print("\n\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"Total Models: {len(models)}")
        print(f"  • Embedding Models: {len(embedding_models)}")
        print(f"  • Text Generation Models: {len(text_models)}")
        print(f"  • Other Models: {len(other_models)}")

        # Check for Granite embeddings specifically
        granite_embeddings = [m for m in embedding_models if "granite" in m[0].lower()]
        if granite_embeddings:
            print("\n✅ GRANITE EMBEDDING MODELS AVAILABLE!")
            for model_id, model_name, _ in granite_embeddings:
                print(f"  • {model_id}")
        else:
            print("\n❌ No Granite embedding models found in WatsonX")
            print("   Current model: ibm/slate-125m-english-rtrvr (512 token limit)")

    except Exception as e:
        print(f"\n❌ Error listing models: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    list_all_models()
