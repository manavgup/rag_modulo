"""Tests for PromptTemplateService."""

from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from core.custom_exceptions import NotFoundError, ValidationError
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateOutput, PromptTemplateType
from rag_solution.services.prompt_template_service import PromptTemplateService, _template_to_dict


@pytest.fixture
def db_session():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def template_service(db_session):
    """Create a PromptTemplateService instance."""
    return PromptTemplateService(db_session)


@pytest.fixture
def sample_user_id():
    """Create a sample user ID."""
    return uuid4()


@pytest.fixture
def sample_template_input():
    """Create a sample template input."""
    return PromptTemplateInput(
        name="test-template",
        provider="watsonx",
        template_type=PromptTemplateType.RAG_QUERY,
        system_prompt="You are a helpful assistant.",
        template_format="{context}\n\n{question}",
        input_variables={"context": "Context for the question", "question": "User's question"},
        example_inputs={"context": "Sample context", "question": "Sample question"},
        is_default=True,
        validation_schema={
            "model": "PromptVariables",
            "fields": {"context": {"type": "str", "min_length": 1}, "question": {"type": "str", "min_length": 1}},
            "required": ["context", "question"],
        },
    )


@pytest.fixture
def sample_template_model(sample_user_id, sample_template_input):
    """Create a sample template model."""
    return PromptTemplate(
        id=uuid4(),
        user_id=sample_user_id,
        name=sample_template_input.name,
        provider=sample_template_input.provider,
        template_type=sample_template_input.template_type,
        system_prompt=sample_template_input.system_prompt,
        template_format=sample_template_input.template_format,
        input_variables=sample_template_input.input_variables,
        example_inputs=sample_template_input.example_inputs,
        validation_schema=sample_template_input.validation_schema,
        is_default=sample_template_input.is_default,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.mark.atomic
def test_initialize_default_templates(template_service, sample_user_id):
    """Test initialization of default templates."""
    # Mock repository responses
    template_service.repository.get_by_type = Mock(return_value=None)
    template_service.repository.create_or_update_by_user_id = Mock(
        side_effect=[
            PromptTemplate(template_type=PromptTemplateType.RAG_QUERY),
            PromptTemplate(template_type=PromptTemplateType.QUESTION_GENERATION),
        ]
    )

    rag_template, question_template = template_service.initialize_default_templates(sample_user_id, "watsonx")

    assert rag_template is not None
    assert question_template is not None
    assert template_service.repository.create_or_update_by_user_id.call_count == 2


def test_create_or_update_template(template_service, sample_user_id, sample_template_input, sample_template_model):
    """Test template creation/update."""
    template_service.repository.create_or_update_by_user_id.return_value = sample_template_model

    result = template_service.create_or_update_template(sample_user_id, sample_template_input)

    assert isinstance(result, PromptTemplateOutput)
    assert result.name == sample_template_input.name
    assert result.provider == sample_template_input.provider
    assert result.template_type == sample_template_input.template_type


def test_get_by_id(template_service, sample_template_model):
    """Test template retrieval by ID."""
    template_service.repository.get_by_id.return_value = sample_template_model

    result = template_service.get_by_id(sample_template_model.id)

    assert isinstance(result, PromptTemplateOutput)
    assert result.id == sample_template_model.id
    assert result.name == sample_template_model.name

    # Test nonexistent template
    template_service.repository.get_by_id.return_value = None
    assert template_service.get_by_id(uuid4()) is None


def test_get_user_templates(template_service, sample_user_id, sample_template_model):
    """Test retrieving user's templates."""
    template_service.repository.get_by_user_id.return_value = [sample_template_model]

    results = template_service.get_user_templates(sample_user_id)

    assert len(results) == 1
    assert isinstance(results[0], PromptTemplateOutput)
    assert results[0].id == sample_template_model.id


def test_get_by_type(template_service, sample_user_id, sample_template_model):
    """Test template retrieval by type."""
    template_service.repository.get_user_default_by_type.return_value = sample_template_model

    result = template_service.get_by_type(PromptTemplateType.RAG_QUERY, sample_user_id)

    assert isinstance(result, PromptTemplateOutput)
    assert result.template_type == PromptTemplateType.RAG_QUERY

    # Test fallback to non-default template
    template_service.repository.get_user_default_by_type.return_value = None
    template_service.repository.get_by_user_id_and_type.return_value = [sample_template_model]

    result = template_service.get_by_type(PromptTemplateType.RAG_QUERY, sample_user_id)
    assert result is not None


def test_delete_template(template_service, sample_user_id):
    """Test template deletion."""
    template_service.repository.delete_user_template.return_value = True

    assert template_service.delete_template(sample_user_id, uuid4()) is True

    template_service.repository.delete_user_template.return_value = False
    assert template_service.delete_template(sample_user_id, uuid4()) is False


def test_format_prompt(template_service, sample_template_model):
    """Test prompt formatting."""
    template_service.repository.get_by_id.return_value = sample_template_model

    variables = {"context": "Test context", "question": "Test question"}

    result = template_service.format_prompt(sample_template_model.id, variables)

    assert isinstance(result, str)
    assert variables["context"] in result
    assert variables["question"] in result
    assert sample_template_model.system_prompt in result

    # Test missing variables
    with pytest.raises(ValidationError):
        template_service.format_prompt(sample_template_model.id, {"context": "Test"})

    # Test nonexistent template
    template_service.repository.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        template_service.format_prompt(uuid4(), variables)


def test_apply_context_strategy(template_service, sample_template_model):
    """Test context strategy application."""
    contexts = ["First context chunk", "Second context chunk", "Third context chunk"]

    # Test default strategy
    sample_template_model.context_strategy = None
    template_service.repository.get_by_id.return_value = sample_template_model

    result = template_service.apply_context_strategy(sample_template_model.id, contexts)
    assert isinstance(result, str)
    assert all(context in result for context in contexts)

    # Test custom strategy
    sample_template_model.context_strategy = {
        "max_chunks": 2,
        "chunk_separator": " | ",
        "ordering": "relevance",
        "truncation": "end",
    }
    sample_template_model.max_context_length = 10

    result = template_service.apply_context_strategy(sample_template_model.id, contexts)
    assert isinstance(result, str)
    assert len(result.split(" | ")) == 2  # Only 2 chunks due to max_chunks
    assert all(len(chunk) <= 10 for chunk in result.split(" | "))  # Truncated chunks

    # Test nonexistent template
    template_service.repository.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        template_service.apply_context_strategy(uuid4(), contexts)


def test_template_to_dict(sample_template_model):
    """Test template model to dictionary conversion."""
    result = _template_to_dict(sample_template_model)

    assert isinstance(result, dict)
    assert result["id"] == sample_template_model.id
    assert result["name"] == sample_template_model.name
    assert result["provider"] == sample_template_model.provider
    assert result["template_type"] == sample_template_model.template_type
    assert result["system_prompt"] == sample_template_model.system_prompt
    assert result["template_format"] == sample_template_model.template_format
    assert result["input_variables"] == sample_template_model.input_variables
    assert result["example_inputs"] == sample_template_model.example_inputs
    assert result["validation_schema"] == sample_template_model.validation_schema
    assert result["is_default"] == sample_template_model.is_default


if __name__ == "__main__":
    pytest.main([__file__])
