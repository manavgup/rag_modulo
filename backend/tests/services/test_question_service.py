"""Tests for question service with provider system."""

import os
import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from rag_solution.services.question_service import QuestionService
from core.logging_utils import get_logger
from rag_solution.services.provider_config_service import ProviderConfigService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.schemas.llm_parameters_schema import LLMParametersCreate
from rag_solution.schemas.prompt_template_schema import PromptTemplateCreate
from rag_solution.schemas.provider_config_schema import ProviderModelConfigBase

logger = get_logger(__name__)

@pytest.fixture
def provider_config_service(db_session: Session) -> ProviderConfigService:
    """Fixture for provider config service."""
    return ProviderConfigService(db_session)

@pytest.fixture
def llm_parameters_service(db_session: Session) -> LLMParametersService:
    """Fixture for LLM parameters service."""
    return LLMParametersService(db_session)

@pytest.fixture
def prompt_template_service(db_session: Session) -> PromptTemplateService:
    """Fixture for prompt template service."""
    return PromptTemplateService(db_session)

@pytest.fixture
def sample_llm_params() -> LLMParametersCreate:
    """Fixture for sample LLM parameters."""
    return LLMParametersCreate(
        name="test_params",
        description="Test parameters",
        max_new_tokens=150,
        min_new_tokens=1,
        temperature=0.7,
        top_k=50,
        top_p=1.0
    )

@pytest.fixture
def sample_prompt_template() -> PromptTemplateCreate:
    """Fixture for sample prompt template."""
    return PromptTemplateCreate(
        name="test_template",
        provider="watsonx",
        description="Test template",
        system_prompt="You are a helpful AI assistant",
        context_prefix="Context:",
        query_prefix="Question:",
        answer_prefix="Answer:"
    )

@pytest.fixture
def sample_provider_config() -> ProviderModelConfigBase:
    """Fixture for sample provider configuration."""
    return ProviderModelConfigBase(
        provider_name="watsonx",
        model_id="meta-llama/llama-2-70b-chat",
        default_model_id="meta-llama/llama-2-70b-chat",
        api_key=os.getenv('WATSONX_APIKEY', ''),
        api_url=os.getenv('WATSONX_URL', ''),
        project_id=os.getenv('WATSONX_INSTANCE_ID', ''),
        parameters_id=1,
        timeout=30,
        max_retries=3,
        batch_size=10
    )

@pytest.fixture
def question_service(
    db_session: Session,
    base_environment,
    provider_config_service: ProviderConfigService,
    llm_parameters_service: LLMParametersService,
    prompt_template_service: PromptTemplateService,
    sample_llm_params: LLMParametersCreate,
    sample_prompt_template: PromptTemplateCreate,
    sample_provider_config: ProviderModelConfigBase
) -> QuestionService:
    """Question service instance with real components."""
    try:
        logger.info("Creating question service instance for tests")
        
        # Register provider model
        provider_config_service.register_provider_model(
            provider="watsonx",
            model_id="meta-llama/llama-2-70b-chat",
            parameters=sample_llm_params,
            provider_config=sample_provider_config,
            prompt_template=sample_prompt_template
        )
        
        # Create service with configuration
        config = {
            'num_questions': 2,
            'min_length': 10,
            'max_length': 100
        }
        
        service = QuestionService(db_session, config)
        logger.info("Question service instance created successfully")
        return service
    except Exception as e:
        logger.error(f"Failed to create question service instance: {e}")
        raise

def test_service_initialization(question_service):
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
async def test_generate_questions(question_service):
    """Test question generation using provider."""
    try:
        logger.info("Testing question generation")
        context = """
        The Python programming language was created by Guido van Rossum and was first released in 1991.
        Python is known for its simplicity and readability, emphasizing code readability with its notable
        use of significant whitespace. Python features a dynamic type system and automatic memory management.
        """
        
        questions = await question_service._generate_questions_async(context, 2)
        logger.info(f"Generated {len(questions)} questions")
        
        # Verify questions
        assert len(questions) > 0
        assert all(q.endswith('?') for q in questions)
        assert all(len(q) >= question_service.min_length for q in questions)
        assert all(len(q) <= question_service.max_length for q in questions)
        logger.info("Question generation test passed")
    except Exception as e:
        logger.error(f"Question generation test failed: {e}")
        raise

def test_question_validation(question_service):
    """Test question validation logic."""
    try:
        logger.info("Testing question validation")
        valid_question = "What is the main concept in this context?"
        invalid_question = "Note: this is not a question"
        context = "The main concept involves understanding context and validation."
        
        assert question_service._validate_question(valid_question, context)
        assert not question_service._validate_question(invalid_question, context)
        logger.info("Question validation test passed")
    except Exception as e:
        logger.error(f"Question validation test failed: {e}")
        raise

def test_question_ranking(question_service):
    """Test question ranking functionality."""
    try:
        logger.info("Testing question ranking")
        questions = [
            "What is the main concept?",
            "How does this relate to testing?",
            "Why is validation important?"
        ]
        context = "Testing involves validating main concepts and ensuring proper functionality."
        
        ranked = question_service._rank_questions(questions, context)
        logger.info(f"Ranked {len(ranked)} questions")
        
        assert len(ranked) == len(questions)
        # First question should have highest relevance due to matching terms
        assert "main concept" in ranked[0].lower()
        logger.info("Question ranking test passed")
    except Exception as e:
        logger.error(f"Question ranking test failed: {e}")
        raise

def test_duplicate_filtering(question_service):
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

def test_text_chunk_combination(question_service):
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
async def test_suggest_questions(question_service, db_session):
    """Test end-to-end question suggestion."""
    try:
        logger.info("Testing question suggestion")
        texts = ["""
        The Python programming language was created by Guido van Rossum and was first released in 1991.
        Python is known for its simplicity and readability, emphasizing code readability with its notable
        use of significant whitespace. Python features a dynamic type system and automatic memory management.
        """]
        collection_id = db_session.info['test_collection_id']
        
        questions = await question_service.suggest_questions(texts, collection_id, 2)
        logger.info(f"Generated {len(questions)} suggested questions")
        
        # Verify basic structure
        assert len(questions) > 0
        assert all(isinstance(q, str) for q in questions)
        assert all(q.endswith('?') for q in questions)
        
        # Verify question content
        question_text = ' '.join(questions).lower()
        assert any(term in question_text for term in ['python', 'programming', 'language'])
        assert any(term in question_text for term in ['guido', 'van rossum', 'creator'])
        logger.info("Question suggestion test passed")
    except Exception as e:
        logger.error(f"Question suggestion test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_regenerate_questions(question_service, db_session):
    """Test question regeneration for a collection."""
    try:
        logger.info("Testing question regeneration")
        texts = ["""
        The Python programming language was created by Guido van Rossum and was first released in 1991.
        Python is known for its simplicity and readability, emphasizing code readability with its notable
        use of significant whitespace. Python features a dynamic type system and automatic memory management.
        """]
        collection_id = db_session.info['test_collection_id']
        
        # First generate questions
        logger.info("Generating initial questions")
        initial_questions = await question_service.suggest_questions(texts, collection_id, 2)
        assert len(initial_questions) > 0
        initial_text = ' '.join(initial_questions).lower()
        assert any(term in initial_text for term in ['python', 'programming', 'language'])
        
        # Then regenerate
        logger.info("Regenerating questions")
        new_questions = await question_service.regenerate_questions(collection_id, texts, 2)
        assert len(new_questions) > 0
        new_text = ' '.join(new_questions).lower()
        assert any(term in new_text for term in ['python', 'programming', 'language'])
        
        # Questions should be different
        assert set(initial_questions) != set(new_questions)
        logger.info("Question regeneration test passed")
    except Exception as e:
        logger.error(f"Question regeneration test failed: {e}")
        raise
