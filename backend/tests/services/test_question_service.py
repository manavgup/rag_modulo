"""Integration tests for QuestionService."""


import pytest

from rag_solution.schemas.collection_schema import CollectionOutput
from rag_solution.schemas.llm_parameters_schema import LLMParametersOutput
from rag_solution.schemas.prompt_template_schema import PromptTemplateOutput
from rag_solution.schemas.question_schema import QuestionInput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.question_service import QuestionService


@pytest.mark.atomic
@pytest.mark.asyncio
async def test_suggest_questions_success(
    question_service: QuestionService,
    base_collection: CollectionOutput,
    base_user: UserOutput,
    base_prompt_template: PromptTemplateOutput,
    test_documents: list[str],
    base_llm_parameters: LLMParametersOutput,
    llm_provider: str,
) -> None:
    """Test successful question generation."""
    questions = await question_service.suggest_questions(
        texts=test_documents,
        collection_id=base_collection.id,
        user_id=base_user.id,
        provider_name=llm_provider,
        template=base_prompt_template,
        parameters=base_llm_parameters.to_input(),
    )

    assert len(questions) > 0
    assert all(q.collection_id == base_collection.id for q in questions)
    assert all(q.is_valid for q in questions)

    # Verify questions are relevant to context
    for question in questions:
        assert question.question.strip().endswith("?")
        # Check if question contains key terms from context
        key_terms = ["Python", "programming", "language"]
        assert any(term.lower() in question.question.lower() for term in key_terms)


@pytest.mark.atomic
@pytest.mark.asyncio
async def test_suggest_questions_empty_texts(
    question_service: QuestionService,
    base_collection: CollectionOutput,
    base_user: UserOutput,
    base_prompt_template: PromptTemplateOutput,
    base_llm_parameters: LLMParametersOutput,
    llm_provider: str,
) -> None:
    """Test question generation with empty texts."""
    questions = await question_service.suggest_questions(
        texts=[],
        collection_id=base_collection.id,
        user_id=base_user.id,
        provider_name=llm_provider,
        template=base_prompt_template,
        parameters=base_llm_parameters.to_input(),
    )
    assert len(questions) == 0


@pytest.mark.atomic
@pytest.mark.asyncio
async def test_question_generation_with_technical_content(
    question_service: QuestionService,
    base_collection: CollectionOutput,
    base_user: UserOutput,
    base_prompt_template: PromptTemplateOutput,
    base_llm_parameters: LLMParametersOutput,
    llm_provider: str,
) -> None:
    """Test question generation with technical documentation."""
    technical_texts = [
        "Docker containers are lightweight, standalone executable packages that include "
        "everything needed to run an application: code, runtime, system tools, libraries, "
        "and settings. Containers isolate software from its surroundings and ensure "
        "consistent operation across different environments.",
        "Kubernetes is an open-source container orchestration platform that automates "
        "the deployment, scaling, and management of containerized applications. It groups "
        "containers into logical units for easy management and discovery.",
        "Container orchestration handles the scheduling, deployment, scaling, and networking "
        "of containers in modern cloud architectures. Organizations use orchestration tools "
        "to manage complex containerized applications across multiple clusters.",
    ]

    questions = await question_service.suggest_questions(
        texts=technical_texts,
        collection_id=base_collection.id,
        user_id=base_user.id,
        provider_name=llm_provider,
        template=base_prompt_template,
        parameters=base_llm_parameters.to_input(),
    )

    assert len(questions) > 0

    # Verify technical question quality
    tech_terms = ["docker", "container", "kubernetes", "orchestration", "deployment"]
    questions_text = " ".join(q.question.lower() for q in questions)
    assert any(term in questions_text for term in tech_terms)

    # Each question should focus on a specific technical concept
    for question in questions:
        assert question.is_valid
        # Should not be too broad
        assert not question.question.startswith("What is the meaning")
        assert not question.question.startswith("Can you explain")
        # Should be focused technical questions
        assert len(question.question.split()) <= 15


@pytest.mark.atomic
def test_question_filtering(question_service: QuestionService, base_user: UserOutput, base_llm_parameters: LLMParametersOutput) -> None:
    """Test internal question filtering logic."""
    questions = [
        "What is Python?",  # Valid
        "1. What is programming?",  # Valid after cleaning
        "Note: This is not a question",  # Invalid - not a question
        "A?",  # Invalid - too short
        "What is Python? Here's the answer: it's a programming language",  # Invalid - contains answer
        "What is the meaning of life, the universe, and everything?",  # Invalid - too long/generic
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


@pytest.mark.atomic
def test_question_ranking(question_service: QuestionService, base_user: UserOutput, base_llm_parameters: LLMParametersOutput) -> None:
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

    ranked = question_service._rank_questions(questions, context)

    # Verify ranking order
    assert len(ranked) > 0
    # Most relevant questions should be at the top
    assert "What is Python used for in software development?" in ranked[0:2]
    assert "Who created Python and when?" in ranked[0:2]
    # Irrelevant questions should be filtered out
    assert "What is the capital of France?" not in ranked


@pytest.mark.atomic
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
async def test_question_storage_and_retrieval(
    question_service: QuestionService,
    base_collection: CollectionOutput,
    base_user: UserOutput,
    base_prompt_template: PromptTemplateOutput,
    base_llm_parameters: LLMParametersOutput,
    llm_provider: str,
) -> None:
    """Test storing and retrieving generated questions."""
    # Generate initial questions
    texts = ["Python is a programming language used for software development."]
    initial_questions = await question_service.suggest_questions(
        texts=texts,
        collection_id=base_collection.id,
        user_id=base_user.id,
        provider_name=llm_provider,
        template=base_prompt_template,
        parameters=base_llm_parameters.to_input(),
    )

    assert len(initial_questions) > 0

    # Retrieve questions
    stored_questions = question_service.get_collection_questions(base_collection.id)
    assert len(stored_questions) == len(initial_questions)

    # Create additional question
    question_service.create_question(
        QuestionInput(collection_id=base_collection.id, question="What are the main features of Python?")
    )

    # Verify question was added
    updated_questions = question_service.get_collection_questions(base_collection.id)
    assert len(updated_questions) == len(initial_questions) + 1


if __name__ == "__main__":
    pytest.main([__file__])
