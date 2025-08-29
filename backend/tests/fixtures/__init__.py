"""Fixture package initialization.

This package contains all pytest fixtures organized by functionality.
Import all fixtures here to make them available through conftest.py
"""

from .auth import mock_jwt_decode, mock_jwt_settings, mock_oauth_client
from .collections import base_collection, mock_collection_service, test_collection, test_collection_create, vector_store
from .data import test_documents
from .db import mock_db_session, test_db, test_session
from .files import base_file, base_file_with_content, test_file, test_file_create, uploaded_file
from .llm import base_llm_parameters, mock_llm_provider, mock_llm_response, provider_factory
from .llm_model import test_llm_model, test_llm_model_create
from .llm_parameter import test_llm_parameters, test_llm_parameters_create
from .llm_provider import test_llm_provider, test_llm_provider_create
from .pipelines import base_pipeline_config, test_pipeline, test_pipeline_create
from .prompt_template import (
    base_prompt_template,
    base_prompt_template_input,
    base_question_gen_template,
    base_question_gen_template_input,
    base_rag_prompt_template,
    base_rag_prompt_template_input,
    test_prompt_template,
    test_prompt_template_create,
)
from .services import base_user, mock_pipeline_service, mock_search_service
from .teams import test_team, test_team_create
from .user import test_user

# Explicit re-exports to fix F401 warnings
__all__ = [
    "base_collection",
    "base_file",
    "base_file_with_content",
    "base_llm_parameters",
    "base_pipeline_config",
    "base_prompt_template",
    "base_prompt_template_input",
    "base_question_gen_template",
    "base_question_gen_template_input",
    "base_rag_prompt_template",
    "base_rag_prompt_template_input",
    "base_user",
    "mock_collection_service",
    "mock_db_session",
    "mock_jwt_decode",
    "mock_jwt_settings",
    "mock_llm_provider",
    "mock_llm_response",
    "mock_oauth_client",
    "mock_pipeline_service",
    "mock_search_service",
    "provider_factory",
    "test_collection",
    "test_collection_create",
    "test_db",
    "test_documents",
    "test_file",
    "test_file_create",
    "test_llm_model",
    "test_llm_model_create",
    "test_llm_parameters",
    "test_llm_parameters_create",
    "test_llm_provider",
    "test_llm_provider_create",
    "test_pipeline",
    "test_pipeline_create",
    "test_prompt_template",
    "test_prompt_template_create",
    "test_session",
    "test_team",
    "test_team_create",
    "test_user",
    "uploaded_file",
    "vector_store",
]
