"""Tests for question service with provider system."""

import pytest
from uuid import UUID
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.generation.providers.base import LLMProvider, LLMProviderError
from rag_solution.schemas.collection_schema import CollectionInput, CollectionStatus
from rag_solution.schemas.prompt_template_schema import PromptTemplateCreate
from rag_solution.schemas.user_schema import UserInput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.question_service import QuestionService
from rag_solution.services.runtime_config_service import RuntimeConfigService
from rag_solution.services.user_service import UserService
from rag_solution.services.user_team_service import UserTeamService

logger = get_logger(__name__)

@pytest.fixture
def user_team_service(db_session):
    """Create user team service."""
    return UserTeamService(db_session)

@pytest.fixture
def user_service(db_session: Session, user_team_service: UserTeamService):
    """Create user service."""
    return UserService(db_session, user_team_service)

@pytest.fixture
def test_user(user_service):
    """Create test user."""
    user = user_service.create_user(UserInput(
        ibm_id="test_ibm_id",
        email="test@example.com",
        name="Test User"
    ))
    return user

@pytest.fixture
def collection_service(db_session):
    """Create collection service."""
    return CollectionService(db_session)

@pytest.fixture
def provider(db_session: Session):
    """Create LLM provider instance."""
    provider = LLMProviderFactory(db_session).get_provider("watsonx")
    yield provider
    provider.close()

@pytest.fixture
def question_service(db_session: Session, provider: LLMProvider):
    """Create question service instance with real provider."""
    try:
        # Create prompt template
        prompt_template_service = PromptTemplateService(db_session)
        template = prompt_template_service.create_template(PromptTemplateCreate(
            name="watsonx-question-gen",
            provider="watsonx",
            description="Template for generating questions",
            system_prompt="You are a helpful AI assistant.",
            context_prefix="Context:",
            query_prefix="Generate questions about this context:\n",
            answer_prefix="Questions:\n",
            input_variables=["prompt", "context", "num_questions"],
            template_format="{prompt}\n\nBased on this context:\n{context}\n\nGenerate {num_questions} questions about the above context."
        ))
        
        # Create service
        service = QuestionService(
            db=db_session,
            provider=provider,
            config={
                'num_questions': 2,
                'min_length': 10,
                'max_length': 100
            }
        )
        return service
    except Exception as e:
        logger.error(f"Error in question service fixture: {e}")
        raise

@pytest.mark.asyncio
async def test_suggest_questions_provider_error(question_service: QuestionService, collection_service: CollectionService, test_user):
    """Test question suggestion with provider error."""
    try:
        logger.info("Testing question suggestion with provider error")
        
        # Create test collection
        collection = collection_service.create_collection(CollectionInput(
            name="test_collection",
            is_private=True,
            users=[test_user.id],
            status=CollectionStatus.CREATED
        ))
        
        # Break the provider client
        question_service.provider.client = None
        question_service.provider.initialize_client = lambda: None  # Prevent auto-initialization
        
        texts = ["Test context"]
        
        with pytest.raises(LLMProviderError, match="Provider client is not initialized"):
            await question_service.suggest_questions(texts, collection.id, 2)
        
        logger.info("Provider error test passed")
    except Exception as e:
        logger.error(f"Provider error test failed: {e}")
        raise

def test_service_initialization(question_service: QuestionService):
    """Test service initialization with provider configuration."""
    try:
        logger.info("Testing question service initialization")
        assert question_service.provider is not None
        assert question_service.num_questions == 2
        assert question_service.min_length == 10
        assert question_service.max_length == 100
        logger.info("Question service initialization test passed")
    except Exception as e:
        logger.error(f"Question service initialization test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_suggest_questions(question_service: QuestionService, collection_service: CollectionService, test_user):
    """Test question suggestion using provider."""
    try:
        logger.info("Testing question suggestion")
        texts = ["""
        The Python programming language was created by Guido van Rossum and was first released in 1991.
        Python is known for its simplicity and readability, emphasizing code readability with its notable
        use of significant whitespace. Python features a dynamic type system and automatic memory management.
        """]
        
        # Create test collection
        collection = collection_service.create_collection(CollectionInput(
            name="test_collection",
            is_private=True,
            users=[test_user.id],
            status=CollectionStatus.CREATED
        ))
        
        questions = await question_service.suggest_questions(texts, collection.id, 2)
        logger.info(f"Generated {len(questions)} questions")
        
        # Verify questions
        assert len(questions) > 0
        assert all(q.endswith('?') for q in questions)
        assert all(len(q) >= question_service.min_length for q in questions)
        assert all(len(q) <= question_service.max_length for q in questions)
        
        # Verify content relevance
        questions_text = ' '.join(questions).lower()
        assert any(term in questions_text for term in ['python', 'programming', 'language'])
        
        # Verify questions are stored
        stored_questions = question_service.get_collection_questions(collection.id)
        assert set(questions) == set(stored_questions)
        
        logger.info("Question suggestion test passed")
    except Exception as e:
        logger.error(f"Question suggestion test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_suggest_questions_empty_texts(question_service: QuestionService, collection_service: CollectionService, test_user):
    """Test question suggestion with empty texts."""
    try:
        logger.info("Testing question suggestion with empty texts")
        
        # Create test collection
        collection = collection_service.create_collection(CollectionInput(
            name="test_collection",
            is_private=True,
            users=[test_user.id],
            status=CollectionStatus.CREATED
        ))
        
        questions = await question_service.suggest_questions([], collection.id, 2)
        assert len(questions) == 0
        
        logger.info("Empty texts test passed")
    except Exception as e:
        logger.error(f"Empty texts test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_suggest_questions_invalid_template(question_service: QuestionService, collection_service: CollectionService, test_user, monkeypatch):
    """Test question suggestion with invalid template."""
    try:
        logger.info("Testing question suggestion with invalid template")
        
        # Create test collection
        collection = collection_service.create_collection(CollectionInput(
            name="test_collection",
            is_private=True,
            users=[test_user.id],
            status=CollectionStatus.CREATED
        ))
        
        # Mock get_question_template to raise error
        def mock_get_template():
            raise ValueError("Template not found")
        monkeypatch.setattr(question_service, '_get_question_template', mock_get_template)
        
        texts = ["Test context"]
        
        with pytest.raises(ValueError, match="Template not found"):
            await question_service.suggest_questions(texts, collection.id, 2)
        
        logger.info("Invalid template test passed")
    except Exception as e:
        logger.error(f"Invalid template test failed: {e}")
        raise

def test_duplicate_filtering(question_service: QuestionService):
    """Test duplicate question filtering."""
    try:
        logger.info("Testing duplicate question filtering")
        questions = [
            "What is testing?",
            "what is Testing?",  # Same question, different case
            "How does testing work?",
            "What is testing?"  # Exact duplicate
        ]
        
        filtered = question_service._filter_duplicate_questions(questions)
        logger.info(f"Filtered {len(filtered)} unique questions")
        
        assert len(filtered) == 2
        assert "What is testing?" in filtered
        assert "How does testing work?" in filtered
        logger.info("Duplicate filtering test passed")
    except Exception as e:
        logger.error(f"Duplicate filtering test failed: {e}")
        raise

def test_text_chunk_combination(question_service: QuestionService):
    """Test text chunk combination logic."""
    try:
        logger.info("Testing text chunk combination")
        texts = [
            "First chunk of text.",
            "Second chunk of text.",
            "Third chunk of text."
        ]
        available_length = len("First chunk of text.Second chunk of text.")
        
        combined = question_service._combine_text_chunks(texts, available_length)
        logger.info(f"Combined into {len(combined)} chunks")
        
        assert len(combined) == 2
        assert combined[0].startswith("First chunk")
        assert combined[1].startswith("Third chunk")
        logger.info("Text chunk combination test passed")
    except Exception as e:
        logger.error(f"Text chunk combination test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_regenerate_questions(question_service: QuestionService, collection_service: CollectionService, test_user):
    """Test question regeneration for a collection."""
    try:
        logger.info("Testing question regeneration")
        texts = ["""
        The Python programming language was created by Guido van Rossum and was first released in 1991.
        Python is known for its simplicity and readability, emphasizing code readability with its notable
        use of significant whitespace. Python features a dynamic type system and automatic memory management.
        """]
        
        # Create test collection
        collection = collection_service.create_collection(CollectionInput(
            name="test_collection",
            is_private=True,
            users=[test_user.id],
            status=CollectionStatus.CREATED
        ))
        
        # First generate questions
        logger.info("Generating initial questions")
        initial_questions = await question_service.suggest_questions(texts, collection.id, 2)
        assert len(initial_questions) > 0
        initial_text = ' '.join(initial_questions).lower()
        assert any(term in initial_text for term in ['python', 'programming', 'language'])
        
        # Then regenerate
        logger.info("Regenerating questions")
        new_questions = await question_service.regenerate_questions(collection.id, texts, 2)
        assert len(new_questions) > 0
        new_text = ' '.join(new_questions).lower()
        assert any(term in new_text for term in ['python', 'programming', 'language'])
        
        # Questions should be different
        assert set(initial_questions) != set(new_questions)
        logger.info("Question regeneration test passed")
    except Exception as e:
        logger.error(f"Question regeneration test failed: {e}")
        raise
