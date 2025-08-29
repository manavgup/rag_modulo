"""Integration tests for LLMModelService."""

from uuid import uuid4

import pytest

from core.custom_exceptions import ModelConfigError, ModelValidationError
from rag_solution.schemas.llm_model_schema import LLMModelOutput, ModelType


# -------------------------------------------
# 🧪 Model Creation Tests
# -------------------------------------------
def test_create_model(llm_model_service, base_provider_input, base_model_input, ensure_watsonx_provider):
    """Test model creation."""
    provider = ensure_watsonx_provider
    base_model_input.provider_id = provider.id

    model = llm_model_service.create_model(base_model_input)

    assert isinstance(model, LLMModelOutput)
    assert model.provider_id == provider.id
    assert model.model_id == base_model_input.model_id
    assert model.model_type == base_model_input.model_type
    assert model.is_default == base_model_input.is_default


def test_create_model_with_invalid_provider(llm_model_service, base_model_input):
    """Test model creation with invalid provider ID."""
    base_model_input.provider_id = uuid4()  # Non-existent provider

    with pytest.raises(ModelConfigError) as exc_info:
        llm_model_service.create_model(base_model_input)
    assert "provider_id" in str(exc_info.value)


def test_create_model_validation(llm_model_service, base_model_input, ensure_watsonx_provider):
    """Test model input validation."""
    provider = ensure_watsonx_provider
    base_model_input.provider_id = provider.id

    # Test invalid timeout
    with pytest.raises(ModelValidationError) as exc_info:
        invalid_model = base_model_input.model_copy(update={"timeout": 0})
        llm_model_service.create_model(invalid_model)
    assert "timeout" in str(exc_info.value)

    # Test invalid max_retries
    with pytest.raises(ModelValidationError) as exc_info:
        invalid_model = base_model_input.model_copy(update={"max_retries": -1})
        llm_model_service.create_model(invalid_model)
    assert "max_retries" in str(exc_info.value)


# -------------------------------------------
# 🧪 Model Retrieval Tests
# -------------------------------------------
def test_get_model_by_id(llm_model_service, base_model_input, ensure_watsonx_provider):
    """Test getting model by ID."""
    provider = ensure_watsonx_provider
    base_model_input.provider_id = provider.id
    created = llm_model_service.create_model(base_model_input)

    model = llm_model_service.get_model_by_id(created.id)
    assert model is not None
    assert model.id == created.id
    assert model.model_id == created.model_id

    # Test nonexistent ID
    model = llm_model_service.get_model_by_id(uuid4())
    assert model is None


def test_get_models_by_provider(llm_model_service, base_model_input, ensure_watsonx_provider):
    """Test getting models by provider."""
    provider = ensure_watsonx_provider
    base_model_input.provider_id = provider.id

    # Create two models
    model1 = llm_model_service.create_model(base_model_input)
    model2 = llm_model_service.create_model(base_model_input.model_copy(update={"model_id": "another-model"}))

    models = llm_model_service.get_models_by_provider(provider.id)
    assert len(models) >= 2
    model_ids = {m.id for m in models}
    assert model1.id in model_ids
    assert model2.id in model_ids


def test_get_models_by_type(llm_model_service, base_model_input, ensure_watsonx_provider):
    """Test getting models by type."""
    provider = ensure_watsonx_provider
    base_model_input.provider_id = provider.id

    # Create models with different types
    gen_model = llm_model_service.create_model(base_model_input.model_copy(update={"model_type": ModelType.GENERATION}))
    embed_model = llm_model_service.create_model(
        base_model_input.model_copy(update={"model_id": "embedding-model", "model_type": ModelType.EMBEDDING})
    )

    # Get generation models
    gen_models = llm_model_service.get_models_by_type(ModelType.GENERATION)
    assert any(m.id == gen_model.id for m in gen_models)
    assert not any(m.id == embed_model.id for m in gen_models)

    # Get embedding models
    embed_models = llm_model_service.get_models_by_type(ModelType.EMBEDDING)
    assert any(m.id == embed_model.id for m in embed_models)
    assert not any(m.id == gen_model.id for m in embed_models)


# -------------------------------------------
# 🧪 Default Model Tests
# -------------------------------------------
def test_set_default_model(llm_model_service, base_model_input, ensure_watsonx_provider):
    """Test setting model as default."""
    provider = ensure_watsonx_provider
    base_model_input.provider_id = provider.id

    # Create two models
    model1 = llm_model_service.create_model(base_model_input.model_copy(update={"is_default": False}))
    model2 = llm_model_service.create_model(
        base_model_input.model_copy(update={"model_id": "model2", "is_default": False})
    )

    # Set model1 as default
    updated = llm_model_service.set_default_model(model1.id)
    assert updated.is_default is True

    # Check that model2 is not default
    model2_check = llm_model_service.get_model_by_id(model2.id)
    assert model2_check.is_default is False


def test_get_default_model(llm_model_service, base_model_input, ensure_watsonx_provider):
    """Test getting default model for provider and type."""
    provider = ensure_watsonx_provider
    base_model_input.provider_id = provider.id

    # Create default model
    model = llm_model_service.create_model(base_model_input.model_copy(update={"is_default": True}))

    # Get default model
    default = llm_model_service.get_default_model(provider.id, base_model_input.model_type)
    assert default is not None
    assert default.id == model.id
    assert default.is_default is True


# -------------------------------------------
# 🧪 Model Update Tests
# -------------------------------------------
def test_update_model(llm_model_service, base_model_input, ensure_watsonx_provider):
    """Test updating model."""
    provider = ensure_watsonx_provider
    base_model_input.provider_id = provider.id
    model = llm_model_service.create_model(base_model_input)

    updates = {"timeout": 60, "max_retries": 5, "is_active": False}

    updated = llm_model_service.update_model(model.id, updates)
    assert updated is not None
    assert updated.timeout == 60
    assert updated.max_retries == 5
    assert updated.is_active is False


# -------------------------------------------
# 🧪 Model Deletion Tests
# -------------------------------------------
def test_delete_model(llm_model_service, base_model_input, ensure_watsonx_provider):
    """Test model deletion."""
    provider = ensure_watsonx_provider
    base_model_input.provider_id = provider.id
    model = llm_model_service.create_model(base_model_input)

    # Delete model
    result = llm_model_service.delete_model(model.id)
    assert result is True

    # Verify deletion
    deleted_model = llm_model_service.get_model_by_id(model.id)
    assert deleted_model is None


def test_delete_nonexistent_model(llm_model_service):
    """Test deleting non-existent model."""
    result = llm_model_service.delete_model(uuid4())
    assert result is False


# -------------------------------------------
# 🧪 Model Configuration Tests
# -------------------------------------------
def test_model_runtime_settings(llm_model_service, base_model_input, ensure_watsonx_provider):
    """Test model runtime settings configuration."""
    provider = ensure_watsonx_provider
    base_model_input.provider_id = provider.id

    # Test different runtime configurations
    configurations = [
        {
            "timeout": 45,
            "max_retries": 5,
            "batch_size": 20,
            "retry_delay": 2.0,
            "concurrency_limit": 15,
            "stream": True,
            "rate_limit": 20,
        },
        {
            "timeout": 60,
            "max_retries": 3,
            "batch_size": 5,
            "retry_delay": 0.5,
            "concurrency_limit": 5,
            "stream": False,
            "rate_limit": 5,
        },
    ]

    for config in configurations:
        model_input = base_model_input.model_copy(update=config)
        model = llm_model_service.create_model(model_input)

        assert model.timeout == config["timeout"]
        assert model.max_retries == config["max_retries"]
        assert model.batch_size == config["batch_size"]
        assert model.retry_delay == config["retry_delay"]
        assert model.concurrency_limit == config["concurrency_limit"]
        assert model.stream == config["stream"]
        assert model.rate_limit == config["rate_limit"]


def test_model_type_specific_settings(llm_model_service, base_model_input, ensure_watsonx_provider):
    """Test settings specific to different model types."""
    provider = ensure_watsonx_provider
    base_model_input.provider_id = provider.id

    # Test generation model settings
    gen_model = llm_model_service.create_model(
        base_model_input.model_copy(
            update={
                "model_type": ModelType.GENERATION,
                "model_id": "generation-model",
                "stream": True,  # Streaming typically used for generation
            }
        )
    )
    assert gen_model.model_type == ModelType.GENERATION
    assert gen_model.stream is True

    # Test embedding model settings
    embed_model = llm_model_service.create_model(
        base_model_input.model_copy(
            update={
                "model_type": ModelType.EMBEDDING,
                "model_id": "embedding-model",
                "batch_size": 32,  # Larger batch size for embeddings
                "stream": False,  # Streaming not used for embeddings
            }
        )
    )
    assert embed_model.model_type == ModelType.EMBEDDING
    assert embed_model.batch_size == 32
    assert embed_model.stream is False


def test_model_state_transitions(llm_model_service, base_model_input, ensure_watsonx_provider):
    """Test model state transitions (active/inactive, default/non-default)."""
    provider = ensure_watsonx_provider
    base_model_input.provider_id = provider.id

    # Create initial model
    model = llm_model_service.create_model(base_model_input.model_copy(update={"is_active": True, "is_default": False}))

    # Test deactivation
    updated = llm_model_service.update_model(model.id, {"is_active": False})
    assert updated.is_active is False

    # Test setting as default
    updated = llm_model_service.set_default_model(model.id)
    assert updated.is_default is True

    # Test reactivation
    updated = llm_model_service.update_model(model.id, {"is_active": True})
    assert updated.is_active is True
    assert updated.is_default is True  # Should maintain default status


def test_multiple_models_same_provider(llm_model_service, base_model_input, ensure_watsonx_provider):
    """Test handling multiple models for the same provider."""
    provider = ensure_watsonx_provider
    base_model_input.provider_id = provider.id

    # Create multiple models
    models = []
    for i in range(3):
        model_input = base_model_input.model_copy(
            update={
                "model_id": f"model-{i}",
                "is_default": i == 0,  # First model is default
            }
        )
        model = llm_model_service.create_model(model_input)
        models.append(model)

    # Verify models
    provider_models = llm_model_service.get_models_by_provider(provider.id)
    assert len(provider_models) >= 3

    # Verify only one default
    default_models = [m for m in provider_models if m.is_default]
    assert len(default_models) == 1
    assert default_models[0].id == models[0].id


if __name__ == "__main__":
    pytest.main([__file__])
