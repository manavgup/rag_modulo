"""Unit tests for SystemInitializationService with mocked dependencies."""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from core.config import Settings
from core.custom_exceptions import LLMProviderError
from rag_solution.schemas.llm_model_schema import ModelType
from rag_solution.schemas.llm_provider_schema import LLMProviderInput, LLMProviderOutput
from rag_solution.services.system_initialization_service import SystemInitializationService


@pytest.mark.unit
class TestSystemInitializationServiceUnit:
    """Unit tests for SystemInitializationService with mocked dependencies."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Mock settings with provider configurations."""
        settings = Mock(spec=Settings)
        settings.wx_api_key = "test-wx-key"  # pragma: allowlist secret
        settings.wx_project_id = "test-project-id"  # pragma: allowlist secret
        settings.wx_url = "https://test-wx.com"
        settings.openai_api_key = "test-openai-key"  # pragma: allowlist secret
        settings.anthropic_api_key = "test-anthropic-key"  # pragma: allowlist secret
        settings.rag_llm = "ibm/granite-3-8b-instruct"
        settings.embedding_model = "ibm/slate-125m-english-rtrvr"
        return settings

    @pytest.fixture
    def mock_llm_provider_service(self):
        """Mock LLM provider service."""
        return Mock()

    @pytest.fixture
    def mock_llm_model_service(self):
        """Mock LLM model service."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        """Create service instance with mocked dependencies."""
        with (
            patch("rag_solution.services.system_initialization_service.LLMProviderService") as _mock_provider_service,
            patch("rag_solution.services.system_initialization_service.LLMModelService") as _mock_model_service,
        ):
            service = SystemInitializationService(mock_db, mock_settings)
            service.llm_provider_service = Mock()
            service.llm_model_service = Mock()
            return service

    def test_service_initialization(self, mock_db, mock_settings):
        """Test service initialization with dependency injection."""
        with (
            patch("rag_solution.services.system_initialization_service.LLMProviderService") as mock_provider_service,
            patch("rag_solution.services.system_initialization_service.LLMModelService") as mock_model_service,
        ):
            service = SystemInitializationService(mock_db, mock_settings)

            assert service.db is mock_db
            assert service.settings is mock_settings
            mock_provider_service.assert_called_once_with(mock_db)
            mock_model_service.assert_called_once_with(mock_db)

    def test_get_provider_configs_with_all_providers(self, service, mock_settings):  # noqa: ARG002
        """Test _get_provider_configs returns all configured providers."""
        result = service._get_provider_configs()

        assert isinstance(result, dict)
        assert "watsonx" in result
        assert "openai" in result
        assert "anthropic" in result

        # Check WatsonX config
        watsonx_config = result["watsonx"]
        assert watsonx_config.name == "watsonx"
        assert watsonx_config.base_url == "https://test-wx.com"
        assert watsonx_config.project_id == "test-project-id"
        assert watsonx_config.is_default is True

        # Check OpenAI config
        openai_config = result["openai"]
        assert openai_config.name == "openai"
        assert openai_config.base_url == "https://api.openai.com"
        assert openai_config.is_default is False

        # Check Anthropic config
        anthropic_config = result["anthropic"]
        assert anthropic_config.name == "anthropic"
        assert anthropic_config.base_url == "https://api.anthropic.com"
        assert anthropic_config.is_default is False

    def test_get_provider_configs_with_partial_providers(self, service, mock_settings):
        """Test _get_provider_configs with only some providers configured."""
        # Only OpenAI configured
        mock_settings.wx_api_key = None
        mock_settings.wx_project_id = None
        mock_settings.anthropic_api_key = None

        result = service._get_provider_configs()

        assert isinstance(result, dict)
        assert "openai" in result
        assert "watsonx" not in result
        assert "anthropic" not in result
        assert len(result) == 1

    def test_get_provider_configs_with_no_providers(self, service, mock_settings):
        """Test _get_provider_configs with no providers configured."""
        mock_settings.wx_api_key = None
        mock_settings.wx_project_id = None
        mock_settings.openai_api_key = None
        mock_settings.anthropic_api_key = None

        result = service._get_provider_configs()

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_initialize_providers_success_all_new(self, service):
        """Test initialize_providers with all new providers."""
        # Mock empty existing providers
        service.llm_provider_service.get_all_providers.return_value = []

        # Mock provider configs
        mock_provider = LLMProviderOutput(
            id=uuid4(),
            name="watsonx",
            base_url="https://test-wx.com",
            org_id=None,
            project_id="test-project",
            is_active=True,
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with (
            patch.object(service, "_get_provider_configs") as mock_get_configs,
            patch.object(service, "_initialize_single_provider") as mock_init_single,
        ):
            mock_get_configs.return_value = {
                "watsonx": LLMProviderInput(name="watsonx", base_url="https://test.com", api_key="test-key")
            }
            mock_init_single.return_value = mock_provider

            result = service.initialize_providers()

            assert len(result) == 1
            assert result[0] is mock_provider
            service.llm_provider_service.get_all_providers.assert_called_once()
            mock_get_configs.assert_called_once()
            mock_init_single.assert_called_once()

    def test_initialize_providers_success_with_existing(self, service):
        """Test initialize_providers with existing providers."""
        # Mock existing provider
        existing_provider = LLMProviderOutput(
            id=uuid4(),
            name="watsonx",
            base_url="https://old-url.com",
            org_id=None,
            project_id="old-project",
            is_active=True,
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        service.llm_provider_service.get_all_providers.return_value = [existing_provider]

        # Mock updated provider
        updated_provider = LLMProviderOutput(
            id=existing_provider.id,
            name="watsonx",
            base_url="https://test-wx.com",
            org_id=None,
            project_id="test-project",
            is_active=True,
            is_default=True,
            created_at=existing_provider.created_at,
            updated_at=datetime.now(),
        )

        with (
            patch.object(service, "_get_provider_configs") as mock_get_configs,
            patch.object(service, "_initialize_single_provider") as mock_init_single,
        ):
            mock_get_configs.return_value = {
                "watsonx": LLMProviderInput(name="watsonx", base_url="https://test-wx.com", api_key="test-key")
            }
            mock_init_single.return_value = updated_provider

            result = service.initialize_providers()

            assert len(result) == 1
            assert result[0] is updated_provider
            mock_init_single.assert_called_once_with(
                "watsonx",
                mock_get_configs.return_value["watsonx"],
                existing_provider,
                False,
            )

    def test_initialize_providers_get_providers_error_no_raise(self, service):
        """Test initialize_providers when get_all_providers fails with raise_on_error=False."""
        service.llm_provider_service.get_all_providers.side_effect = Exception("Database connection failed")

        result = service.initialize_providers(raise_on_error=False)

        assert result == []
        service.llm_provider_service.get_all_providers.assert_called_once()

    def test_initialize_providers_get_providers_error_with_raise(self, service):
        """Test initialize_providers when get_all_providers fails with raise_on_error=True."""
        service.llm_provider_service.get_all_providers.side_effect = Exception("Database connection failed")

        with pytest.raises(LLMProviderError) as exc_info:
            service.initialize_providers(raise_on_error=True)

        assert "Database connection failed" in str(exc_info.value)
        service.llm_provider_service.get_all_providers.assert_called_once()

    def test_initialize_providers_no_configs(self, service):
        """Test initialize_providers when no provider configs available."""
        service.llm_provider_service.get_all_providers.return_value = []

        with patch.object(service, "_get_provider_configs") as mock_get_configs:
            mock_get_configs.return_value = {}

            result = service.initialize_providers()

            assert result == []
            mock_get_configs.assert_called_once()

    def test_initialize_providers_single_provider_error_no_raise(self, service):
        """Test initialize_providers when single provider fails with raise_on_error=False."""
        service.llm_provider_service.get_all_providers.return_value = []

        with (
            patch.object(service, "_get_provider_configs") as mock_get_configs,
            patch.object(service, "_initialize_single_provider") as mock_init_single,
        ):
            mock_get_configs.return_value = {
                "watsonx": LLMProviderInput(name="watsonx", base_url="https://test.com", api_key="invalid-key")
            }
            mock_init_single.side_effect = Exception("Invalid API key")

            result = service.initialize_providers(raise_on_error=False)

            assert result == []
            mock_init_single.assert_called_once()

    def test_initialize_providers_single_provider_error_with_raise(self, service):
        """Test initialize_providers when single provider fails with raise_on_error=True."""
        service.llm_provider_service.get_all_providers.return_value = []

        with (
            patch.object(service, "_get_provider_configs") as mock_get_configs,
            patch.object(service, "_initialize_single_provider") as mock_init_single,
        ):
            mock_get_configs.return_value = {
                "watsonx": LLMProviderInput(name="watsonx", base_url="https://test.com", api_key="invalid-key")
            }
            mock_init_single.side_effect = Exception("Invalid API key")

            with pytest.raises(LLMProviderError) as exc_info:
                service.initialize_providers(raise_on_error=True)

            assert "Invalid API key" in str(exc_info.value)

    def test_initialize_single_provider_create_new(self, service):
        """Test _initialize_single_provider creates new provider."""
        config = LLMProviderInput(name="openai", base_url="https://api.openai.com", api_key="test-key")

        mock_provider = LLMProviderOutput(
            id=uuid4(),
            name="openai",
            base_url="https://api.openai.com",
            org_id=None,
            project_id=None,
            is_active=True,
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        service.llm_provider_service.create_provider.return_value = mock_provider

        result = service._initialize_single_provider("openai", config, None, False)

        assert result is mock_provider
        service.llm_provider_service.create_provider.assert_called_once_with(config)

    def test_initialize_single_provider_update_existing(self, service):
        """Test _initialize_single_provider updates existing provider."""
        existing_provider = LLMProviderOutput(
            id=uuid4(),
            name="openai",
            base_url="https://old-api.openai.com",
            org_id=None,
            project_id=None,
            is_active=True,
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        config = LLMProviderInput(name="openai", base_url="https://api.openai.com", api_key="test-key")

        updated_provider = LLMProviderOutput(
            id=existing_provider.id,
            name="openai",
            base_url="https://api.openai.com",
            org_id=None,
            project_id=None,
            is_active=True,
            is_default=False,
            created_at=existing_provider.created_at,
            updated_at=datetime.now(),
        )

        service.llm_provider_service.update_provider.return_value = updated_provider

        result = service._initialize_single_provider("openai", config, existing_provider, False)

        assert result is updated_provider
        service.llm_provider_service.update_provider.assert_called_once_with(
            existing_provider.id, config.model_dump(exclude_unset=True)
        )

    def test_initialize_single_provider_create_error_no_raise(self, service):
        """Test _initialize_single_provider handles create error with raise_on_error=False."""
        config = LLMProviderInput(name="openai", base_url="https://api.openai.com", api_key="invalid-key")

        service.llm_provider_service.create_provider.side_effect = Exception("Invalid API key")

        result = service._initialize_single_provider("openai", config, None, False)

        assert result is None
        service.llm_provider_service.create_provider.assert_called_once_with(config)

    def test_initialize_single_provider_create_error_with_raise(self, service):
        """Test _initialize_single_provider handles create error with raise_on_error=True."""
        config = LLMProviderInput(name="openai", base_url="https://api.openai.com", api_key="invalid-key")

        service.llm_provider_service.create_provider.side_effect = Exception("Invalid API key")

        with pytest.raises(Exception) as exc_info:
            service._initialize_single_provider("openai", config, None, True)

        assert "Invalid API key" in str(exc_info.value)

    def test_initialize_single_provider_watsonx_with_models(self, service):
        """Test _initialize_single_provider for WatsonX creates models."""
        provider_id = uuid4()
        config = LLMProviderInput(
            name="watsonx",
            base_url="https://test-wx.com",
            api_key="test-key",  # pragma: allowlist secret
            project_id="test-project",
        )

        mock_provider = LLMProviderOutput(
            id=provider_id,
            name="watsonx",
            base_url="https://test-wx.com",
            org_id=None,
            project_id="test-project",
            is_active=True,
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        service.llm_provider_service.create_provider.return_value = mock_provider

        with patch.object(service, "_setup_watsonx_models") as mock_setup_models:
            result = service._initialize_single_provider("watsonx", config, None, False)

            assert result is mock_provider
            mock_setup_models.assert_called_once_with(provider_id, False)

    def test_setup_watsonx_models_success(self, service, mock_settings):
        """Test _setup_watsonx_models creates generation and embedding models."""
        provider_id = uuid4()

        mock_generation_model = Mock()
        mock_embedding_model = Mock()

        # Mock get_models_by_provider to return empty list (no existing models)
        service.llm_model_service.get_models_by_provider.return_value = []

        service.llm_model_service.create_model.side_effect = [
            mock_generation_model,
            mock_embedding_model,
        ]

        service._setup_watsonx_models(provider_id, False)

        # Should be called twice - once for generation, once for embedding
        assert service.llm_model_service.create_model.call_count == 2

        # Check the calls were made with correct model types
        calls = service.llm_model_service.create_model.call_args_list
        generation_call_args = calls[0][0][0]
        embedding_call_args = calls[1][0][0]

        assert generation_call_args.provider_id == provider_id
        assert generation_call_args.model_type == ModelType.GENERATION
        assert generation_call_args.model_id == mock_settings.rag_llm

        assert embedding_call_args.provider_id == provider_id
        assert embedding_call_args.model_type == ModelType.EMBEDDING
        assert embedding_call_args.model_id == mock_settings.embedding_model

    def test_setup_watsonx_models_error_no_raise(self, service):
        """Test _setup_watsonx_models handles error with raise_on_error=False."""
        provider_id = uuid4()

        # Mock get_models_by_provider to return empty list
        service.llm_model_service.get_models_by_provider.return_value = []

        service.llm_model_service.create_model.side_effect = Exception("Model creation failed")

        # Should not raise exception
        service._setup_watsonx_models(provider_id, False)

        service.llm_model_service.create_model.assert_called_once()

    def test_setup_watsonx_models_error_with_raise(self, service):
        """Test _setup_watsonx_models handles error with raise_on_error=True."""
        provider_id = uuid4()

        # Mock get_models_by_provider to return empty list
        service.llm_model_service.get_models_by_provider.return_value = []

        service.llm_model_service.create_model.side_effect = Exception("Model creation failed")

        with pytest.raises(Exception) as exc_info:
            service._setup_watsonx_models(provider_id, True)

        assert "Model creation failed" in str(exc_info.value)
