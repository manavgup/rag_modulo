"""Atomic tests for configuration data validation and schemas."""

from uuid import uuid4

import pytest
from rag_solution.schemas.llm_model_schema import LLMModelInput, ModelType
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.llm_provider_schema import LLMProviderInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType
from pydantic import SecretStr


@pytest.mark.atomic
class TestConfigurationDataValidation:
    """Test configuration data validation and schemas - no external dependencies."""

    def test_llm_provider_input_validation(self):
        """Test LLMProviderInput schema validation."""
        # Valid provider input
        valid_provider = LLMProviderInput(
            name="test-watsonx",
            base_url="https://test.watsonx.ai/api",
            api_key=SecretStr("test-key"),
            project_id="test-project",
            org_id="test-org",
            is_active=True,
            is_default=False,
            user_id=uuid4(),
        )

        assert valid_provider.name == "test-watsonx"
        assert str(valid_provider.base_url) == "https://test.watsonx.ai/api"
        assert valid_provider.project_id == "test-project"
        assert valid_provider.org_id == "test-org"
        assert valid_provider.is_active is True
        assert not valid_provider.is_default
        assert valid_provider.user_id is not None

    def test_llm_provider_name_validation(self):
        """Test LLM provider name validation rules."""
        # Valid provider names
        valid_names = ["watsonx", "openai", "anthropic", "test-provider-123", "provider_with_underscores"]

        for name in valid_names:
            provider = LLMProviderInput(
                name=name,
                base_url="https://test.example.com",
                api_key=SecretStr("test-key"),
                project_id="test-project",
                org_id="test-org",
                is_active=True,
                is_default=False,
                user_id=uuid4(),
            )
            assert provider.name == name
            assert isinstance(provider.name, str)
            assert len(provider.name.strip()) > 0

    def test_llm_provider_url_validation(self):
        """Test LLM provider URL validation rules."""
        # Valid URLs
        valid_urls = [
            "https://api.openai.com/v1",
            "https://test.watsonx.ai/api",
            "https://api.anthropic.com",
            "http://localhost:8000/api",
            "https://api.example.com/v1/chat",
        ]

        for url in valid_urls:
            provider = LLMProviderInput(
                name="test-provider",
                base_url=url,
                api_key=SecretStr("test-key"),
                project_id="test-project",
                org_id="test-org",
                is_active=True,
                is_default=False,
                user_id=uuid4(),
            )
            assert str(provider.base_url) == url
            assert isinstance(provider.base_url, str)

    def test_llm_provider_boolean_validation(self):
        """Test LLM provider boolean field validation."""
        # Test active flag
        active_provider = LLMProviderInput(
            name="active-provider",
            base_url="https://test.example.com",
            api_key=SecretStr("test-key"),
            project_id="test-project",
            org_id="test-org",
            is_active=True,
            is_default=False,
            user_id=uuid4(),
        )
        assert active_provider.is_active is True

        # Test default flag
        default_provider = LLMProviderInput(
            name="default-provider",
            base_url="https://test.example.com",
            api_key=SecretStr("test-key"),
            project_id="test-project",
            org_id="test-org",
            is_active=True,
            is_default=True,
            user_id=uuid4(),
        )
        assert default_provider.is_default is True

    def test_llm_model_input_validation(self):
        """Test LLMModelInput schema validation."""
        # Valid model input
        valid_model = LLMModelInput(
            provider_id=uuid4(),
            model_id="granite-13b",
            default_model_id="granite-13b",
            model_type=ModelType.GENERATION,
            timeout=30,
            max_retries=3,
            batch_size=10,
            retry_delay=1.0,
            concurrency_limit=10,
            stream=False,
            rate_limit=10,
            is_default=True,
            is_active=True,
        )

        assert valid_model.model_id == "granite-13b"
        assert valid_model.default_model_id == "granite-13b"
        assert valid_model.model_type == ModelType.GENERATION
        assert valid_model.timeout == 30
        assert valid_model.max_retries == 3
        assert valid_model.batch_size == 10
        assert valid_model.retry_delay == 1.0
        assert valid_model.concurrency_limit == 10
        assert not valid_model.stream
        assert valid_model.rate_limit == 10
        assert valid_model.is_default is True
        assert valid_model.is_active is True

    def test_llm_parameters_input_validation(self):
        """Test LLMParametersInput schema validation."""
        # Valid parameters input
        valid_params = LLMParametersInput(
            name="test-params",
            user_id=uuid4(),
            description="Test parameters",
            max_new_tokens=1000,
            temperature=0.7,
            top_k=50,
            top_p=1.0,
            repetition_penalty=1.1,
            is_default=True,
        )

        assert valid_params.name == "test-params"
        assert valid_params.user_id is not None
        assert valid_params.description == "Test parameters"
        assert valid_params.max_new_tokens == 1000
        assert valid_params.temperature == 0.7
        assert valid_params.top_k == 50
        assert valid_params.top_p == 1.0
        assert valid_params.repetition_penalty == 1.1
        assert valid_params.is_default is True

    def test_prompt_template_input_validation(self):
        """Test PromptTemplateInput schema validation."""
        # Valid template input
        valid_template = PromptTemplateInput(
            name="test-template",
            user_id=uuid4(),
            template_type=PromptTemplateType.RAG_QUERY,
            system_prompt="You are a helpful AI assistant.",
            template_format="Context:\n{context}\nQuestion:{question}",
            input_variables={"context": "Retrieved context", "question": "User's question"},
            example_inputs={"context": "Initial context", "question": "Initial question"},
            max_context_length=1000,
            is_default=True,
        )

        assert valid_template.name == "test-template"
        assert valid_template.user_id is not None
        assert valid_template.template_type == PromptTemplateType.RAG_QUERY
        assert valid_template.system_prompt == "You are a helpful AI assistant."
        assert valid_template.template_format == "Context:\n{context}\nQuestion:{question}"
        assert valid_template.input_variables == {"context": "Retrieved context", "question": "User's question"}
        assert valid_template.example_inputs == {"context": "Initial context", "question": "Initial question"}
        assert valid_template.max_context_length == 1000
        assert valid_template.is_default is True

    def test_model_type_enum_validation(self):
        """Test ModelType enum validation."""
        # Test all valid model types
        valid_types = [ModelType.GENERATION, ModelType.EMBEDDING]

        for model_type in valid_types:
            model = LLMModelInput(
                provider_id=uuid4(),
                model_id="test-model",
                default_model_id="test-model",
                model_type=model_type,
                timeout=30,
                max_retries=3,
                batch_size=10,
                retry_delay=1.0,
                concurrency_limit=10,
                stream=False,
                rate_limit=10,
                is_default=True,
                is_active=True,
            )
            assert model.model_type == model_type

    def test_prompt_template_type_enum_validation(self):
        """Test PromptTemplateType enum validation."""
        # Test all valid template types
        valid_types = [
            PromptTemplateType.RAG_QUERY,
            PromptTemplateType.QUESTION_GENERATION,
            PromptTemplateType.RESPONSE_EVALUATION,
            PromptTemplateType.CUSTOM,
        ]

        for template_type in valid_types:
            template = PromptTemplateInput(
                name="test-template",
                user_id=uuid4(),
                template_type=template_type,
                system_prompt="Test prompt",
                template_format="Test format with {variable}",
                input_variables={"variable": "Test variable"},
                example_inputs={"variable": "Test example"},
                max_context_length=1000,
                is_default=True,
            )
            assert template.template_type == template_type

    def test_configuration_serialization(self):
        """Test configuration data serialization."""
        # Test provider serialization
        provider = LLMProviderInput(
            name="serialization-test",
            base_url="https://test.example.com",
            api_key=SecretStr("test-key"),
            project_id="test-project",
            org_id="test-org",
            is_active=True,
            is_default=False,
            user_id=uuid4(),
        )

        data = provider.model_dump()
        assert isinstance(data, dict)
        assert "name" in data
        assert "base_url" in data
        assert "api_key" in data
        assert "project_id" in data
        assert "org_id" in data
        assert "is_active" in data
        assert "is_default" in data
        assert "user_id" in data
        assert data["name"] == "serialization-test"
        assert data["is_active"] is True
        assert not data["is_default"]
