"""Tests for configuration-related services with strong typing and validation."""

import pytest
from uuid import UUID
from typing import Dict, Any
from pydantic import SecretStr, ValidationError as PydanticValidationError

from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.user_service import UserService
from rag_solution.schemas.llm_provider_schema import (
    LLMProviderInput,
    LLMProviderOutput,
    LLMProviderModelInput,
    ModelType
)
from rag_solution.schemas.user_schema import UserInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateType
from core.custom_exceptions import (
    ProviderValidationError,
    ProviderConfigError,
    LLMProviderError,
    NotFoundException
)


@pytest.mark.service
class TestConfigurationServices:
    """Test configuration services functionality."""

    @pytest.fixture
    def test_user(self, db_session):
        """Create test user."""
        user_service = UserService(db_session)
        user = user_service.create_user(UserInput(
            ibm_id="test_ibm_id",
            email="test@example.com",
            name="Test User"
        ))
        return user

    @pytest.fixture
    def llm_provider_service(self, db_session) -> LLMProviderService:
        """Create LLM provider service fixture."""
        return LLMProviderService(db_session)

    @pytest.fixture
    def llm_parameters_service(self, db_session) -> LLMParametersService:
        """Create LLM parameters service fixture."""
        return LLMParametersService(db_session)

    @pytest.fixture
    def prompt_template_service(self, db_session) -> PromptTemplateService:
        """Create prompt template service fixture."""
        return PromptTemplateService(db_session)

    @pytest.fixture
    def test_provider_input(self) -> LLMProviderInput:
        """Create test provider input fixture."""
        return LLMProviderInput(
            name="test-watsonx",
            base_url="https://test.watsonx.ai/api",
            api_key=SecretStr("test-key"),
            project_id="test-project"
        )

    @pytest.fixture
    def test_model_input(self) -> LLMProviderModelInput:
        """Create test model input fixture."""
        return LLMProviderModelInput(
            provider_id=UUID("00000000-0000-0000-0000-000000000000"),  # Will be replaced in tests
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
            is_active=True
        )

    @pytest.fixture
    def test_llm_parameters(self, test_user) -> Dict[str, Any]:
        """Test LLM parameters data."""
        return {
            "name": "test-params",
            "user_id": test_user.id,
            "provider": "watsonx",
            "model_id": "granite-13b",
            "temperature": 0.7,
            "max_new_tokens": 1000,
            "min_new_tokens": 1,
            "repetition_penalty": 1.1,
            "stop_sequences": ["User:", "Assistant:"],
            "is_default": True
        }

    @pytest.fixture
    def test_prompt_template(self, test_user) -> Dict[str, Any]:
        """Test prompt template data."""
        return {
            "name": "test-template",
            "provider": "watsonx",
            "template_type": PromptTemplateType.RAG_QUERY,
            "system_prompt": "You are a helpful AI assistant.",
            "template_format": "Context:\n{context}\nQuestion:{question}",
            "input_variables": {
                "context": "Retrieved context",
                "question": "User's question"
            },
            "example_inputs": {
                "context": "Initial context",
                "question": "Initial question"
            },
            "is_default": True
        }

    @pytest.mark.unit
    async def test_create_provider(
        self,
        llm_provider_service: LLMProviderService,
        test_provider_input: LLMProviderInput
    ):
        """Test creating LLM provider."""
        provider = llm_provider_service.create_provider(test_provider_input)
        assert isinstance(provider, LLMProviderOutput)
        assert provider.name == test_provider_input.name
        assert str(provider.base_url) == str(test_provider_input.base_url)
        assert provider.project_id == test_provider_input.project_id
        assert provider.is_active
        assert isinstance(provider.id, UUID)

    @pytest.mark.unit
    async def test_create_provider_model(
        self,
        llm_provider_service: LLMProviderService,
        test_provider_input: LLMProviderInput,
        test_model_input: LLMProviderModelInput
    ):
        """Test creating provider model."""
        provider = llm_provider_service.create_provider(test_provider_input)
        test_model_input.provider_id = provider.id
        
        model = llm_provider_service.create_provider_model(test_model_input)
        assert model.model_id == test_model_input.model_id
        assert model.model_type == test_model_input.model_type
        assert model.is_default == test_model_input.is_default
        assert model.provider_id == provider.id

    @pytest.mark.unit
    async def test_create_llm_parameters(
        self,
        llm_parameters_service: LLMParametersService,
        test_llm_parameters: Dict[str, Any]
    ):
        """Test creating LLM parameters."""
        params = llm_parameters_service.create_or_update_parameters(
            test_llm_parameters["user_id"],
            test_llm_parameters
        )
        assert params.name == test_llm_parameters["name"]
        assert params.user_id == test_llm_parameters["user_id"]
        assert params.provider == test_llm_parameters["provider"]
        assert params.model_id == test_llm_parameters["model_id"]
        assert params.is_default == test_llm_parameters["is_default"]

    @pytest.mark.unit
    async def test_create_prompt_template(
        self,
        prompt_template_service: PromptTemplateService,
        test_prompt_template: Dict[str, Any],
        test_user
    ):
        """Test creating prompt template."""
        template = prompt_template_service.create_or_update_template(
            test_user.id,
            test_prompt_template
        )
        assert template.name == test_prompt_template["name"]
        assert template.provider == test_prompt_template["provider"]
        assert template.template_type == test_prompt_template["template_type"]
        assert template.is_default == test_prompt_template["is_default"]

    @pytest.mark.integration
    async def test_configuration_flow(
        self,
        llm_provider_service: LLMProviderService,
        llm_parameters_service: LLMParametersService,
        prompt_template_service: PromptTemplateService,
        test_provider_input: LLMProviderInput,
        test_model_input: LLMProviderModelInput,
        test_llm_parameters: Dict[str, Any],
        test_prompt_template: Dict[str, Any],
        test_user
    ):
        """Test complete configuration flow."""
        # Create provider
        provider = llm_provider_service.create_provider(test_provider_input)
        assert isinstance(provider, LLMProviderOutput)
        assert provider.id is not None
        
        # Create model
        test_model_input.provider_id = provider.id
        model = llm_provider_service.create_provider_model(test_model_input)
        assert model.id is not None

        # Create LLM parameters
        params = llm_parameters_service.create_or_update_parameters(
            test_user.id,
            test_llm_parameters
        )
        assert params.id is not None

        # Create prompt template
        template = prompt_template_service.create_or_update_template(
            test_user.id,
            test_prompt_template
        )
        assert template.id is not None

        # Verify relationships
        assert params.provider == test_llm_parameters["provider"]
        assert template.provider == test_prompt_template["provider"]
        assert params.model_id == test_llm_parameters["model_id"]
        assert params.user_id == test_llm_parameters["user_id"]

    @pytest.mark.error
    async def test_provider_validation_errors(
        self,
        llm_provider_service: LLMProviderService
    ):
        """Test provider validation error handling."""
        # Test invalid name
        with pytest.raises(ProviderValidationError) as exc_info:
            llm_provider_service.create_provider(LLMProviderInput(
                name="test@invalid",  # Invalid characters
                base_url="https://test.com",
                api_key=SecretStr("test-key")
            ))
        assert "name" in str(exc_info.value)

        # Test invalid URL
        with pytest.raises(ProviderValidationError) as exc_info:
            llm_provider_service.create_provider(LLMProviderInput(
                name="test-provider",
                base_url="not-a-url",  # Invalid URL
                api_key=SecretStr("test-key")
            ))
        assert "base_url" in str(exc_info.value)

    @pytest.mark.error
    async def test_model_validation_errors(
        self,
        llm_provider_service: LLMProviderService,
        test_provider_input: LLMProviderInput,
        test_model_input: LLMProviderModelInput
    ):
        """Test model validation error handling."""
        provider = llm_provider_service.create_provider(test_provider_input)
        test_model_input.provider_id = provider.id

        # Test invalid timeout
        test_model_input.timeout = 0
        with pytest.raises(ProviderValidationError) as exc_info:
            llm_provider_service.create_provider_model(test_model_input)
        assert "timeout" in str(exc_info.value)

        # Test missing provider ID
        test_model_input.provider_id = None
        with pytest.raises(ProviderConfigError) as exc_info:
            llm_provider_service.create_provider_model(test_model_input)
        assert "provider_id" in str(exc_info.value)

    @pytest.mark.error
    async def test_not_found_errors(
        self,
        llm_provider_service: LLMProviderService,
        llm_parameters_service: LLMParametersService,
        test_user
    ):
        """Test not found error handling."""
        # Test non-existent provider
        with pytest.raises(NotFoundException):
            llm_parameters_service.create_or_update_parameters(
                test_user.id,
                {
                    "name": "test-params",
                    "provider": "watsonx",
                    "model_id": "test-model"
                }
            )

        # Test non-existent user
        with pytest.raises(NotFoundException):
            llm_parameters_service.create_or_update_parameters(
                UUID("00000000-0000-0000-0000-000000000000"),
                {
                    "name": "test-params",
                    "provider": "watsonx",
                    "model_id": "test-model"
                }
            )
