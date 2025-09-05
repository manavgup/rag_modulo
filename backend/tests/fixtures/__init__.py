"""Fixture package initialization.

This package contains all pytest fixtures organized by functionality.
Import all fixtures here to make them available through conftest.py
"""

from .auth import (
    admin_auth_headers,
    auth_headers,
    auth_headers_for_role,
    mock_auth_token,
    test_client,
)
from .collections import (
    base_collection,
    base_suggested_question,
    indexed_documents,
    vector_store,
)
from .data import (
    indexed_large_document,
    sample_content,
    test_documents,
    test_prompt_template_data,
    test_questions,
)
from .db import db_engine, db_session
from .files import base_file, base_file_with_content
from .llm import base_llm_parameters, get_watsonx, provider_factory
from .llm_model import base_model_input, ensure_watsonx_models
from .llm_parameter import (
    base_llm_parameters as session_base_llm_parameters,
)
from .llm_parameter import (
    custom_llm_parameters,
    custom_llm_parameters_input,
    default_llm_parameters_input,
    multiple_llm_parameters,
)
from .llm_provider import base_provider_input
from .llm_provider import get_watsonx as get_llm_provider
from .pipelines import base_pipeline_config, default_pipeline_config
from .prompt_template import (
    base_prompt_template,
    base_prompt_template_input,
    base_question_gen_template,
    base_question_gen_template_input,
    base_rag_prompt_template,
    base_rag_prompt_template_input,
)
from .services import (
    base_user,
    collection_service,
    ensure_watsonx_provider,
    file_service,
    init_providers,
    llm_model_service,
    llm_parameters_service,
    llm_provider_service,
    pipeline_service,
    prompt_template_service,
    question_service,
    search_service,
    session_db,
    session_llm_model_service,
    session_llm_parameters_service,
    session_llm_provider_service,
    session_prompt_template_service,
    session_user_service,
    team_service,
    user_collection_service,
    user_service,
    user_team_service,
)
from .teams import base_team, base_user_team, user_team
from .user import test_user

# Explicit re-exports to fix F401 warnings
__all__ = [
    "admin_auth_headers",
    "auth_headers",
    "auth_headers_for_role",
    "base_collection",
    "base_file",
    "base_file_with_content",
    "base_llm_parameters",
    "base_model_input",
    "base_pipeline_config",
    "base_prompt_template",
    "base_prompt_template_input",
    "base_provider_input",
    "base_question_gen_template",
    "base_question_gen_template_input",
    "base_rag_prompt_template",
    "base_rag_prompt_template_input",
    "base_suggested_question",
    "base_team",
    "base_user",
    "base_user_team",
    "collection_service",
    "custom_llm_parameters",
    "custom_llm_parameters_input",
    "db_engine",
    "db_session",
    "default_llm_parameters_input",
    "default_pipeline_config",
    "ensure_watsonx_models",
    "ensure_watsonx_provider",
    "file_service",
    "get_llm_provider",
    "get_watsonx",
    "indexed_documents",
    "indexed_large_document",
    "init_providers",
    "llm_model_service",
    "llm_parameters_service",
    "llm_provider_service",
    "mock_auth_token",
    "multiple_llm_parameters",
    "pipeline_service",
    "prompt_template_service",
    "provider_factory",
    "question_service",
    "sample_content",
    "search_service",
    "session_base_llm_parameters",
    "session_db",
    "session_llm_model_service",
    "session_llm_parameters_service",
    "session_llm_provider_service",
    "session_prompt_template_service",
    "session_user_service",
    "team_service",
    "test_client",
    "test_documents",
    "test_prompt_template_data",
    "test_questions",
    "test_user",
    "user_collection_service",
    "user_service",
    "user_team",
    "user_team_service",
    "vector_store",
]
