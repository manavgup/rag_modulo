"""Unit tests for RuntimeConfigService.

This module provides comprehensive unit tests for the Runtime Configuration Service,
covering all CRUD operations, hierarchical configuration resolution, scope validation,
and Settings fallback integration.
"""

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from core.custom_exceptions import NotFoundException, ValidationError
from pydantic import UUID4
from rag_solution.schemas.runtime_config_schema import (
    ConfigCategory,
    ConfigScope,
    EffectiveConfig,
    RuntimeConfigInput,
    RuntimeConfigOutput,
)
from rag_solution.services.runtime_config_service import RuntimeConfigService


class TestRuntimeConfigService:
    """Test cases for RuntimeConfigService."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create a mock settings object."""
        settings = Mock()
        settings.max_new_tokens = 1024
        settings.temperature = 0.7
        settings.top_k = 50
        settings.top_p = 1.0
        settings.repetition_penalty = 1.1
        return settings

    @pytest.fixture
    def service(self, mock_db: Mock, mock_settings: Mock) -> RuntimeConfigService:
        """Create a RuntimeConfigService instance with mocked dependencies."""
        service = RuntimeConfigService(mock_db, mock_settings)
        # Mock the repository
        service.repository = Mock()
        return service

    @pytest.fixture
    def sample_user_id(self) -> UUID4:
        """Create a sample user ID."""
        return uuid4()

    @pytest.fixture
    def sample_collection_id(self) -> UUID4:
        """Create a sample collection ID."""
        return uuid4()

    @pytest.fixture
    def sample_config_id(self) -> UUID4:
        """Create a sample config ID."""
        return uuid4()

    @pytest.fixture
    def sample_global_config_input(self) -> RuntimeConfigInput:
        """Create a sample global configuration input."""
        return RuntimeConfigInput(
            scope=ConfigScope.GLOBAL,
            category=ConfigCategory.LLM,
            config_key="max_new_tokens",
            config_value={"value": 1024, "type": "int"},
            description="Global default token limit",
            is_active=True,
        )

    @pytest.fixture
    def sample_user_config_input(self, sample_user_id: UUID4) -> RuntimeConfigInput:
        """Create a sample user configuration input."""
        return RuntimeConfigInput(
            scope=ConfigScope.USER,
            category=ConfigCategory.LLM,
            config_key="temperature",
            config_value={"value": 0.8, "type": "float"},
            user_id=sample_user_id,
            description="User-specific temperature setting",
            is_active=True,
        )

    @pytest.fixture
    def sample_collection_config_input(
        self, sample_user_id: UUID4, sample_collection_id: UUID4
    ) -> RuntimeConfigInput:
        """Create a sample collection configuration input."""
        return RuntimeConfigInput(
            scope=ConfigScope.COLLECTION,
            category=ConfigCategory.LLM,
            config_key="temperature",
            config_value={"value": 0.9, "type": "float"},
            user_id=sample_user_id,
            collection_id=sample_collection_id,
            description="Collection-specific temperature override",
            is_active=True,
        )

    @pytest.fixture
    def sample_config_output(self, sample_config_id: UUID4) -> RuntimeConfigOutput:
        """Create a sample configuration output."""
        return RuntimeConfigOutput(
            id=sample_config_id,
            scope=ConfigScope.GLOBAL,
            category=ConfigCategory.LLM,
            config_key="max_new_tokens",
            config_value={"value": 1024, "type": "int"},
            description="Global default token limit",
            is_active=True,
            user_id=None,
            collection_id=None,
            created_by=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    # ============================================================================
    # INITIALIZATION TESTS
    # ============================================================================

    def test_init(self, mock_db: Mock, mock_settings: Mock) -> None:
        """Test RuntimeConfigService initialization."""
        service = RuntimeConfigService(mock_db, mock_settings)

        assert service.db is mock_db
        assert service.settings is mock_settings
        assert service.repository is not None

    # ============================================================================
    # CREATE OPERATIONS
    # ============================================================================

    def test_create_config_global_success(
        self,
        service: RuntimeConfigService,
        sample_global_config_input: RuntimeConfigInput,
        sample_config_output: RuntimeConfigOutput,
    ) -> None:
        """Test successful creation of global configuration."""
        service.repository.create.return_value = sample_config_output

        result = service.create_config(sample_global_config_input)

        assert result == sample_config_output
        assert result.scope == ConfigScope.GLOBAL
        service.repository.create.assert_called_once_with(sample_global_config_input)

    def test_create_config_user_success(
        self,
        service: RuntimeConfigService,
        sample_user_config_input: RuntimeConfigInput,
        sample_user_id: UUID4,
        sample_config_id: UUID4,
    ) -> None:
        """Test successful creation of user-scoped configuration."""
        user_output = RuntimeConfigOutput(
            id=sample_config_id,
            scope=ConfigScope.USER,
            category=ConfigCategory.LLM,
            config_key="temperature",
            config_value={"value": 0.8, "type": "float"},
            description="User-specific temperature setting",
            is_active=True,
            user_id=sample_user_id,
            collection_id=None,
            created_by=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.create.return_value = user_output

        result = service.create_config(sample_user_config_input)

        assert result == user_output
        assert result.scope == ConfigScope.USER
        assert result.user_id == sample_user_id
        service.repository.create.assert_called_once_with(sample_user_config_input)

    def test_create_config_collection_success(
        self,
        service: RuntimeConfigService,
        sample_collection_config_input: RuntimeConfigInput,
        sample_user_id: UUID4,
        sample_collection_id: UUID4,
        sample_config_id: UUID4,
    ) -> None:
        """Test successful creation of collection-scoped configuration."""
        collection_output = RuntimeConfigOutput(
            id=sample_config_id,
            scope=ConfigScope.COLLECTION,
            category=ConfigCategory.LLM,
            config_key="temperature",
            config_value={"value": 0.9, "type": "float"},
            description="Collection-specific temperature override",
            is_active=True,
            user_id=sample_user_id,
            collection_id=sample_collection_id,
            created_by=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.create.return_value = collection_output

        result = service.create_config(sample_collection_config_input)

        assert result == collection_output
        assert result.scope == ConfigScope.COLLECTION
        assert result.user_id == sample_user_id
        assert result.collection_id == sample_collection_id
        service.repository.create.assert_called_once_with(sample_collection_config_input)

    def test_create_config_global_with_user_id_fails(
        self, service: RuntimeConfigService, sample_user_id: UUID4
    ) -> None:
        """Test that GLOBAL scope with user_id raises ValidationError at schema level."""
        # Pydantic raises validation error when creating the input schema
        with pytest.raises(Exception) as exc_info:  # Pydantic ValidationError
            RuntimeConfigInput(
                scope=ConfigScope.GLOBAL,
                category=ConfigCategory.LLM,
                config_key="max_new_tokens",
                config_value={"value": 1024, "type": "int"},
                user_id=sample_user_id,  # Invalid for GLOBAL scope
            )

        assert "user_id must be None for GLOBAL scope" in str(exc_info.value)
        service.repository.create.assert_not_called()

    def test_create_config_user_without_user_id_fails(
        self, service: RuntimeConfigService
    ) -> None:
        """Test that USER scope without user_id raises ValidationError."""
        from pydantic import ValidationError as PydanticValidationError
        
        # Pydantic validation happens during RuntimeConfigInput creation
        # The model_validator raises ValueError which Pydantic wraps in ValidationError
        with pytest.raises(PydanticValidationError) as exc_info:
            invalid_input = RuntimeConfigInput(
                scope=ConfigScope.USER,
                category=ConfigCategory.LLM,
                config_key="temperature",
                config_value={"value": 0.8, "type": "float"},
                # Missing user_id
            )

        # Check that the validation error message mentions user_id requirement
        error_str = str(exc_info.value)
        assert "user_id" in error_str.lower() or "USER scope" in error_str

    def test_create_config_collection_without_collection_id_fails(
        self, service: RuntimeConfigService, sample_user_id: UUID4
    ) -> None:
        """Test that COLLECTION scope without collection_id raises ValidationError."""
        from pydantic import ValidationError as PydanticValidationError
        
        # Pydantic validation happens during RuntimeConfigInput creation
        # The model_validator raises ValueError which Pydantic wraps in ValidationError
        with pytest.raises(PydanticValidationError) as exc_info:
            invalid_input = RuntimeConfigInput(
                scope=ConfigScope.COLLECTION,
                category=ConfigCategory.LLM,
                config_key="temperature",
                config_value={"value": 0.9, "type": "float"},
                user_id=sample_user_id,
                # Missing collection_id
            )

        # Check that the validation error message mentions collection_id requirement
        error_str = str(exc_info.value)
        assert "collection_id" in error_str.lower() or "COLLECTION scope" in error_str
        service.repository.create.assert_not_called()

    # ============================================================================
    # READ OPERATIONS
    # ============================================================================

    def test_get_config_success(
        self,
        service: RuntimeConfigService,
        sample_config_id: UUID4,
        sample_config_output: RuntimeConfigOutput,
    ) -> None:
        """Test successful configuration retrieval by ID."""
        service.repository.get.return_value = sample_config_output

        result = service.get_config(sample_config_id)

        assert result == sample_config_output
        assert result.id == sample_config_id
        service.repository.get.assert_called_once_with(sample_config_id)

    def test_get_config_not_found(
        self, service: RuntimeConfigService, sample_config_id: UUID4
    ) -> None:
        """Test get_config raises NotFoundException when config not found."""
        service.repository.get.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            service.get_config(sample_config_id)

        assert exc_info.value.details["resource_type"] == "RuntimeConfig"
        assert exc_info.value.details["resource_id"] == str(sample_config_id)
        service.repository.get.assert_called_once_with(sample_config_id)

    def test_get_effective_config_success(
        self,
        service: RuntimeConfigService,
        sample_user_id: UUID4,
        sample_collection_id: UUID4,
    ) -> None:
        """Test successful effective configuration retrieval."""
        effective_config = EffectiveConfig(
            category=ConfigCategory.LLM,
            values={"temperature": 0.9, "max_new_tokens": 1024},
            sources={"temperature": "collection", "max_new_tokens": "global"},
        )
        service.repository.get_effective_config.return_value = effective_config

        result = service.get_effective_config(sample_user_id, sample_collection_id, ConfigCategory.LLM)

        assert result == effective_config
        assert result.category == ConfigCategory.LLM
        assert len(result.values) == 2
        service.repository.get_effective_config.assert_called_once_with(
            sample_user_id, sample_collection_id, ConfigCategory.LLM
        )

    def test_get_effective_config_with_settings_fallback(
        self,
        service: RuntimeConfigService,
        sample_user_id: UUID4,
    ) -> None:
        """Test effective config uses Settings as fallback."""
        # Mock repository to return config with Settings fallback
        effective_config = EffectiveConfig(
            category=ConfigCategory.LLM,
            values={"max_new_tokens": 1024},  # From Settings
            sources={"max_new_tokens": "settings"},
        )
        service.repository.get_effective_config.return_value = effective_config

        result = service.get_effective_config(sample_user_id, None, ConfigCategory.LLM)

        assert result.values["max_new_tokens"] == 1024
        assert result.sources["max_new_tokens"] == "settings"
        service.repository.get_effective_config.assert_called_once_with(
            sample_user_id, None, ConfigCategory.LLM
        )

    # ============================================================================
    # UPDATE OPERATIONS
    # ============================================================================

    def test_update_config_success(
        self,
        service: RuntimeConfigService,
        sample_config_id: UUID4,
        sample_config_output: RuntimeConfigOutput,
    ) -> None:
        """Test successful configuration update."""
        # Mock existing config retrieval
        service.repository.get.return_value = sample_config_output

        # Mock update
        updated_output = RuntimeConfigOutput(
            id=sample_config_id,
            scope=ConfigScope.GLOBAL,
            category=ConfigCategory.LLM,
            config_key="max_new_tokens",
            config_value={"value": 2048, "type": "int"},  # Updated value
            description="Updated token limit",
            is_active=True,
            user_id=None,
            collection_id=None,
            created_by=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.update.return_value = updated_output

        updates = {"config_value": {"value": 2048, "type": "int"}, "description": "Updated token limit"}
        result = service.update_config(sample_config_id, updates)

        assert result == updated_output
        assert result.config_value["value"] == 2048
        service.repository.update.assert_called_once_with(sample_config_id, updates)

    def test_update_config_not_found(
        self, service: RuntimeConfigService, sample_config_id: UUID4
    ) -> None:
        """Test update_config raises NotFoundException when config not found."""
        service.repository.get.return_value = None

        with pytest.raises(NotFoundException):
            service.update_config(sample_config_id, {"description": "Updated"})

        service.repository.update.assert_not_called()

    def test_update_config_scope_change_validates(
        self,
        service: RuntimeConfigService,
        sample_config_id: UUID4,
        sample_config_output: RuntimeConfigOutput,
        sample_user_id: UUID4,
    ) -> None:
        """Test that updating scope triggers validation."""
        service.repository.get.return_value = sample_config_output

        # Try to change GLOBAL to USER without adding user_id (should fail)
        # Need to use string value for scope update since it's stored as string in DB
        updates = {"scope": "user"}  # String value matches what would come from API

        with pytest.raises(Exception) as exc_info:  # ValidationError or Pydantic error
            service.update_config(sample_config_id, updates)

        # Should fail validation - check that error is about scope/category validation
        error_msg = str(exc_info.value)
        assert ("configscope" in error_msg.lower() or "configcategory" in error_msg.lower())
        service.repository.update.assert_not_called()

    def test_update_config_repository_not_found(
        self,
        service: RuntimeConfigService,
        sample_config_id: UUID4,
        sample_config_output: RuntimeConfigOutput,
    ) -> None:
        """Test update_config handles repository returning None."""
        service.repository.get.return_value = sample_config_output
        service.repository.update.return_value = None

        with pytest.raises(NotFoundException):
            service.update_config(sample_config_id, {"description": "Updated"})

    # ============================================================================
    # DELETE OPERATIONS
    # ============================================================================

    def test_delete_config_success(
        self, service: RuntimeConfigService, sample_config_id: UUID4
    ) -> None:
        """Test successful configuration deletion."""
        service.repository.delete.return_value = True

        # Should not raise an exception
        service.delete_config(sample_config_id)

        service.repository.delete.assert_called_once_with(sample_config_id)

    def test_delete_config_not_found(
        self, service: RuntimeConfigService, sample_config_id: UUID4
    ) -> None:
        """Test delete_config raises NotFoundException when config not found."""
        service.repository.delete.return_value = False

        with pytest.raises(NotFoundException) as exc_info:
            service.delete_config(sample_config_id)

        assert exc_info.value.details["resource_type"] == "RuntimeConfig"
        service.repository.delete.assert_called_once_with(sample_config_id)

    # ============================================================================
    # TOGGLE OPERATIONS
    # ============================================================================

    def test_toggle_config_enable(
        self,
        service: RuntimeConfigService,
        sample_config_id: UUID4,
        sample_config_output: RuntimeConfigOutput,
    ) -> None:
        """Test successful configuration enable."""
        enabled_output = RuntimeConfigOutput(
            id=sample_config_id,
            scope=ConfigScope.GLOBAL,
            category=ConfigCategory.LLM,
            config_key="max_new_tokens",
            config_value={"value": 1024, "type": "int"},
            description="Global default token limit",
            is_active=True,  # Enabled
            user_id=None,
            collection_id=None,
            created_by=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.toggle_active.return_value = enabled_output

        result = service.toggle_config(sample_config_id, True)

        assert result.is_active is True
        service.repository.toggle_active.assert_called_once_with(sample_config_id, True)

    def test_toggle_config_disable(
        self,
        service: RuntimeConfigService,
        sample_config_id: UUID4,
    ) -> None:
        """Test successful configuration disable."""
        disabled_output = RuntimeConfigOutput(
            id=sample_config_id,
            scope=ConfigScope.GLOBAL,
            category=ConfigCategory.LLM,
            config_key="max_new_tokens",
            config_value={"value": 1024, "type": "int"},
            description="Global default token limit",
            is_active=False,  # Disabled
            user_id=None,
            collection_id=None,
            created_by=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.toggle_active.return_value = disabled_output

        result = service.toggle_config(sample_config_id, False)

        assert result.is_active is False
        service.repository.toggle_active.assert_called_once_with(sample_config_id, False)

    def test_toggle_config_not_found(
        self, service: RuntimeConfigService, sample_config_id: UUID4
    ) -> None:
        """Test toggle_config raises NotFoundException when config not found."""
        service.repository.toggle_active.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            service.toggle_config(sample_config_id, True)

        assert exc_info.value.details["resource_type"] == "RuntimeConfig"
        service.repository.toggle_active.assert_called_once_with(sample_config_id, True)

    # ============================================================================
    # LIST OPERATIONS
    # ============================================================================

    def test_list_user_configs_without_category(
        self, service: RuntimeConfigService, sample_user_id: UUID4
    ) -> None:
        """Test listing all user configurations without category filter."""
        config1 = RuntimeConfigOutput(
            id=uuid4(),
            scope=ConfigScope.USER,
            category=ConfigCategory.LLM,
            config_key="temperature",
            config_value={"value": 0.8, "type": "float"},
            description="User LLM config",
            is_active=True,
            user_id=sample_user_id,
            collection_id=None,
            created_by=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        config2 = RuntimeConfigOutput(
            id=uuid4(),
            scope=ConfigScope.USER,
            category=ConfigCategory.RETRIEVAL,
            config_key="top_k",
            config_value={"value": 10, "type": "int"},
            description="User retrieval config",
            is_active=True,
            user_id=sample_user_id,
            collection_id=None,
            created_by=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.get_all_for_user.return_value = [config1, config2]

        result = service.list_user_configs(sample_user_id)

        assert len(result) == 2
        assert result[0].category == ConfigCategory.LLM
        assert result[1].category == ConfigCategory.RETRIEVAL
        service.repository.get_all_for_user.assert_called_once_with(sample_user_id, None)

    def test_list_user_configs_with_category_filter(
        self, service: RuntimeConfigService, sample_user_id: UUID4
    ) -> None:
        """Test listing user configurations with category filter."""
        config = RuntimeConfigOutput(
            id=uuid4(),
            scope=ConfigScope.USER,
            category=ConfigCategory.LLM,
            config_key="temperature",
            config_value={"value": 0.8, "type": "float"},
            description="User LLM config",
            is_active=True,
            user_id=sample_user_id,
            collection_id=None,
            created_by=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.get_all_for_user.return_value = [config]

        result = service.list_user_configs(sample_user_id, ConfigCategory.LLM)

        assert len(result) == 1
        assert result[0].category == ConfigCategory.LLM
        service.repository.get_all_for_user.assert_called_once_with(sample_user_id, ConfigCategory.LLM)

    def test_list_collection_configs_without_category(
        self, service: RuntimeConfigService, sample_collection_id: UUID4
    ) -> None:
        """Test listing all collection configurations without category filter."""
        config1 = RuntimeConfigOutput(
            id=uuid4(),
            scope=ConfigScope.COLLECTION,
            category=ConfigCategory.LLM,
            config_key="temperature",
            config_value={"value": 0.9, "type": "float"},
            description="Collection LLM config",
            is_active=True,
            user_id=uuid4(),
            collection_id=sample_collection_id,
            created_by=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        service.repository.get_all_for_collection.return_value = [config1]

        result = service.list_collection_configs(sample_collection_id)

        assert len(result) == 1
        assert result[0].category == ConfigCategory.LLM
        service.repository.get_all_for_collection.assert_called_once_with(sample_collection_id, None)

    def test_list_collection_configs_with_category_filter(
        self, service: RuntimeConfigService, sample_collection_id: UUID4
    ) -> None:
        """Test listing collection configurations with category filter."""
        service.repository.get_all_for_collection.return_value = []

        result = service.list_collection_configs(sample_collection_id, ConfigCategory.CHUNKING)

        assert len(result) == 0
        service.repository.get_all_for_collection.assert_called_once_with(
            sample_collection_id, ConfigCategory.CHUNKING
        )

    def test_list_user_configs_empty(
        self, service: RuntimeConfigService, sample_user_id: UUID4
    ) -> None:
        """Test listing user configs when none exist."""
        service.repository.get_all_for_user.return_value = []

        result = service.list_user_configs(sample_user_id)

        assert len(result) == 0
        service.repository.get_all_for_user.assert_called_once_with(sample_user_id, None)

    def test_list_collection_configs_empty(
        self, service: RuntimeConfigService, sample_collection_id: UUID4
    ) -> None:
        """Test listing collection configs when none exist."""
        service.repository.get_all_for_collection.return_value = []

        result = service.list_collection_configs(sample_collection_id)

        assert len(result) == 0
        service.repository.get_all_for_collection.assert_called_once_with(sample_collection_id, None)
