"""Unit tests for runtime configuration schemas.

Tests the Pydantic schemas for runtime configuration including:
- Enum values
- Input validation
- Scope constraints
- Config value structure validation
- Type conversion in typed_value property
- EffectiveConfig functionality
"""

import uuid

import pytest
from pydantic import ValidationError

from rag_solution.schemas.runtime_config_schema import (
    ConfigCategory,
    ConfigScope,
    EffectiveConfig,
    RuntimeConfigInput,
    RuntimeConfigOutput,
)


class TestConfigEnums:
    """Test configuration enum values."""

    def test_config_scope_values(self) -> None:
        """Test ConfigScope enum has expected values."""
        assert ConfigScope.GLOBAL == "global"
        assert ConfigScope.USER == "user"
        assert ConfigScope.COLLECTION == "collection"

    def test_config_category_values(self) -> None:
        """Test ConfigCategory enum has expected values."""
        assert ConfigCategory.LLM == "llm"
        assert ConfigCategory.CHUNKING == "chunking"
        assert ConfigCategory.RETRIEVAL == "retrieval"
        assert ConfigCategory.EMBEDDING == "embedding"
        assert ConfigCategory.COT == "cot"
        assert ConfigCategory.RERANKING == "reranking"
        assert ConfigCategory.PODCAST == "podcast"
        assert ConfigCategory.QUESTION == "question"
        assert ConfigCategory.LOGGING == "logging"
        assert ConfigCategory.SYSTEM == "system"


class TestRuntimeConfigInput:
    """Test RuntimeConfigInput validation."""

    def test_valid_global_config(self) -> None:
        """Test creating valid GLOBAL scope configuration."""
        config = RuntimeConfigInput(
            scope=ConfigScope.GLOBAL,
            category=ConfigCategory.LLM,
            config_key="temperature",
            config_value={"value": 0.7, "type": "float"},
        )
        assert config.scope == ConfigScope.GLOBAL
        assert config.category == ConfigCategory.LLM
        assert config.config_key == "temperature"
        assert config.config_value == {"value": 0.7, "type": "float"}
        assert config.user_id is None
        assert config.collection_id is None
        assert config.is_active is True
        assert config.created_by is None

    def test_valid_user_config(self) -> None:
        """Test creating valid USER scope configuration."""
        user_id = uuid.uuid4()
        config = RuntimeConfigInput(
            scope=ConfigScope.USER,
            category=ConfigCategory.CHUNKING,
            config_key="chunk_size",
            config_value={"value": 512, "type": "int"},
            user_id=user_id,
        )
        assert config.scope == ConfigScope.USER
        assert config.user_id == user_id
        assert config.collection_id is None

    def test_valid_collection_config(self) -> None:
        """Test creating valid COLLECTION scope configuration."""
        user_id = uuid.uuid4()
        collection_id = uuid.uuid4()
        config = RuntimeConfigInput(
            scope=ConfigScope.COLLECTION,
            category=ConfigCategory.RETRIEVAL,
            config_key="top_k",
            config_value={"value": 10, "type": "int"},
            user_id=user_id,
            collection_id=collection_id,
        )
        assert config.scope == ConfigScope.COLLECTION
        assert config.user_id == user_id
        assert config.collection_id == collection_id

    def test_config_value_missing_value_key(self) -> None:
        """Test config_value validation fails without 'value' key."""
        with pytest.raises(ValidationError) as exc_info:
            RuntimeConfigInput(
                scope=ConfigScope.GLOBAL,
                category=ConfigCategory.LLM,
                config_key="temperature",
                config_value={"type": "float"},  # Missing 'value' key
            )
        assert "config_value must contain 'value' key" in str(exc_info.value)

    def test_config_value_missing_type_key(self) -> None:
        """Test config_value validation fails without 'type' key."""
        with pytest.raises(ValidationError) as exc_info:
            RuntimeConfigInput(
                scope=ConfigScope.GLOBAL,
                category=ConfigCategory.LLM,
                config_key="temperature",
                config_value={"value": 0.7},  # Missing 'type' key
            )
        assert "config_value must contain 'type' key" in str(exc_info.value)

    def test_config_value_invalid_type(self) -> None:
        """Test config_value validation fails with invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            RuntimeConfigInput(
                scope=ConfigScope.GLOBAL,
                category=ConfigCategory.LLM,
                config_key="temperature",
                config_value={"value": 0.7, "type": "invalid_type"},
            )
        assert "Invalid type" in str(exc_info.value)

    def test_config_key_too_long(self) -> None:
        """Test config_key validation fails when too long."""
        with pytest.raises(ValidationError) as exc_info:
            RuntimeConfigInput(
                scope=ConfigScope.GLOBAL,
                category=ConfigCategory.LLM,
                config_key="a" * 256,  # Exceeds max_length=255
                config_value={"value": 0.7, "type": "float"},
            )
        assert "String should have at most 255 characters" in str(exc_info.value)

    def test_description_too_long(self) -> None:
        """Test description validation fails when too long."""
        with pytest.raises(ValidationError) as exc_info:
            RuntimeConfigInput(
                scope=ConfigScope.GLOBAL,
                category=ConfigCategory.LLM,
                config_key="temperature",
                config_value={"value": 0.7, "type": "float"},
                description="a" * 1025,  # Exceeds max_length=1024
            )
        assert "String should have at most 1024 characters" in str(exc_info.value)

    def test_all_value_types(self) -> None:
        """Test config_value accepts all valid types."""
        valid_types = [
            {"value": 42, "type": "int"},
            {"value": 3.14, "type": "float"},
            {"value": "hello", "type": "str"},
            {"value": True, "type": "bool"},
            {"value": [1, 2, 3], "type": "list"},
            {"value": {"key": "value"}, "type": "dict"},
        ]
        for config_value in valid_types:
            config = RuntimeConfigInput(
                scope=ConfigScope.GLOBAL,
                category=ConfigCategory.LLM,
                config_key="test_key",
                config_value=config_value,
            )
            assert config.config_value == config_value


class TestRuntimeConfigOutput:
    """Test RuntimeConfigOutput functionality."""

    def test_typed_value_int(self) -> None:
        """Test typed_value property returns int correctly."""
        output = RuntimeConfigOutput(
            id=uuid.uuid4(),
            scope=ConfigScope.GLOBAL,
            category=ConfigCategory.LLM,
            config_key="max_tokens",
            config_value={"value": 1024, "type": "int"},
            is_active=True,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert output.typed_value == 1024
        assert isinstance(output.typed_value, int)

    def test_typed_value_float(self) -> None:
        """Test typed_value property returns float correctly."""
        output = RuntimeConfigOutput(
            id=uuid.uuid4(),
            scope=ConfigScope.GLOBAL,
            category=ConfigCategory.LLM,
            config_key="temperature",
            config_value={"value": 0.7, "type": "float"},
            is_active=True,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert output.typed_value == 0.7
        assert isinstance(output.typed_value, float)

    def test_typed_value_str(self) -> None:
        """Test typed_value property returns str correctly."""
        output = RuntimeConfigOutput(
            id=uuid.uuid4(),
            scope=ConfigScope.GLOBAL,
            category=ConfigCategory.LLM,
            config_key="model_name",
            config_value={"value": "gpt-4", "type": "str"},
            is_active=True,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert output.typed_value == "gpt-4"
        assert isinstance(output.typed_value, str)

    def test_typed_value_bool(self) -> None:
        """Test typed_value property returns bool correctly."""
        output = RuntimeConfigOutput(
            id=uuid.uuid4(),
            scope=ConfigScope.GLOBAL,
            category=ConfigCategory.COT,
            config_key="enabled",
            config_value={"value": True, "type": "bool"},
            is_active=True,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert output.typed_value is True
        assert isinstance(output.typed_value, bool)

    def test_typed_value_list(self) -> None:
        """Test typed_value property returns list correctly."""
        output = RuntimeConfigOutput(
            id=uuid.uuid4(),
            scope=ConfigScope.GLOBAL,
            category=ConfigCategory.QUESTION,
            config_key="question_types",
            config_value={"value": ["What", "How", "Why"], "type": "list"},
            is_active=True,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert output.typed_value == ["What", "How", "Why"]
        assert isinstance(output.typed_value, list)

    def test_typed_value_dict(self) -> None:
        """Test typed_value property returns dict correctly."""
        output = RuntimeConfigOutput(
            id=uuid.uuid4(),
            scope=ConfigScope.GLOBAL,
            category=ConfigCategory.LLM,
            config_key="advanced_params",
            config_value={"value": {"key1": "value1", "key2": 42}, "type": "dict"},
            is_active=True,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        assert output.typed_value == {"key1": "value1", "key2": 42}
        assert isinstance(output.typed_value, dict)

    def test_typed_value_none(self) -> None:
        """Test typed_value property raises error for None value."""
        output = RuntimeConfigOutput(
            id=uuid.uuid4(),
            scope=ConfigScope.GLOBAL,
            category=ConfigCategory.LLM,
            config_key="optional_param",
            config_value={"value": None, "type": "str"},
            is_active=True,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        with pytest.raises(ValueError) as exc_info:
            _ = output.typed_value
        assert "config_value['value'] cannot be None" in str(exc_info.value)


class TestEffectiveConfig:
    """Test EffectiveConfig functionality."""

    def test_effective_config_creation(self) -> None:
        """Test creating EffectiveConfig with values and sources."""
        config = EffectiveConfig(
            category=ConfigCategory.LLM,
            values={"temperature": 0.7, "max_new_tokens": 1024},
            sources={"temperature": "user", "max_new_tokens": "settings"},
        )
        assert config.category == ConfigCategory.LLM
        assert config.values == {"temperature": 0.7, "max_new_tokens": 1024}
        assert config.sources == {"temperature": "user", "max_new_tokens": "settings"}

    def test_effective_config_get_existing_key(self) -> None:
        """Test get() method returns value for existing key."""
        config = EffectiveConfig(
            category=ConfigCategory.LLM,
            values={"temperature": 0.7, "max_new_tokens": 1024},
            sources={"temperature": "user", "max_new_tokens": "settings"},
        )
        assert config.get("temperature") == 0.7
        assert config.get("max_new_tokens") == 1024

    def test_effective_config_get_missing_key_no_default(self) -> None:
        """Test get() method returns None for missing key without default."""
        config = EffectiveConfig(
            category=ConfigCategory.LLM,
            values={"temperature": 0.7},
            sources={"temperature": "user"},
        )
        assert config.get("missing_key") is None

    def test_effective_config_get_missing_key_with_default(self) -> None:
        """Test get() method returns default for missing key."""
        config = EffectiveConfig(
            category=ConfigCategory.LLM,
            values={"temperature": 0.7},
            sources={"temperature": "user"},
        )
        assert config.get("missing_key", default="default_value") == "default_value"
        assert config.get("missing_key", default=42) == 42

    def test_effective_config_empty_values(self) -> None:
        """Test EffectiveConfig with empty values dict."""
        config = EffectiveConfig(
            category=ConfigCategory.LLM,
            values={},
            sources={},
        )
        assert config.values == {}
        assert config.sources == {}
        assert config.get("any_key") is None
        assert config.get("any_key", default="fallback") == "fallback"
