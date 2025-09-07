"""Tests for prompt template functionality."""

from typing import Any

import pytest
from sqlalchemy.orm import Session

from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.schemas.prompt_template_schema import PromptTemplateType


def test_create_prompt_template(db_session: Session, base_user: Any) -> None:
    """Test creating a prompt template."""
    template = PromptTemplate(
        name="test-template",
        provider="watsonx",
        template_type=PromptTemplateType.RAG_QUERY,
        system_prompt="You are a helpful AI assistant.",
        template_format="{context}\n\n{question}",
        input_variables={
            "context": "Retrieved context for answering the question",
            "question": "User's question to answer",
        },
        example_inputs={"context": "Python was created by Guido van Rossum.", "question": "Who created Python?"},
        is_default=True,
        user_id=base_user.id,
    )
    db_session.add(template)
    db_session.commit()

    assert template.id is not None
    assert template.name == "test-template"
    assert template.provider == "watsonx"
    assert template.template_type == PromptTemplateType.RAG_QUERY
    assert template.system_prompt == "You are a helpful AI assistant."
    assert template.template_format == "{context}\n\n{question}"
    assert template.input_variables is not None
    assert "context" in template.input_variables
    assert "question" in template.input_variables
    assert template.example_inputs is not None
    assert template.example_inputs["context"] == "Python was created by Guido van Rossum."
    assert template.example_inputs["question"] == "Who created Python?"
    assert template.is_default is True


def test_create_question_generation_template(db_session: Session, base_user: Any) -> None:
    """Test creating a question generation template."""
    template = PromptTemplate(
        name="test-question-template",
        provider="watsonx",
        template_type=PromptTemplateType.QUESTION_GENERATION,
        system_prompt=(
            "You are an AI assistant that generates relevant questions based on " "the given context. Generate clear, focused questions that can be " "answered using the information provided."
        ),
        template_format=("{context}\n\n" "Generate {num_questions} specific questions that can be answered " "using only the information provided above."),
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

    assert template.id is not None
    assert template.name == "test-question-template"
    assert template.provider == "watsonx"
    assert template.template_type == PromptTemplateType.QUESTION_GENERATION
    assert "context" in template.input_variables
    assert "num_questions" in template.input_variables
    assert template.example_inputs is not None
    assert template.example_inputs["context"] == "Python supports multiple programming paradigms."
    assert template.example_inputs["num_questions"] == 3
    assert template.is_default is True


def test_invalid_provider(db_session: Session, base_user: Any) -> None:
    """Test that invalid provider raises error."""
    with pytest.raises(ValueError, match="Invalid provider"):
        PromptTemplate(
            name="test-template",
            provider="invalid",
            template_type=PromptTemplateType.RAG_QUERY,
            template_format="{context}\n\n{question}",
            input_variables={
                "context": "Retrieved context for answering the question",
                "question": "User's question to answer",
            },
            user_id=base_user.id,
        )


def test_missing_variables(db_session: Session, base_user: Any) -> None:
    """Test that missing variables in template format raises error."""
    with pytest.raises(ValueError, match="Template variables missing"):
        PromptTemplate(
            name="test-template",
            provider="watsonx",
            template_type=PromptTemplateType.RAG_QUERY,
            template_format="{context}\n\n{question}",
            input_variables={"context": "Retrieved context"},  # Missing question variable
            user_id=base_user.id,
        )
