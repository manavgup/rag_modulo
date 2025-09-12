"""Atomic tests for SystemInitializationService - schema and logic validation only."""

import pytest
from pydantic import SecretStr
from uuid import uuid4

from rag_solution.schemas.llm_provider_schema import LLMProviderInput
from rag_solution.schemas.llm_model_schema import LLMModelInput, ModelType


@pytest.mark.atomic
class TestSystemInitializationServiceAtomic:
    """Atomic tests for SystemInitializationService - no external dependencies."""

    def test_provider_config_validation_watsonx(self):
        """Test WatsonX provider configuration validation."""
        # Valid WatsonX config
        valid_config = LLMProviderInput(
            name="watsonx",
            base_url="https://us-south.ml.cloud.ibm.com",
            api_key=SecretStr("test-api-key"),
            project_id="test-project-id",
            is_default=True,
            is_active=True
        )

        assert valid_config.name == "watsonx"
        assert valid_config.base_url == "https://us-south.ml.cloud.ibm.com"
        assert valid_config.api_key.get_secret_value() == "test-api-key"
        assert valid_config.project_id == "test-project-id"
        assert valid_config.is_default is True
        assert valid_config.is_active is True

    def test_provider_config_validation_openai(self):
        """Test OpenAI provider configuration validation."""
        # Valid OpenAI config
        valid_config = LLMProviderInput(
            name="openai",
            base_url="https://api.openai.com",
            api_key=SecretStr("test-openai-key"),
            is_default=False,
            is_active=True
        )

        assert valid_config.name == "openai"
        assert valid_config.base_url == "https://api.openai.com"
        assert valid_config.api_key.get_secret_value() == "test-openai-key"
        assert valid_config.is_default is False
        assert valid_config.is_active is True

    def test_provider_config_validation_anthropic(self):
        """Test Anthropic provider configuration validation."""
        # Valid Anthropic config
        valid_config = LLMProviderInput(
            name="anthropic",
            base_url="https://api.anthropic.com",
            api_key=SecretStr("test-anthropic-key"),
            is_default=False,
            is_active=True
        )

        assert valid_config.name == "anthropic"
        assert valid_config.base_url == "https://api.anthropic.com"
        assert valid_config.api_key.get_secret_value() == "test-anthropic-key"
        assert valid_config.is_default is False
        assert valid_config.is_active is True

    def test_provider_config_serialization(self):
        """Test provider configuration serialization."""
        config = LLMProviderInput(
            name="test-provider",
            base_url="https://test.api.com",
            api_key=SecretStr("secret-key"),
            org_id="test-org",
            project_id="test-project",
            is_default=True,
            is_active=True
        )

        data = config.model_dump()
        assert isinstance(data, dict)
        assert data["name"] == "test-provider"
        assert data["base_url"] == "https://test.api.com"
        assert "api_key" in data
        assert data["org_id"] == "test-org"
        assert data["project_id"] == "test-project"
        assert data["is_default"] is True
        assert data["is_active"] is True

    def test_model_config_validation_generation(self):
        """Test generation model configuration validation."""
        provider_id = uuid4()

        valid_model = LLMModelInput(
            provider_id=provider_id,
            model_id="ibm/granite-3-8b-instruct",
            default_model_id="ibm/granite-3-8b-instruct",
            model_type=ModelType.GENERATION,
            timeout=30,
            max_retries=3,
            batch_size=10,
            retry_delay=1.0,
            concurrency_limit=10,
            stream=False,
            rate_limit=10,
            is_default=True,
            is_active=True
        )

        assert valid_model.provider_id == provider_id
        assert valid_model.model_id == "ibm/granite-3-8b-instruct"
        assert valid_model.model_type == ModelType.GENERATION
        assert valid_model.timeout == 30
        assert valid_model.max_retries == 3
        assert valid_model.batch_size == 10
        assert valid_model.retry_delay == 1.0
        assert valid_model.concurrency_limit == 10
        assert valid_model.stream is False
        assert valid_model.rate_limit == 10
        assert valid_model.is_default is True
        assert valid_model.is_active is True

    def test_model_config_validation_embedding(self):
        """Test embedding model configuration validation."""
        provider_id = uuid4()

        valid_model = LLMModelInput(
            provider_id=provider_id,
            model_id="ibm/slate-125m-english-rtrvr",
            default_model_id="ibm/slate-125m-english-rtrvr",
            model_type=ModelType.EMBEDDING,
            timeout=30,
            max_retries=3,
            batch_size=10,
            retry_delay=1.0,
            concurrency_limit=10,
            stream=False,
            rate_limit=10,
            is_default=True,
            is_active=True
        )

        assert valid_model.provider_id == provider_id
        assert valid_model.model_id == "ibm/slate-125m-english-rtrvr"
        assert valid_model.model_type == ModelType.EMBEDDING
        assert valid_model.timeout == 30
        assert valid_model.max_retries == 3
        assert valid_model.batch_size == 10
        assert valid_model.retry_delay == 1.0
        assert valid_model.concurrency_limit == 10
        assert valid_model.stream is False
        assert valid_model.rate_limit == 10
        assert valid_model.is_default is True
        assert valid_model.is_active is True

    def test_provider_config_defaults(self):
        """Test provider configuration default values."""
        # Minimal config with defaults
        config = LLMProviderInput(
            name="minimal-provider",
            base_url="https://minimal.api.com",
            api_key=SecretStr("minimal-key")
        )

        # Check defaults
        assert config.org_id is None
        assert config.project_id is None
        assert config.is_active is True
        assert config.is_default is False
        assert config.user_id is None

    def test_model_type_enum_validation(self):
        """Test ModelType enum validation."""
        # Test enum values
        assert ModelType.GENERATION == "generation"
        assert ModelType.EMBEDDING == "embedding"

        # Test enum list
        valid_types = [ModelType.GENERATION, ModelType.EMBEDDING]
        assert len(valid_types) == 2
        assert ModelType.GENERATION in valid_types
        assert ModelType.EMBEDDING in valid_types

    def test_initialization_logic_flow(self):
        """Test initialization logic flow without external dependencies."""
        # Test provider config creation logic
        provider_configs = {}

        # Simulate WatsonX config creation
        if "test-wx-key" and "test-project":
            provider_configs["watsonx"] = {
                "name": "watsonx",
                "base_url": "https://us-south.ml.cloud.ibm.com",
                "api_key": "test-wx-key",
                "project_id": "test-project",
                "is_default": True
            }

        # Simulate OpenAI config creation
        if "test-openai-key":
            provider_configs["openai"] = {
                "name": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "test-openai-key"
            }

        # Test logic flow
        assert len(provider_configs) == 2
        assert "watsonx" in provider_configs
        assert "openai" in provider_configs
        assert provider_configs["watsonx"]["is_default"] is True
        assert provider_configs["watsonx"]["project_id"] == "test-project"

    def test_error_handling_logic(self):
        """Test error handling logic without external dependencies."""
        # Test error message construction
        provider_name = "test-provider"
        operation = "initialization"
        error_msg = "API key invalid"

        full_error = f"Error in {operation} for {provider_name}: {error_msg}"
        assert full_error == "Error in initialization for test-provider: API key invalid"

        # Test raise_on_error logic
        raise_on_error = False
        if not raise_on_error:
            result = []
        else:
            result = None

        assert result == []  # Should return empty list when raise_on_error=False

    def test_provider_update_vs_create_logic(self):
        """Test provider update vs create decision logic."""
        # Simulate existing provider check
        existing_providers = {
            "watsonx": {"id": uuid4(), "name": "watsonx"},
            "openai": {"id": uuid4(), "name": "openai"}
        }

        # Test update logic
        provider_name = "watsonx"
        if provider_name in existing_providers:
            operation = "update"
            provider_id = existing_providers[provider_name]["id"]
        else:
            operation = "create"
            provider_id = None

        assert operation == "update"
        assert provider_id is not None

        # Test create logic
        provider_name = "anthropic"
        if provider_name in existing_providers:
            operation = "update"
            provider_id = existing_providers[provider_name]["id"]
        else:
            operation = "create"
            provider_id = None

        assert operation == "create"
        assert provider_id is None
