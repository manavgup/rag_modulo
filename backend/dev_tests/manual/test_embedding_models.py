#!/usr/bin/env python3
"""Test different WatsonX embedding models with a sample PDF document."""

import sys
from pathlib import Path

import pymupdf
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import Embeddings

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import get_settings


def extract_text_from_pdf(pdf_path: str, max_pages: int = 3) -> list[str]:
    """Extract text from PDF, limited to first few pages."""
    doc = pymupdf.open(pdf_path)
    texts = []

    # Extract full page text first
    full_text = ""
    for page_num in range(min(max_pages, len(doc))):
        page = doc[page_num]
        full_text += page.get_text()

    doc.close()

    # Create chunks of varying sizes to test limits
    test_sizes = [100, 200, 400, 600, 800, 1000, 1200, 1500, 2000, 2500, 3000]
    texts = []

    for size in test_sizes:
        if len(full_text) >= size:
            texts.append(full_text[:size])

    return texts


def test_embedding_model(client: APIClient, model_id: str, texts: list[str]) -> dict:
    """Test a specific embedding model with sample texts."""
    print(f"\n{'=' * 80}")
    print(f"Testing model: {model_id}")
    print(f"{'=' * 80}")

    try:
        embeddings = Embeddings(
            model_id=model_id,
            credentials=client.credentials,
            project_id=client.default_project_id,
        )

        # Test with a single short text first
        test_text = texts[0][:100]  # Very short test
        print(f"Testing with short text ({len(test_text)} chars)...")
        result = embeddings.embed_documents(texts=[test_text])
        embedding_dim = len(result[0])

        print(f"✅ SUCCESS - Embedding dimension: {embedding_dim}")

        # Now test with progressively longer texts
        successful_lengths = []
        for _i, text in enumerate(texts):  # Test all chunks
            try:
                char_len = len(text)
                embeddings.embed_documents(texts=[text])
                successful_lengths.append(char_len)
                print(f"  ✓ Size {char_len} chars - OK")
            except Exception as e:
                error_msg = str(e)
                if "Token sequence length" in error_msg or "exceeds the maximum" in error_msg:
                    print(f"  ✗ Size {char_len} chars - TOO LONG (hit token limit)")
                    break
                else:
                    print(f"  ✗ Size {char_len} chars - Error: {error_msg[:100]}")
                    break

        max_length = max(successful_lengths) if successful_lengths else 0

        return {
            "model_id": model_id,
            "status": "success",
            "embedding_dim": embedding_dim,
            "max_successful_length": max_length,
            "successful_chunks": len(successful_lengths),
        }

    except Exception as e:
        error_msg = str(e)
        print(f"❌ FAILED: {error_msg[:200]}")
        return {
            "model_id": model_id,
            "status": "failed",
            "error": error_msg[:200],
        }


def main():
    """Main function to test embedding models."""
    # Load settings
    settings = get_settings()

    # Setup WatsonX client
    credentials = Credentials(
        url=settings.wx_url,
        api_key=settings.wx_api_key,
    )

    client = APIClient(credentials=credentials, project_id=settings.wx_project_id)

    # Get available embedding models
    print("\n" + "=" * 80)
    print("AVAILABLE EMBEDDING MODELS")
    print("=" * 80)

    # Get embedding models enum
    try:
        models_dict = client.foundation_models.EmbeddingModels.show()
        print(f"\nTotal models available: {len(models_dict)}")
        print("\nModel IDs:")
        for model_id in sorted(models_dict.keys()):
            print(f"  - {model_id}")
    except Exception as e:
        print(f"Could not enumerate models: {e}")
        # Use a predefined list
        models_dict = {
            "ibm/slate-125m-english-rtrvr": {},
            "ibm/slate-30m-english-rtrvr": {},
            "intfloat/multilingual-e5-large": {},
            "sentence-transformers/all-minilm-l6-v2": {},
        }
        print("\nUsing predefined model list")

    # Extract text from PDF
    pdf_path = "/Users/mg/Downloads/2020-ibm-annual-report.pdf"
    print(f"\n{'=' * 80}")
    print(f"Extracting text from: {pdf_path}")
    print(f"{'=' * 80}")

    if not Path(pdf_path).exists():
        print(f"ERROR: PDF file not found at {pdf_path}")
        return

    texts = extract_text_from_pdf(pdf_path, max_pages=3)
    print(f"Extracted {len(texts)} text chunks from PDF")
    print(f"Sample chunk lengths: {[len(t) for t in texts[:5]]}")

    # Test embedding models
    results = []

    # Priority models to test (these support longer sequences)
    priority_models = [
        "ibm/slate-125m-english-rtrvr",  # IBM's retrieval model
        "ibm/slate-30m-english-rtrvr",  # Smaller IBM model
        "intfloat/multilingual-e5-large",  # Supports 512 tokens
        "sentence-transformers/all-minilm-l6-v2",  # Current model (for comparison)
    ]

    print(f"\n{'=' * 80}")
    print("TESTING PRIORITY MODELS")
    print(f"{'=' * 80}")

    for model_id in priority_models:
        if model_id in models_dict:
            result = test_embedding_model(client, model_id, texts)
            results.append(result)
        else:
            print(f"\n⚠️  Model not available: {model_id}")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}\n")

    successful_models = [r for r in results if r["status"] == "success"]

    if successful_models:
        # Sort by max successful length
        successful_models.sort(key=lambda x: x.get("max_successful_length", 0), reverse=True)

        print("✅ SUCCESSFUL MODELS (sorted by max chunk size supported):\n")
        for result in successful_models:
            print(f"Model: {result['model_id']}")
            print(f"  Embedding Dimension: {result['embedding_dim']}")
            print(f"  Max Chunk Length: {result['max_successful_length']} chars")
            print(f"  Successful Chunks: {result['successful_chunks']}/10")
            print()

        print("\n" + "=" * 80)
        print("RECOMMENDATION")
        print("=" * 80)
        best_model = successful_models[0]
        print(f"\n🎯 Use: {best_model['model_id']}")
        print(f"   - Supports chunks up to {best_model['max_successful_length']} characters")
        print(f"   - Embedding dimension: {best_model['embedding_dim']}")
        print("\nUpdate your .env file:")
        print(f"  EMBEDDING_MODEL={best_model['model_id']}")
        print(f"  EMBEDDING_DIM={best_model['embedding_dim']}")
        print(f"  MAX_CHUNK_SIZE={best_model['max_successful_length'] - 50}  # Leave some margin")
    else:
        print("❌ No models succeeded")

    print()


if __name__ == "__main__":
    main()
