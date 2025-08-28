"""Integration tests for question service without mocks."""

import pytest
from uuid import uuid4
from typing import List
from sqlalchemy.orm import Session

from core.custom_exceptions import NotFoundError, ValidationError, NotFoundException
from rag_solution.models.question import SuggestedQuestion
from rag_solution.models.collection import Collection
from rag_solution.models.user import User
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.services.question_service import QuestionService
from rag_solution.schemas.prompt_template_schema import PromptTemplateType, PromptTemplateInput
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput


@pytest.mark.atomic
@pytest.mark.asyncio
async def test_suggest_questions_success(
    question_service: QuestionService,
    base_collection: Collection,
    base_user: User,
    base_prompt_template: PromptTemplate,
    test_documents: List[str],
    db_session: Session,
    base_llm_parameters: LLMParameters,
    llm_provider: str
) -> None:
    """Test successful question generation."""
    questions = await question_service.suggest_questions(
        texts=test_documents,
        collection_id=base_collection.id,
        user_id=base_user.id,
        provider_name=llm_provider,
        template=base_prompt_template,
        parameters=base_llm_parameters,
        num_questions=3
    )
    
    assert len(questions) > 0
    assert all(isinstance(q, SuggestedQuestion) for q in questions)
    assert all(q.collection_id == base_collection.id for q in questions)
    assert all(q.is_valid for q in questions)
    
    # Verify questions are relevant to context
    for question in questions:
        assert question.question.strip().endswith('?')
        # Check if question contains key terms from context
        key_terms = ['Python', 'programming', 'language']
        assert any(term.lower() in question.question.lower() for term in key_terms)

@pytest.mark.atomic
@pytest.mark.asyncio
async def test_suggest_questions_empty_texts(
    question_service: QuestionService,
    base_collection: Collection,
    base_user: User,
    base_prompt_template: PromptTemplate,
    base_llm_parameters: LLMParameters,
    llm_provider: str
) -> None:
    """Test question generation with empty texts."""
    questions = await question_service.suggest_questions(
        texts=[],
        collection_id=base_collection.id,
        user_id=base_user.id,
        provider_name=llm_provider,
        template=base_prompt_template,
        parameters=base_llm_parameters
    )
    assert len(questions) == 0


@pytest.mark.atomic
@pytest.mark.asyncio
async def test_suggest_questions_validation(
    question_service: QuestionService,
    base_collection: Collection,
    base_user: User,
    base_prompt_template: PromptTemplate,
    test_documents: List[str],
    base_llm_parameters: LLMParameters,
    llm_provider: str
) -> None:
    """Test question validation logic."""
    # Generate questions with custom validation rules
    questions = await question_service.suggest_questions(
        texts=test_documents,
        collection_id=base_collection.id,
        user_id=base_user.id,
        provider_name=llm_provider,
        template=base_prompt_template,
        parameters=base_llm_parameters
    )

    # Manually validate the generated questions
    for question in questions:
        # Check length constraints (example: min_length=20, max_length=100)
        assert 20 <= len(question.question) <= 100

        # Check required terms (example: 'Python' and 'programming')
        question_lower = question.question.lower()
        assert any(term.lower() in question_lower for term in ['Python', 'programming'])

        # Check question patterns (example: contains 'what', 'how', or 'why')
        assert any(pattern in question_lower for pattern in ['what', 'how', 'why', 'who']), f"Question does not contain expected pattern: {question.question}"


@pytest.mark.atomic
@pytest.mark.asyncio
async def test_regenerate_questions(
    question_service: QuestionService,
    base_collection: Collection,
    base_user: User,
    base_prompt_template: PromptTemplate,
    test_documents: List[str],
    base_llm_parameters: LLMParameters,
    llm_provider: str
) -> None:
    """Test regenerating questions for a collection."""
    # Generate initial questions
    initial_questions = await question_service.suggest_questions(
        texts=test_documents,
        collection_id=base_collection.id,
        user_id=base_user.id,
        provider_name=llm_provider,
        template=base_prompt_template,
        parameters=base_llm_parameters
    )
    assert len(initial_questions) > 0
    initial_ids = {q.id for q in initial_questions}
    
    # Regenerate questions
    new_questions = await question_service.regenerate_questions(
        collection_id=base_collection.id,
        user_id=base_user.id,
        texts=test_documents,
        provider_name=llm_provider,
        template=base_prompt_template,
        parameters=base_llm_parameters
    )
    
    assert len(new_questions) > 0
    new_ids = {q.id for q in new_questions}
    
    # Verify old questions were replaced
    assert not initial_ids.intersection(new_ids)
    assert all(q.is_valid for q in new_questions)


@pytest.mark.atomic
@pytest.mark.asyncio
async def test_get_collection_questions(
    question_service: QuestionService,
    base_collection: Collection,
    base_user: User,
    base_prompt_template: PromptTemplate,
    test_documents: List[str],
    base_llm_parameters: LLMParameters,
    llm_provider: str
) -> None:
    """Test retrieving questions for a collection."""
    # Generate some questions
    generated_questions = await question_service.suggest_questions(
        texts=test_documents,
        collection_id=base_collection.id,
        user_id=base_user.id,
        provider_name=llm_provider,
        template=base_prompt_template,
        parameters=base_llm_parameters
    )
    assert len(generated_questions) > 0
    
    # Retrieve questions
    stored_questions = question_service.get_collection_questions(
        collection_id=base_collection.id
    )
    
    assert len(stored_questions) == len(generated_questions)
    assert {q.id for q in stored_questions} == {q.id for q in generated_questions}


def test_question_filtering(question_service: QuestionService,
                            base_user: User, base_llm_parameters: LLMParameters) -> None:
    """Test internal question filtering logic."""
    questions = [
        "What is Python?",  # Valid
        "1. What is programming?",  # Valid after cleaning
        "Note: This is not a question",  # Invalid - not a question
        "A?",  # Invalid - too short
        "What is Python? Here's the answer: it's a programming language",  # Invalid - contains answer
        "What is the meaning of life, the universe, and everything?"  # Invalid - too long/generic
    ]
    
    context = "Python is a programming language. It is used for software development."
    
    filtered = []
    for q in questions:
        is_valid, cleaned_q = question_service._validate_question(q, context)
        if is_valid:
            filtered.append(cleaned_q)
    
    assert len(filtered) == 2
    assert "What is Python?" in filtered
    assert "What is programming?" in filtered


def test_question_ranking(question_service: QuestionService, base_user: User, 
                          llm_provider: str, base_llm_parameters: LLMParameters) -> None:
    """Test ranking of questions by relevance."""
    questions = [
        "What is machine learning?",  # Less relevant
        "What is the capital of France?",  # Not relevant
        "What is Python used for in software development?",  # Most relevant
        "Who created Python and when?",  # Highly relevant
    ]
    
    context = (
        "Python is a versatile programming language widely used in software development. "
        "It was created by Guido van Rossum and is particularly popular in web development "
        "and data analysis."
    )
    
    ranked = question_service._rank_questions(questions, context, base_user.id, llm_provider)
    
    # Verify ranking order
    assert len(ranked) > 0
    # Most relevant questions should be at the top
    assert "What is Python used for in software development?" in ranked[0:2]
    assert "Who created Python and when?" in ranked[0:2]
    # Irrelevant questions should be filtered out
    assert "What is the capital of France?" not in ranked


def test_duplicate_question_filtering(question_service: QuestionService) -> None:
    """Test deduplication of similar questions."""
    questions = [
        "What is Python?",
        "WHAT IS PYTHON?",  # Duplicate with different case
        "What is python?",  # Duplicate with different case
        "What is Python programming?",  # Different question
        "1. What is Python?",  # Duplicate with numbering
        "What is Python!?",  # Duplicate with different punctuation
    ]
    
    unique_questions = question_service._filter_duplicate_questions(questions)
    assert len(unique_questions) == 2
    assert "What is Python?" in unique_questions
    assert "What is Python programming?" in unique_questions


@pytest.mark.atomic
@pytest.mark.asyncio
async def test_suggest_questions_empty_llm_response(
    question_service: QuestionService,
    base_collection: Collection,
    base_user: User,
    base_prompt_template: PromptTemplate,
    test_documents: List[str],
    base_llm_parameters: LLMParameters,
    llm_provider: str
) -> None:
    """Test handling of empty LLM response."""
    # Create a restrictive prompt template
    restrictive_template = PromptTemplateInput(
        name="restrictive-template",
        provider=base_prompt_template.provider,
        template_type=PromptTemplateType.QUESTION_GENERATION,
        system_prompt="Generate very long and specific questions.",
        template_format="{context}\n\nGenerate {num_questions} questions.",  # Ensure context is included
        input_variables={
            "context": "Retrieved context for answering the question",
            "num_questions": "Number of questions to generate"
        },
        example_inputs={
            "context": "Python is a programming language.",
            "num_questions": 3
        },
        context_strategy=base_prompt_template.context_strategy,
        max_context_length=100,  # Restrict context length
        stop_sequences=["\n"],   # Stop generation at newlines
        is_default=False,
        validation_schema={
            "model": "PromptVariables",
            "fields": {
                "context": {"type": "str", "min_length": 1000},  # Require long context
                "question": {"type": "str", "min_length": 1000}  # Require long questions
            },
            "required": ["context", "question"]
        }
    )

    # Use restrictive LLM parameters
    restrictive_parameters = LLMParametersInput(
        name="restrictive_params",
        max_new_tokens=10,  # Force very short questions
        temperature=0.1,    # Low temperature for deterministic output
        top_k=1,            # Restrict sampling to top 1 token
        top_p=0.1,          # Restrict sampling to top 10% of tokens
        repetition_penalty=2.0  # High penalty for repetition
    )

    # Generate questions with restrictive parameters and template
    questions = await question_service.suggest_questions(
        texts=test_documents,
        collection_id=base_collection.id,
        user_id=base_user.id,
        provider_name=llm_provider,
        template=restrictive_template,
        parameters=restrictive_parameters,
        num_questions=5  # Pass the number of questions as a variable
    )

    # Assert that no questions were generated due to restrictions
    assert len(questions) == 0

@pytest.mark.atomic
def test_validate_question_malformed_input(question_service: QuestionService) -> None:
    """Test validation of malformed questions."""
    context = "Sample context"
    malformed_cases = [
        None,  # None input
        "",  # Empty string
        "?" * 1000,  # Extremely long question mark string
        "\n\n\n?",  # Just newlines and question mark
        "What is Python" + "?" * 100,  # Multiple question marks
        "What\x00is\x00Python?",  # Null bytes
    ]
    
    for question in malformed_cases:
        is_valid, cleaned = question_service._validate_question(question, context)
        assert not is_valid

@pytest.mark.atomic
def test_invalid_configuration(question_service: QuestionService) -> None:
    """Test validation of invalid question inputs."""
    context = "Python is a programming language. It is used for software development."

    # Test invalid questions
    invalid_questions = [
        None,  # None input
        "",  # Empty string
        "?" * 1000,  # Extremely long question mark string
        "\n\n\n?",  # Just newlines and question mark
        "What is Python" + "?" * 100,  # Multiple question marks
        "What\x00is\x00Python?",  # Null bytes
    ]

    for question in invalid_questions:
        is_valid, cleaned = question_service._validate_question(question, context)
        assert not is_valid, f"Expected invalid question: {question}"

if __name__ == "__main__":
    pytest.main([__file__])
