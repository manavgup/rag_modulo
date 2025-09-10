"""Centralized test fixtures."""

# Import specific fixtures to avoid wildcard imports
from .atomic import (
    base_collection_data,
    base_llm_parameters_data,
    base_team_data,
    base_user_data,
)
from .e2e import (
    base_collection_e2e,
    base_team_e2e,
    base_user_e2e,
    full_database_setup,
    full_llm_provider_setup,
    full_vector_store_setup,
)
from .integration import (
    complex_test_pdf_path,
    test_database_url,
    test_milvus_config,
    test_minio_config,
)
from .unit import (
    mock_collection_service,
    mock_jwt_verification,
    mock_team_service,
    mock_user_service,
    mock_watsonx_imports,
)

__all__ = [
    # Atomic fixtures
    "base_collection_data",
    "base_llm_parameters_data",
    "base_team_data",
    "base_user_data",
    # Unit fixtures
    "mock_collection_service",
    "mock_jwt_verification",
    "mock_team_service",
    "mock_user_service",
    "mock_watsonx_imports",
    # Integration fixtures
    "complex_test_pdf_path",
    "test_database_url",
    "test_milvus_config",
    "test_minio_config",
    # E2E fixtures
    "base_collection_e2e",
    "base_team_e2e",
    "base_user_e2e",
    "full_database_setup",
    "full_llm_provider_setup",
    "full_vector_store_setup",
]
