"""Tests for question service provider integration."""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.schemas.prompt_template_schema import PromptTemplateType
from rag_solution.services.question_service import QuestionService


@pytest.mark.asyncio
@pytest.mark.atomic
@patch("rag_solution.services.question_service.ProviderFactory")
async def test_question_generation_with_watsonx(mock_provider_factory, db_session: Session, base_user, base_collection):
    """Test question generation using WatsonX provider."""
    # Mock the provider factory and WatsonX provider
    mock_watsonx = mock_provider_factory.return_value.get_provider.return_value
    mock_watsonx.generate_questions.return_value = [
        "What is Python?",
        "Who created Python?",
        "What are Python's key features?",
    ]

    # Create template
    template = PromptTemplate(
        name="test-question-template",
        provider="watsonx",
        template_type=PromptTemplateType.QUESTION_GENERATION,
        system_prompt=(
            "You are an AI assistant that generates relevant questions based on "
            "the given context. Generate clear, focused questions that can be "
            "answered using the information provided."
        ),
        template_format=(
            "{context}\n\n"
            "Generate {num_questions} specific questions that can be answered "
            "using only the information provided above."
        ),
        input_variables={
            "context": "Retrieved passages from knowledge base",
            "num_questions": "Number of questions to generate",
        },
        example_inputs={"context": "Python supports multiple programming paradigms.", "num_questions": 3},
        is_default=True,
        user_id=base_user.id,
    )
    db_session.add(template)
    db_session.commit()

    # Test service
    service = QuestionService(db_session)
    context = (
        "Python is a high-level programming language created by Guido van Rossum. "
        "It emphasizes code readability and allows programmers to express concepts "
        "in fewer lines of code than would be possible in languages such as C++ or Java."
    )
    questions = await service.suggest_questions(
        texts=[context],
        collection_id=base_collection.id,
        user_id=base_user.id,
        provider_name="watsonx",
        num_questions=3,
    )

    assert len(questions) > 0
    for question in questions:
        assert question.question.strip().endswith("?")
        assert len(question.question) > 0


def test_question_generation_with_invalid_template(db_session: Session, base_user):
    """Test question generation with invalid template."""
    # Create template with missing variables
    template = PromptTemplate(
        name="test-template",
        provider="watsonx",
        template_type=PromptTemplateType.QUESTION_GENERATION,
        template_format="{context}\n\n{num_questions}",
        input_variables={"context": "Retrieved context"},  # Missing num_questions
        user_id=base_user.id,
    )
    db_session.add(template)
    db_session.commit()

    # Test service
    service = QuestionService(db_session)
    context = "Python is a programming language."

    with pytest.raises(ValueError, match="Template variables missing"):
        service.generate_questions(context, template.id, num_questions=3)


def test_question_generation_with_nonexistent_template(db_session: Session):
    """Test question generation with nonexistent template."""
    service = QuestionService(db_session)
    context = "Python is a programming language."

    with pytest.raises(ValueError, match="Template not found"):
        service.generate_questions(context, "nonexistent-id", num_questions=3)


def test_question_generation_with_invalid_provider(db_session: Session, base_user):
    """Test question generation with invalid provider."""
    # Create template with invalid provider
    with pytest.raises(ValueError, match="Invalid provider"):
        PromptTemplate(
            name="test-template",
            provider="invalid",
            template_type=PromptTemplateType.QUESTION_GENERATION,
            template_format="{context}\n\n{num_questions}",
            input_variables={"context": "Retrieved context", "num_questions": "Number of questions"},
            user_id=base_user.id,
        )
