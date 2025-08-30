"""Tests for PromptTemplateService."""

import pytest

from core.custom_exceptions import NotFoundError, ValidationError
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.prompt_template_service import PromptTemplateService


# -------------------------------------------
# 🔧 Test Fixtures
# -------------------------------------------
@pytest.fixture
def test_prompt_template(base_user: UserOutput) -> PromptTemplateInput:
    """Test prompt template data."""
    return PromptTemplateInput(
        name="test-template",
        user_id=base_user.id,
        template_type=PromptTemplateType.RAG_QUERY,
        system_prompt="You are a helpful AI assistant.",
        template_format="Context:\n{context}\nQuestion:{question}",
        input_variables={"context": "Retrieved context", "question": "User's question"},
        example_inputs={"context": "Initial context", "question": "Initial question"},
        max_context_length=1000,
        is_default=True,
    )


# -------------------------------------------
# 🧪 Template Creation Tests
# -------------------------------------------
@pytest.mark.atomic
def test_create_prompt_template(
    prompt_template_service: PromptTemplateService, base_user: UserOutput, test_prompt_template: PromptTemplateInput
) -> None:
    """Test creating prompt template."""
    template = prompt_template_service.create_template(test_prompt_template)

    assert template.name == test_prompt_template.name
    assert template.template_type == test_prompt_template.template_type
    assert template.is_default == test_prompt_template.is_default


@pytest.mark.atomic
def test_create_or_update_template(
    prompt_template_service: PromptTemplateService, base_user: UserOutput, test_prompt_template: PromptTemplateInput
) -> None:
    """Test template creation and update."""
    # Create initial template
    template = prompt_template_service.create_template(test_prompt_template)

    # Update the same template
    updated_input = test_prompt_template.model_copy(update={"system_prompt": "Updated system prompt"})
    updated = prompt_template_service.update_template(template.id, updated_input)

    assert updated.id == template.id
    assert updated.system_prompt == "Updated system prompt"


# -------------------------------------------
# 🧪 Template Retrieval Tests
# -------------------------------------------
@pytest.mark.atomic
def test_get_by_id(prompt_template_service: PromptTemplateService, base_user: UserOutput, test_prompt_template: PromptTemplateInput) -> None:
    """Test template retrieval by ID."""
    created = prompt_template_service.create_template(test_prompt_template)

    # Use get_by_type since there's no get_by_id method
    template = prompt_template_service.get_by_type(base_user.id, created.template_type)
    assert template is not None
    assert template.id == created.id
    assert template.name == created.name


@pytest.mark.atomic
def test_get_by_type(prompt_template_service: PromptTemplateService, base_user: UserOutput, test_prompt_template: PromptTemplateInput) -> None:
    """Test template retrieval by type."""
    prompt_template_service.create_template(test_prompt_template)

    template = prompt_template_service.get_by_type(base_user.id, PromptTemplateType.RAG_QUERY)

    assert template is not None
    assert template.template_type == PromptTemplateType.RAG_QUERY
    assert template.user_id == base_user.id


@pytest.mark.atomic
def test_get_user_templates(prompt_template_service: PromptTemplateService, base_user: UserOutput, test_prompt_template: PromptTemplateInput) -> None:
    """Test retrieving user's templates."""
    created = prompt_template_service.create_template(test_prompt_template)

    templates = prompt_template_service.get_user_templates(base_user.id)
    assert len(templates) > 0
    assert any(t.id == created.id for t in templates)


# -------------------------------------------
# 🧪 Template Deletion Tests
# -------------------------------------------
@pytest.mark.atomic
def test_delete_template(prompt_template_service: PromptTemplateService, base_user: UserOutput, test_prompt_template: PromptTemplateInput) -> None:
    """Test template deletion."""
    created = prompt_template_service.create_template(test_prompt_template)

    result = prompt_template_service.delete_template(base_user.id, created.id)
    assert result is True

    # Verify template is deleted by checking get_by_type returns None
    template = prompt_template_service.get_by_type(base_user.id, created.template_type)
    assert template is None


# -------------------------------------------
# 🧪 Template Formatting Tests
# -------------------------------------------
@pytest.mark.atomic
def test_format_prompt(prompt_template_service: PromptTemplateService, base_user: UserOutput, test_prompt_template: PromptTemplateInput) -> None:
    """Test prompt formatting."""
    template = prompt_template_service.create_template(test_prompt_template)

    variables = {"context": "Test context", "question": "Test question"}

    result = prompt_template_service.format_prompt(template.id, variables)

    assert isinstance(result, str)
    assert variables["context"] in result
    assert variables["question"] in result
    if template.system_prompt:
        assert template.system_prompt in result


@pytest.mark.atomic
def test_format_prompt_missing_variables(
    prompt_template_service: PromptTemplateService, base_user: UserOutput, test_prompt_template: PromptTemplateInput
) -> None:
    """Test prompt formatting with missing variables."""
    template = prompt_template_service.create_template(test_prompt_template)

    with pytest.raises(ValidationError):
        prompt_template_service.format_prompt(
            template.id,
            {"context": "Test context"},  # Missing question
        )


# -------------------------------------------
# 🧪 Context Strategy Tests
# -------------------------------------------
@pytest.mark.atomic
def test_apply_context_strategy(
    prompt_template_service: PromptTemplateService, base_user: UserOutput, test_prompt_template: PromptTemplateInput
) -> None:
    """Test context strategy application."""
    contexts = ["First context chunk", "Second context chunk", "Third context chunk"]

    # Test default strategy
    template = prompt_template_service.create_template(test_prompt_template)

    result = prompt_template_service.apply_context_strategy(template.id, contexts)
    assert isinstance(result, str)
    assert all(context in result for context in contexts)


@pytest.mark.atomic
def test_apply_custom_context_strategy(
    prompt_template_service: PromptTemplateService, base_user: UserOutput, test_prompt_template: PromptTemplateInput
) -> None:
    """Test custom context strategy application."""
    # Create template with custom strategy
    template_with_strategy = test_prompt_template.model_copy(
        update={
            "context_strategy": {
                "max_chunks": 2,
                "chunk_separator": " | ",
                "ordering": "relevance",
                "truncation": "end",
            },
            "max_context_length": 10,
        }
    )

    template = prompt_template_service.create_template(template_with_strategy)

    contexts = ["First chunk", "Second chunk", "Third chunk"]
    result = prompt_template_service.apply_context_strategy(template.id, contexts)

    assert isinstance(result, str)
    assert len(result.split(" | ")) == 2  # Only 2 chunks due to max_chunks
    assert all(len(chunk) <= 10 for chunk in result.split(" | "))  # Truncated chunks


if __name__ == "__main__":
    pytest.main([__file__])
