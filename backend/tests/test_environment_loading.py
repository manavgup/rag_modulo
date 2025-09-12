"""Test that environment variables are loaded correctly."""

import os
import pytest


@pytest.mark.unit
def test_env_vars_loaded():
    """Verify critical environment variables are loaded from .env file."""
    # These should be loaded from ../.env via pytest-env
    assert os.getenv("VECTOR_DB") == "milvus", f"VECTOR_DB={os.getenv('VECTOR_DB')}"
    assert os.getenv("MILVUS_HOST") == "localhost", f"MILVUS_HOST={os.getenv('MILVUS_HOST')} (should be overridden to localhost)"
    assert os.getenv("MILVUS_PORT") == "19530", f"MILVUS_PORT={os.getenv('MILVUS_PORT')}"

    # WatsonX credentials should be loaded
    assert os.getenv("WATSONX_URL") is not None, "WATSONX_URL not loaded"
    assert os.getenv("WATSONX_INSTANCE_ID") is not None, "WATSONX_INSTANCE_ID not loaded"

    print("\n✅ Environment variables loaded correctly:")
    print(f"  VECTOR_DB: {os.getenv('VECTOR_DB')}")
    print(f"  MILVUS_HOST: {os.getenv('MILVUS_HOST')}")
    print(f"  MILVUS_PORT: {os.getenv('MILVUS_PORT')}")
    print(f"  WATSONX_URL: {os.getenv('WATSONX_URL')[:30]}...")
