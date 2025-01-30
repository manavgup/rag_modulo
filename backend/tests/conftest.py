"""Pytest configuration and shared fixtures with strong typing."""

import logging
import os
from typing import Generator, List
import pytest
from uuid import UUID, uuid4
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy import text
from pydantic import SecretStr

from core.config import settings
from core.logging_utils import setup_logging
from rag_solution.file_management.database import Base, engine
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.generation.providers.factory import LLMProviderFactory, LLMBase

@pytest.fixture
def test_client(base_user):
    """Create a test client with mocked authentication."""
    def mock_verify_token(token):
        return {
            "sub": base_user.ibm_id,
            "email": base_user.email,
            "name": base_user.name,
            "uuid": str(base_user.id),
            "role": "user"
        }
    
    with patch("core.authentication_middleware.verify_jwt_token", side_effect=mock_verify_token):
        client = TestClient(app)
        yield client

@pytest.fixture
def auth_headers():
    """Create authentication headers for test requests."""
    return {"Authorization": "Bearer test_token"}

@pytest.fixture(autouse=True)
def capture_logs(caplog):
    caplog.set_level(logging.INFO)

@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for tests."""
    setup_logging()
    
    # Set root logger to DEBUG for tests
    logging.getLogger().setLevel(logging.DEBUG)
    
    # Configure specific loggers
    loggers_config = {
        # Keep SQL and HTTP loggers at CRITICAL to reduce noise
        'sqlalchemy': logging.CRITICAL,
        'sqlalchemy.engine': logging.CRITICAL,
        'sqlalchemy.engine.base.Engine': logging.CRITICAL,
        'sqlalchemy.dialects': logging.CRITICAL,
        'sqlalchemy.pool': logging.CRITICAL,
        'sqlalchemy.orm': logging.CRITICAL,
        'urllib3': logging.CRITICAL,
        'asyncio': logging.CRITICAL,
        'aiohttp': logging.CRITICAL,
        # Set IBM Watson logger to DEBUG to see API interactions
        'ibm_watsonx_ai': logging.DEBUG,
        # Set our loggers to DEBUG
        'llm.providers': logging.DEBUG,
        'tests.conftest': logging.DEBUG
    }
    
    for logger_name, level in loggers_config.items():
        logging.getLogger(logger_name).setLevel(level)

from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.schemas.llm_provider_schema import (
    LLMProviderInput,
    LLMProviderModelInput,
    ModelType
)
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType
from rag_solution.models.user_collection import UserCollection
from rag_solution.models.user_team import UserTeam
from rag_solution.models.file import File
from rag_solution.models.collection import Collection
from rag_solution.models.team import Team
from rag_solution.models.user import User
from rag_solution.models.llm_provider import LLMProvider, LLMProviderModel
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.repository.llm_parameters_repository import LLMParametersRepository
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.repository.pipeline_repository import PipelineConfigRepository
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput, LLMParametersOutput
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType
from rag_solution.models.question import SuggestedQuestion
from rag_solution.models.pipeline import PipelineConfig
from rag_solution.services.user_service import UserService
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.question_service import QuestionService
from rag_solution.services.search_service import SearchService
from rag_solution.schemas.user_schema import UserInput
from rag_solution.schemas.collection_schema import CollectionInput, CollectionStatus
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.generation.providers.watsonx import WatsonXLLM  # Import to trigger registration
from vectordbs.vector_store import VectorStore
from core.logging_utils import get_logger

logger = get_logger("tests.conftest")

# -------------------------------------------
# 🛠️ vector database fixture
# -------------------------------------------
@pytest.fixture(scope="function")
def vector_store():
    """Initialize and return a vector store instance for testing."""
    from vectordbs.milvus_store import MilvusStore

    store = MilvusStore()
    store._connect(settings.milvus_host, settings.milvus_port)
    yield store
    # Clean up after the test


# -------------------------------------------
# 🛠️ Service Fixtures
# -------------------------------------------
@pytest.fixture
def user_service(db_session: Session) -> UserService:
    """Create user service fixture."""
    return UserService(db_session)


@pytest.fixture
def collection_service(db_session: Session) -> CollectionService:
    """Create collection service fixture."""
    return CollectionService(db_session)

@pytest.fixture
def search_service(db_session: Session):
    """Create an instance of SearchService."""
    return SearchService(db_session)

@pytest.fixture
def question_service(db_session: Session) -> QuestionService:
    """Create question service fixture."""
    return QuestionService(db_session)


@pytest.fixture
def prompt_template_service(db_session: Session) -> PromptTemplateService:
    """Create prompt template service fixture."""
    return PromptTemplateService(db_session)


@pytest.fixture
def llm_parameters_service(db_session: Session) -> LLMParametersService:
    """Create LLM parameters service fixture."""
    return LLMParametersService(db_session)

@pytest.fixture
def get_watsonx(provider_factory: LLMProviderFactory) -> LLMBase:
    """Create watsonx provider"""
    return provider_factory.get_provider("watsonx")

# -------------------------------------------
# 🧪 Model Fixtures
# -------------------------------------------
@pytest.fixture
def base_user(db_session: Session) -> User:
    """Create test user."""
    user = User(
        ibm_id=f"test_user_{uuid4()}",  # Ensure unique ibm_id for each test
        email="test@example.com",
        name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def base_collection(db_session: Session, base_user: User) -> Collection:
    """Create a base collection model."""
    collection_service = CollectionService(db_session)
    collection_input = CollectionInput(
        name="Test Collection",
        is_private=False,
        users=[base_user.id],
        status=CollectionStatus.COMPLETED
    )
    return collection_service.create_collection(collection_input)

@pytest.fixture
def base_file_with_content(db_session: Session, base_collection: Collection, base_user: User) -> File:
    """Create a base file with content for testing."""
    from rag_solution.services.file_management_service import FileManagementService
    from rag_solution.schemas.file_schema import FileInput
    
    service = FileManagementService(db_session)
    file_input = FileInput(
        collection_id=base_collection.id,
        filename="test.txt",
        file_path="/tmp/test.txt",
        file_type="text/plain",
        metadata={
            "total_pages": 1,
            "total_chunks": 1,
            "keywords": {"test": True}
        },
        document_id=str(uuid4())
    )
    return service.create_file(file_input, base_user.id)

@pytest.fixture
def base_llm_parameters(db_session: Session, base_user: User) -> LLMParametersOutput:
    """Create default LLM parameters using repository (ensures business logic is followed)."""
    repository = LLMParametersRepository(db_session)

    params_input = LLMParametersInput(
        name="default",
        description="Default test parameters",
        max_new_tokens=1000,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        repetition_penalty=1.1,
        is_default=True
    )

    # ✅ Use repository to create parameters
    created_params = repository.create(base_user.id, params_input)  # This should return LLMParametersOutput

    return created_params  # ✅ Returns a Pydantic model (good)

@pytest.fixture
def base_file(db_session: Session, base_collection: Collection, base_user: User) -> File:
    """Create a base file for testing."""
    from rag_solution.services.file_management_service import FileManagementService
    from rag_solution.schemas.file_schema import FileInput
    
    service = FileManagementService(db_session)
    file_input = FileInput(
        collection_id=base_collection.id,
        filename="test.txt",
        file_path="/tmp/test.txt",
        file_type="text/plain",
        metadata=None,
        document_id=str(uuid4())
    )
    return service.create_file(file_input, base_user.id)

@pytest.fixture
def base_prompt_template(db_session: Session, base_user: User) -> PromptTemplate:
    """Create a base prompt template model."""
    template = PromptTemplate(
        name="test-question-template",
        provider="watsonx",
        template_type=PromptTemplateType.QUESTION_GENERATION,
        user_id=base_user.id,
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
        input_variables={"context": "Retrieved passages from knowledge base", "num_questions": "Number of questions to generate"},
        example_inputs={
            "context": "Python supports multiple programming paradigms.",
            "num_questions": 3
        },
        is_default=True
    )
    db_session.add(template)
    db_session.commit()
    return template

@pytest.fixture
def base_suggested_question(db_session: Session, base_collection: Collection) -> SuggestedQuestion:
    """Create a base suggested question model."""
    question = SuggestedQuestion(
        collection_id=base_collection.id,
        question="What is Python used for in software development?",
        is_valid=True
    )
    db_session.add(question)
    db_session.commit()
    return question

@pytest.fixture
def llm_provider(db_session: Session) -> str:
    """Returns the default LLM provider name configured for testing."""
    return "watsonx"  # Default provider for tests

@pytest.fixture
def provider_factory(db_session: Session) -> LLMProviderFactory:
    """Create a provider factory for testing."""
    return LLMProviderFactory(db_session)

@pytest.fixture
def provider(
    ensure_watsonx_provider,  # Ensure the provider is registered
    provider_factory: LLMProviderFactory,
    # ensure_watsonx_provider,  # Ensure the provider is registered
    llm_provider: str,
    llm_parameters_service: LLMParametersService,
    prompt_template_service: PromptTemplateService
) -> LLMProvider:
    """Get configured provider instance for testing."""
    provider = provider_factory.get_provider(llm_provider)
    provider._llm_parameters_service = llm_parameters_service
    provider._prompt_template_service = prompt_template_service
    return provider

@pytest.fixture
def initialize_factory(db_session):
    """Initialize LLMProviderFactory with database session."""
    return LLMProviderFactory(db_session)

@pytest.fixture
def test_config(db_session: Session, base_user, base_collection):
    """Create test configurations for user."""
    parameters_service = LLMParametersService(db_session)
    template_service = PromptTemplateService(db_session)
    pipeline_repository = PipelineConfigRepository(db_session)
    provider_service = LLMProviderService(db_session)
    
    # Get existing WatsonX provider
    watsonx_provider = provider_service.get_provider_by_name("watsonx")
    if not watsonx_provider:
        raise ValueError("WatsonX provider not found")

    parameters_input = LLMParametersInput(
        name="test-parameters",
        temperature=0.7,
        max_new_tokens=1000,
        top_k=50,
        top_p=0.95,
        is_default=True
    )
    parameters = parameters_service.create_or_update_parameters(
        base_user.id,
        parameters_input
    )

    templates = {}
    for template_type in [PromptTemplateType.RAG_QUERY, PromptTemplateType.RESPONSE_EVALUATION]:
        template_input = PromptTemplateInput(
            name=f"test-{template_type.value}",
            provider="watsonx",
            template_type=template_type,
            template_format="Context:\n{context}\nQuestion:{question}",
            input_variables={"context": "Retrieved passages from knowledge base", "question": "User's question to answer"},
            is_default=True
        )
        templates[template_type] = template_service.create_or_update_template(
            base_user.id,
            template_input
        )

    pipeline_config = pipeline_repository.create({
        "name": "test-pipeline",
        "description": "Test pipeline configuration",
        "chunking_strategy": "fixed",
        "embedding_model": "sentence-transformers/all-minilm-l6-v2",
        "retriever": "vector",
        "context_strategy": "simple",
        "provider_id": watsonx_provider.id,  # Use existing WatsonX provider ID
        "collection_id": base_collection.id,
        "enable_logging": True,
        "max_context_length": 2048,
        "timeout": 30.0
    })

    return {
        'parameters': parameters,
        'templates': templates,
        'pipeline': pipeline_config
    }

# -------------------------------------------
# 🧪 Test Data Fixtures
# -------------------------------------------
@pytest.fixture
def test_documents() -> List[str]:
    """Create test document texts."""
    return [
        "Python is a high-level programming language created by Guido van Rossum in 1991. "
        "It is widely used in software development, data science, and artificial intelligence. "
        "Python is known for its simplicity, readability, and extensive standard library.",
        
        "Python supports multiple programming paradigms, including procedural, "
        "object-oriented, and functional programming. Its design philosophy emphasizes "
        "code readability with the use of significant indentation and clean syntax.",
        
        "The Python Package Index (PyPI) contains over 300,000 packages for various "
        "programming tasks. Popular frameworks like Django and Flask are used for "
        "web development, while libraries like NumPy and Pandas are essential for "
        "data analysis."
    ]

@pytest.fixture
def test_questions() -> List[str]:
    """Create test questions."""
    return [
        "What is Python?",
        "Who created Python and when?",
        "What programming paradigms does Python support?",
        "Why is Python known for its readability?"
    ]

@pytest.fixture
def test_prompt_template_data(base_user: User) -> dict:
    """Create test prompt template data."""
    return {
        "name": "test-question-template",
        "provider": "watsonx",
        "template_type": PromptTemplateType.QUESTION_GENERATION,
        "system_prompt": (
            "You are an AI assistant that generates relevant questions based on "
            "the given context. Generate clear, focused questions that can be "
            "answered using the information provided."
        ),
        "template_format": (
            "{context}\n\n"
            "Generate {num_questions} specific questions that can be answered "
            "using only the information provided above."
        ),
        "input_variables": {"context": "Retrieved passages from knowledge base", "num_questions": "Number of questions to generate"},
        "example_inputs": {
            "context": "Python supports multiple programming paradigms.",
            "num_questions": 3
        },
        "is_default": True
    }

@pytest.fixture(scope="function")
def indexed_documents(vector_store, base_collection, base_file, get_watsonx):
    """Add documents to the vector store and return the collection name."""
    from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source

    # Create a document from the base_file fixture
    text = "Sample text from the file."  # Define the text as a string
    document = Document(
        document_id=base_file.document_id or str(uuid4()),
        name=base_file.filename,
        chunks=[
            DocumentChunk(
                chunk_id=f"chunk_{base_file.filename}",
                text="Sample text from the file.",
                embeddings=get_watsonx.get_embeddings([text])[0],
                metadata=DocumentChunkMetadata(
                    source=Source.OTHER,
                    document_id=base_file.document_id or str(uuid4()),
                    page_number=1,
                    chunk_number=1,
                    start_index=0,
                    end_index=len("Sample text from the file.")
                )
            )
        ]
    )

    # Add the document to the vector store
    vector_store.delete_collection(base_collection.vector_db_name)  # Clean up any existing collection
    vector_store.create_collection(base_collection.vector_db_name, {"embedding_model": settings.embedding_model})
    vector_store.add_documents(base_collection.vector_db_name, [document])

    yield base_collection.vector_db_name  # Return the collection name for use in tests

    # Clean up after the test
    vector_store.delete_collection(base_collection.vector_db_name)

# -------------------------------------------
# 🛠️ Session-level Database Engine Fixture
# -------------------------------------------
@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """Initialize the database for the test session."""
    with engine.connect() as conn:
        try:
            # Create tables if they don't exist
            logger.info("Creating tables if they don't exist.")
            Base.metadata.create_all(bind=engine)
            conn.commit()
        except Exception as e:
            logger.error(f"Error during DB setup: {e}")
            raise

    yield engine


# -------------------------------------------
# 🛠️ Function-level Database Session Fixture
# -------------------------------------------
@pytest.fixture(scope="function")
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Provide a fresh SQLAlchemy session for each test."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()

    try:
        yield session
        session.commit()  # Commit transactions at the end of the test
    except Exception as e:
        session.rollback()  # Rollback if any error occurs
        raise
    finally:
        session.close()  # Always close the session after the test

# -------------------------------------------
# 🛡️ Ensure WatsonX Provider Configuration
# -------------------------------------------
@pytest.fixture(autouse=True)
def ensure_watsonx_provider(db_session: Session, base_user: User) -> None:
    """Ensure WatsonX provider is configured."""
    provider_service = LLMProviderService(db_session)
    logger = get_logger("tests.conftest")
    
    try:
        # Clean up any existing providers
        logger.info("Cleaning up existing providers...")
        db_session.query(LLMProviderModel).delete()
        db_session.query(LLMProvider).delete()
        db_session.commit()
        
        # Use default values for testing if settings are not available
        api_key = settings.wx_api_key or "vOP8jN6QNnWXR2HJGguzs1AvGOdadZY3_ppjwV-jJfjg"
        logger.debug(f"Using API key type: {type(api_key)}, length: {len(str(api_key))}")

        provider_input = LLMProviderInput(
            name="watsonx",
            base_url=settings.wx_url or "https://us-south.ml.cloud.ibm.com",
            api_key=SecretStr(api_key),
            project_id=settings.wx_project_id or "3f77f23d-71b7-426b-ae13-bc4710769880"
        )

        # Create provider
        logger.info("Creating provider...")
        provider = provider_service.create_provider(provider_input)
        if not provider:
            raise RuntimeError("Provider creation returned None")
        
        logger.debug(f"Created provider with ID: {provider.id}")
        logger.debug(f"Provider API key type: {type(provider.api_key)}, length: {len(str(provider.api_key))}")
        logger.debug(f"Provider is_active: {provider.is_active}")

        # Use default model ID for testing if not set
        default_model = "ibm/granite-3-8b-instruct"
        
        # Create generation model
        logger.info("Creating generation model...")
        gen_model_input = LLMProviderModelInput(
            provider_id=provider.id,
            model_id=settings.rag_llm or default_model,
            default_model_id=settings.rag_llm or default_model,
            model_type=ModelType.GENERATION,
            timeout=30,
            max_retries=3,
            batch_size=10,
            retry_delay=1.0,
            concurrency_limit=10,
            stream=False,
            rate_limit=10,
            is_default=True,
            is_active=True
        )
        provider_service.create_provider_model(gen_model_input)

        # Create embedding model
        logger.info("Creating embedding model...")
        embed_model_input = LLMProviderModelInput(
            provider_id=provider.id,
            model_id="sentence-transformers/all-minilm-l6-v2",
            default_model_id="sentence-transformers/all-minilm-l6-v2",
            model_type=ModelType.EMBEDDING,
            timeout=30,
            max_retries=3,
            batch_size=10,
            retry_delay=1.0,
            concurrency_limit=10,
            stream=False,
            rate_limit=10,
            is_default=True,
            is_active=True
        )
        provider_service.create_provider_model(embed_model_input)
        
        logger.info("Successfully configured WatsonX provider and models")
        
    except Exception as e:
        logger.error(f"Failed to configure WatsonX provider: {e}")
        # Clean up on failure
        db_session.rollback()
        try:
            db_session.query(LLMProviderModel).delete()
            db_session.query(LLMProvider).delete()
            db_session.commit()
        except Exception as cleanup_error:
            logger.error(f"Cleanup after failure also failed: {cleanup_error}")
        raise

    # Create templates
    template_service = PromptTemplateService(db_session)
    
    # Create RAG query template
    template_service.create_or_update_template(
        base_user.id,
        PromptTemplateInput(
            name="default-rag-template",
            provider="watsonx",
            template_type=PromptTemplateType.RAG_QUERY,
            system_prompt="You are a helpful AI assistant specializing in answering questions based on the given context.",
            template_format="{context}\n\n{question}",
            input_variables={
                "context": "Retrieved context for answering the question",
                "question": "User's question to answer"
            },
            example_inputs={
                "context": "Python was created by Guido van Rossum.",
                "question": "Who created Python?"
            },
            is_default=True,
            validation_schema={
                "model": "PromptVariables",
                "fields": {
                    "context": {"type": "str", "min_length": 1},
                    "question": {"type": "str", "min_length": 1}
                },
                "required": ["context", "question"]
            }
        )
    )

    # Create question generation template
    template_service.create_or_update_template(
        base_user.id,
        PromptTemplateInput(
            name="default-question-template",
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
                "num_questions": "Number of questions to generate"
            },
            example_inputs={
                "context": "Python supports multiple programming paradigms.",
                "num_questions": 3
            },
            is_default=True,
            validation_schema={
                "model": "PromptVariables",
                "fields": {
                    "context": {"type": "str", "min_length": 1},
                    "num_questions": {"type": "int", "gt": 0}
                },
                "required": ["context", "num_questions"]
            }
        )
    )


# -------------------------------------------
# 🧼 Autouse Fixture for Database Cleanup
# -------------------------------------------
@pytest.fixture(autouse=True)
def clean_db(db_session: Session, base_user: User):
    """Clean up the database before and after each test."""
    try:
        logger.info("Initial database cleanup.")
        db_session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        
        # Clean up in correct order (respect foreign key relationships)
        tables_to_clean = [
            (UserCollection, "UserCollection"),
            (UserTeam, "UserTeam"),
            (File, "File"),
            (SuggestedQuestion, "SuggestedQuestion"),
            (PipelineConfig, "PipelineConfig"),
            (Collection, "Collection"),
            (Team, "Team"),
            (LLMProviderModel, "LLMProviderModel"),
            (LLMProvider, "LLMProvider"),
            (LLMParameters, "LLMParameters"),
            (PromptTemplate, "PromptTemplate")
            # User table removed to preserve base_user
        ]
        
        for model, name in tables_to_clean:
            try:
                count = db_session.query(model).delete()
                logger.debug(f"Deleted {count} rows from {name}")
            except Exception as e:
                logger.error(f"Error cleaning {name}: {e}")
                raise
                
        db_session.commit()
    except Exception as e:
        logger.error(f"Error during initial database cleanup: {e}")
        db_session.rollback()
        raise

    yield  # Let the test run

    try:
        logger.info("Final database cleanup.")
        db_session.rollback()  # Rollback any uncommitted changes
        db_session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        
        # Clean up again in same order
        for model, name in tables_to_clean:
            try:
                count = db_session.query(model).delete()
                logger.debug(f"Deleted {count} rows from {name}")
            except Exception as e:
                logger.error(f"Error cleaning {name}: {e}")
                raise
                
        db_session.commit()
    except Exception as e:
        logger.error(f"Error during final database cleanup: {e}")
        db_session.rollback()
        raise
