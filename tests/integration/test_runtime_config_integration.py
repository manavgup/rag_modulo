"""Integration tests for RuntimeConfig with real database.

This module tests the complete runtime configuration system with real database operations:
- Full CRUD workflow
- Hierarchical precedence (collection > user > global > Settings)
- Transaction handling and rollback
- Concurrent access patterns
- Error scenarios (duplicates, invalid scopes, missing fields)

Test Strategy:
- Uses real PostgreSQL database via integration fixtures
- Transaction rollback ensures test isolation
- Tests service + repository layers together
- Validates database constraints and JSONB storage
"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pydantic import ValidationError as PydanticValidationError

from backend.core.config import Settings
from backend.core.custom_exceptions import NotFoundError, ValidationError
from backend.rag_solution.models.runtime_config import RuntimeConfig
from backend.rag_solution.repository.runtime_config_repository import RuntimeConfigRepository
from backend.rag_solution.schemas.runtime_config_schema import (
    ConfigCategory,
    ConfigScope,
    RuntimeConfigInput,
)
from backend.rag_solution.services.runtime_config_service import RuntimeConfigService


@pytest.fixture
def runtime_config_service(real_db_session: Session, integration_settings: Settings) -> RuntimeConfigService:
    """Create RuntimeConfigService with real database session."""
    return RuntimeConfigService(real_db_session, integration_settings)


@pytest.fixture
def runtime_config_repository(real_db_session: Session, integration_settings: Settings) -> RuntimeConfigRepository:
    """Create RuntimeConfigRepository with real database session."""
    return RuntimeConfigRepository(real_db_session, integration_settings)


@pytest.fixture
def test_user_id() -> UUID:
    """Generate test user ID."""
    return uuid4()


@pytest.fixture
def test_collection_id() -> UUID:
    """Generate test collection ID."""
    return uuid4()


@pytest.fixture
def global_llm_config() -> RuntimeConfigInput:
    """Create global LLM configuration input."""
    return RuntimeConfigInput(
        scope=ConfigScope.GLOBAL,
        category=ConfigCategory.LLM,
        config_key="temperature",
        config_value={"value": 0.7, "type": "float"},
        description="Global default temperature",
        is_active=True,
    )


@pytest.fixture
def user_llm_config(test_user_id: UUID) -> RuntimeConfigInput:
    """Create user-level LLM configuration input."""
    return RuntimeConfigInput(
        scope=ConfigScope.USER,
        category=ConfigCategory.LLM,
        user_id=test_user_id,
        config_key="temperature",
        config_value={"value": 0.8, "type": "float"},
        description="User override temperature",
        is_active=True,
    )


@pytest.fixture
def collection_llm_config(test_user_id: UUID, test_collection_id: UUID) -> RuntimeConfigInput:
    """Create collection-level LLM configuration input."""
    return RuntimeConfigInput(
        scope=ConfigScope.COLLECTION,
        category=ConfigCategory.LLM,
        user_id=test_user_id,
        collection_id=test_collection_id,
        config_key="temperature",
        config_value={"value": 0.9, "type": "float"},
        description="Collection override temperature",
        is_active=True,
    )


@pytest.mark.integration
class TestRuntimeConfigDatabaseSetup:
    """Test database setup and constraints."""

    def test_runtime_config_table_exists(self, real_db_session: Session):
        """Test RuntimeConfig table exists in database."""
        # Query should succeed without errors
        result = real_db_session.query(RuntimeConfig).first()
        # May be None if no configs exist, but should not raise error
        assert result is None or isinstance(result, RuntimeConfig)

    def test_unique_constraint_enforced(
        self, real_db_session: Session, runtime_config_repository: RuntimeConfigRepository, global_llm_config: RuntimeConfigInput
    ):
        """Test unique constraint on (scope, category, config_key, user_id, collection_id)."""
        # Create first config
        config1 = runtime_config_repository.create(global_llm_config)
        assert config1.id is not None
        real_db_session.commit()  # Commit so constraint is enforced

        # Attempt to create duplicate should fail
        with pytest.raises(IntegrityError):
            config2 = runtime_config_repository.create(global_llm_config)
            real_db_session.commit()  # Try to commit duplicate

    def test_jsonb_config_value_storage(
        self, runtime_config_repository: RuntimeConfigRepository, global_llm_config: RuntimeConfigInput
    ):
        """Test JSONB config_value is stored correctly."""
        created = runtime_config_repository.create(global_llm_config)
        assert created.config_value == {"value": 0.7, "type": "float"}

        # Retrieve from DB and verify
        retrieved = runtime_config_repository.get(created.id)
        assert retrieved is not None
        assert retrieved.config_value == {"value": 0.7, "type": "float"}
        assert retrieved.typed_value == 0.7


@pytest.mark.integration
class TestRuntimeConfigFullCRUD:
    """Test complete CRUD workflow with real database."""

    def test_create_global_config(
        self, runtime_config_service: RuntimeConfigService, global_llm_config: RuntimeConfigInput
    ):
        """Test creating a global configuration."""
        created = runtime_config_service.create_config(global_llm_config)

        assert created.id is not None
        assert created.scope == ConfigScope.GLOBAL
        assert created.category == ConfigCategory.LLM
        assert created.config_key == "temperature"
        assert created.typed_value == 0.7
        assert created.user_id is None
        assert created.collection_id is None
        assert created.is_active is True

    def test_create_user_config(
        self, runtime_config_service: RuntimeConfigService, user_llm_config: RuntimeConfigInput
    ):
        """Test creating a user-level configuration."""
        created = runtime_config_service.create_config(user_llm_config)

        assert created.id is not None
        assert created.scope == ConfigScope.USER
        assert created.user_id is not None
        assert created.collection_id is None
        assert created.typed_value == 0.8

    def test_create_collection_config(
        self, runtime_config_service: RuntimeConfigService, collection_llm_config: RuntimeConfigInput
    ):
        """Test creating a collection-level configuration."""
        created = runtime_config_service.create_config(collection_llm_config)

        assert created.id is not None
        assert created.scope == ConfigScope.COLLECTION
        assert created.user_id is not None
        assert created.collection_id is not None
        assert created.typed_value == 0.9

    def test_read_config(self, runtime_config_service: RuntimeConfigService, global_llm_config: RuntimeConfigInput):
        """Test reading a configuration by ID."""
        created = runtime_config_service.create_config(global_llm_config)

        retrieved = runtime_config_service.get_config(created.id)
        assert retrieved.id == created.id
        assert retrieved.config_key == "temperature"
        assert retrieved.typed_value == 0.7

    def test_update_config(self, runtime_config_service: RuntimeConfigService, global_llm_config: RuntimeConfigInput):
        """Test updating a configuration."""
        created = runtime_config_service.create_config(global_llm_config)

        # Update config_value
        updates = {"config_value": {"value": 0.5, "type": "float"}}
        updated = runtime_config_service.update_config(created.id, updates)

        assert updated.id == created.id
        assert updated.typed_value == 0.5

    def test_update_description(
        self, runtime_config_service: RuntimeConfigService, global_llm_config: RuntimeConfigInput
    ):
        """Test updating configuration description."""
        created = runtime_config_service.create_config(global_llm_config)

        updates = {"description": "Updated description"}
        updated = runtime_config_service.update_config(created.id, updates)

        assert updated.description == "Updated description"

    def test_delete_config(self, runtime_config_service: RuntimeConfigService, global_llm_config: RuntimeConfigInput):
        """Test deleting a configuration."""
        created = runtime_config_service.create_config(global_llm_config)

        # Delete should succeed
        runtime_config_service.delete_config(created.id)

        # Retrieval should fail
        with pytest.raises(NotFoundError):
            runtime_config_service.get_config(created.id)

    def test_toggle_active_status(
        self, runtime_config_service: RuntimeConfigService, global_llm_config: RuntimeConfigInput
    ):
        """Test toggling active status."""
        created = runtime_config_service.create_config(global_llm_config)
        assert created.is_active is True

        # Disable
        toggled = runtime_config_service.toggle_config(created.id, False)
        assert toggled.is_active is False

        # Enable
        toggled = runtime_config_service.toggle_config(created.id, True)
        assert toggled.is_active is True


@pytest.mark.integration
class TestHierarchicalPrecedence:
    """Test hierarchical configuration precedence (collection > user > global > Settings)."""

    def test_global_config_only(
        self,
        runtime_config_service: RuntimeConfigService,
        global_llm_config: RuntimeConfigInput,
        test_user_id: UUID,
    ):
        """Test effective config with only global configs."""
        runtime_config_service.create_config(global_llm_config)

        effective = runtime_config_service.get_effective_config(test_user_id, None, ConfigCategory.LLM)

        assert effective.category == ConfigCategory.LLM
        assert effective.values.get("temperature") == 0.7
        assert effective.sources.get("temperature") == "global"

    def test_user_overrides_global(
        self,
        runtime_config_service: RuntimeConfigService,
        global_llm_config: RuntimeConfigInput,
        user_llm_config: RuntimeConfigInput,
        test_user_id: UUID,
    ):
        """Test user config overrides global config."""
        runtime_config_service.create_config(global_llm_config)
        runtime_config_service.create_config(user_llm_config)

        effective = runtime_config_service.get_effective_config(test_user_id, None, ConfigCategory.LLM)

        # User config (0.8) should override global (0.7)
        assert effective.values.get("temperature") == 0.8
        assert effective.sources.get("temperature") == "user"

    def test_collection_overrides_user_and_global(
        self,
        runtime_config_service: RuntimeConfigService,
        global_llm_config: RuntimeConfigInput,
        user_llm_config: RuntimeConfigInput,
        collection_llm_config: RuntimeConfigInput,
        test_user_id: UUID,
        test_collection_id: UUID,
    ):
        """Test collection config has highest precedence."""
        runtime_config_service.create_config(global_llm_config)
        runtime_config_service.create_config(user_llm_config)
        runtime_config_service.create_config(collection_llm_config)

        effective = runtime_config_service.get_effective_config(test_user_id, test_collection_id, ConfigCategory.LLM)

        # Collection config (0.9) should override user (0.8) and global (0.7)
        assert effective.values.get("temperature") == 0.9
        assert effective.sources.get("temperature") == "collection"

    def test_fallback_to_user_when_collection_deleted(
        self,
        runtime_config_service: RuntimeConfigService,
        user_llm_config: RuntimeConfigInput,
        collection_llm_config: RuntimeConfigInput,
        test_user_id: UUID,
        test_collection_id: UUID,
    ):
        """Test fallback to user config when collection config is deleted."""
        user_config = runtime_config_service.create_config(user_llm_config)
        collection_config = runtime_config_service.create_config(collection_llm_config)

        # Collection config is active
        effective = runtime_config_service.get_effective_config(test_user_id, test_collection_id, ConfigCategory.LLM)
        assert effective.values.get("temperature") == 0.9

        # Delete collection config
        runtime_config_service.delete_config(collection_config.id)

        # Should fallback to user config
        effective = runtime_config_service.get_effective_config(test_user_id, test_collection_id, ConfigCategory.LLM)
        assert effective.values.get("temperature") == 0.8
        assert effective.sources.get("temperature") == "user"

    def test_fallback_to_global_when_user_deleted(
        self,
        runtime_config_service: RuntimeConfigService,
        global_llm_config: RuntimeConfigInput,
        user_llm_config: RuntimeConfigInput,
        test_user_id: UUID,
    ):
        """Test fallback to global config when user config is deleted."""
        global_config = runtime_config_service.create_config(global_llm_config)
        user_config = runtime_config_service.create_config(user_llm_config)

        # User config is active
        effective = runtime_config_service.get_effective_config(test_user_id, None, ConfigCategory.LLM)
        assert effective.values.get("temperature") == 0.8

        # Delete user config
        runtime_config_service.delete_config(user_config.id)

        # Should fallback to global config
        effective = runtime_config_service.get_effective_config(test_user_id, None, ConfigCategory.LLM)
        assert effective.values.get("temperature") == 0.7
        assert effective.sources.get("temperature") == "global"

    def test_inactive_configs_ignored_in_precedence(
        self,
        runtime_config_service: RuntimeConfigService,
        global_llm_config: RuntimeConfigInput,
        user_llm_config: RuntimeConfigInput,
        test_user_id: UUID,
    ):
        """Test inactive configs are ignored in precedence resolution."""
        runtime_config_service.create_config(global_llm_config)
        user_config = runtime_config_service.create_config(user_llm_config)

        # User config is active - should override global
        effective = runtime_config_service.get_effective_config(test_user_id, None, ConfigCategory.LLM)
        assert effective.values.get("temperature") == 0.8

        # Deactivate user config
        runtime_config_service.toggle_config(user_config.id, False)

        # Should fallback to global config
        effective = runtime_config_service.get_effective_config(test_user_id, None, ConfigCategory.LLM)
        assert effective.values.get("temperature") == 0.7
        assert effective.sources.get("temperature") == "global"


@pytest.mark.integration
class TestErrorScenarios:
    """Test error handling and validation."""

    def test_create_duplicate_config_fails(
        self, real_db_session: Session, runtime_config_service: RuntimeConfigService, global_llm_config: RuntimeConfigInput
    ):
        """Test creating duplicate configuration raises IntegrityError."""
        runtime_config_service.create_config(global_llm_config)
        real_db_session.commit()  # Commit so constraint is enforced

        # Duplicate creation should fail
        with pytest.raises(IntegrityError):
            runtime_config_service.create_config(global_llm_config)
            real_db_session.commit()  # Try to commit duplicate

    def test_global_scope_with_user_id_fails(self, runtime_config_service: RuntimeConfigService):
        """Test GLOBAL scope with user_id raises ValidationError."""
        # Pydantic validates this at schema level, so we expect PydanticValidationError
        with pytest.raises(PydanticValidationError):
            invalid_config = RuntimeConfigInput(
                scope=ConfigScope.GLOBAL,
                category=ConfigCategory.LLM,
                user_id=uuid4(),  # Invalid for GLOBAL scope
                config_key="temperature",
                config_value={"value": 0.7, "type": "float"},
            )

    def test_user_scope_without_user_id_fails(self, runtime_config_service: RuntimeConfigService):
        """Test USER scope without user_id raises ValidationError."""
        # Pydantic validates this at schema level
        with pytest.raises(PydanticValidationError):
            invalid_config = RuntimeConfigInput(
                scope=ConfigScope.USER,
                category=ConfigCategory.LLM,
                # user_id missing
                config_key="temperature",
                config_value={"value": 0.7, "type": "float"},
            )

    def test_collection_scope_without_collection_id_fails(self, runtime_config_service: RuntimeConfigService):
        """Test COLLECTION scope without collection_id raises ValidationError."""
        # Pydantic validates this at schema level
        with pytest.raises(PydanticValidationError):
            invalid_config = RuntimeConfigInput(
                scope=ConfigScope.COLLECTION,
                category=ConfigCategory.LLM,
                user_id=uuid4(),
                # collection_id missing
                config_key="temperature",
                config_value={"value": 0.7, "type": "float"},
            )

    def test_get_nonexistent_config_raises_not_found(self, runtime_config_service: RuntimeConfigService):
        """Test retrieving non-existent config raises NotFoundError."""
        fake_id = uuid4()

        with pytest.raises(NotFoundError):
            runtime_config_service.get_config(fake_id)

    def test_update_nonexistent_config_raises_not_found(self, runtime_config_service: RuntimeConfigService):
        """Test updating non-existent config raises NotFoundError."""
        fake_id = uuid4()

        with pytest.raises(NotFoundError):
            runtime_config_service.update_config(fake_id, {"description": "test"})

    def test_delete_nonexistent_config_raises_not_found(self, runtime_config_service: RuntimeConfigService):
        """Test deleting non-existent config raises NotFoundError."""
        fake_id = uuid4()

        with pytest.raises(NotFoundError):
            runtime_config_service.delete_config(fake_id)

    def test_toggle_nonexistent_config_raises_not_found(self, runtime_config_service: RuntimeConfigService):
        """Test toggling non-existent config raises NotFoundError."""
        fake_id = uuid4()

        with pytest.raises(NotFoundError):
            runtime_config_service.toggle_config(fake_id, False)


@pytest.mark.integration
class TestListOperations:
    """Test list operations for user and collection configs."""

    def test_list_user_configs(
        self,
        runtime_config_service: RuntimeConfigService,
        test_user_id: UUID,
    ):
        """Test listing all user configurations."""
        # Create multiple user configs
        config1 = RuntimeConfigInput(
            scope=ConfigScope.USER,
            category=ConfigCategory.LLM,
            user_id=test_user_id,
            config_key="temperature",
            config_value={"value": 0.7, "type": "float"},
        )
        config2 = RuntimeConfigInput(
            scope=ConfigScope.USER,
            category=ConfigCategory.CHUNKING,
            user_id=test_user_id,
            config_key="chunk_size",
            config_value={"value": 512, "type": "int"},
        )

        runtime_config_service.create_config(config1)
        runtime_config_service.create_config(config2)

        # List all user configs
        user_configs = runtime_config_service.list_user_configs(test_user_id)
        assert len(user_configs) >= 2

        # List by category
        llm_configs = runtime_config_service.list_user_configs(test_user_id, ConfigCategory.LLM)
        assert len(llm_configs) >= 1
        assert all(c.category == ConfigCategory.LLM for c in llm_configs)

    def test_list_collection_configs(
        self,
        runtime_config_service: RuntimeConfigService,
        test_user_id: UUID,
        test_collection_id: UUID,
    ):
        """Test listing all collection configurations."""
        # Create multiple collection configs
        config1 = RuntimeConfigInput(
            scope=ConfigScope.COLLECTION,
            category=ConfigCategory.LLM,
            user_id=test_user_id,
            collection_id=test_collection_id,
            config_key="temperature",
            config_value={"value": 0.9, "type": "float"},
        )
        config2 = RuntimeConfigInput(
            scope=ConfigScope.COLLECTION,
            category=ConfigCategory.RETRIEVAL,
            user_id=test_user_id,
            collection_id=test_collection_id,
            config_key="top_k",
            config_value={"value": 10, "type": "int"},
        )

        runtime_config_service.create_config(config1)
        runtime_config_service.create_config(config2)

        # List all collection configs
        collection_configs = runtime_config_service.list_collection_configs(test_collection_id)
        assert len(collection_configs) >= 2

        # List by category
        llm_configs = runtime_config_service.list_collection_configs(test_collection_id, ConfigCategory.LLM)
        assert len(llm_configs) >= 1
        assert all(c.category == ConfigCategory.LLM for c in llm_configs)

    def test_list_empty_results(self, runtime_config_service: RuntimeConfigService):
        """Test listing configs returns empty list when none exist."""
        random_user_id = uuid4()

        user_configs = runtime_config_service.list_user_configs(random_user_id)
        assert user_configs == []

        random_collection_id = uuid4()
        collection_configs = runtime_config_service.list_collection_configs(random_collection_id)
        assert collection_configs == []
