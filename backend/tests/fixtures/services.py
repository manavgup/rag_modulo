"""Core service fixtures for pytest."""

from uuid import uuid4
import pytest
from fastapi import HTTPException
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker
from pydantic import SecretStr
from uuid import UUID

from core.config import settings
from rag_solution.services.user_service import UserService
from rag_solution.services.llm_provider_service import LLMProviderService, LLMProviderInput
from rag_solution.services.llm_model_service import LLMModelService, LLMModelInput, ModelType
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.prompt_template_service import PromptTemplateService, PromptTemplateInput, PromptTemplateType
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.question_service import QuestionService
from rag_solution.services.search_service import SearchService
from rag_solution.services.team_service import TeamService
from rag_solution.services.user_team_service import UserTeamService
from rag_solution.schemas.user_schema import UserInput, UserOutput
from rag_solution.services.user_collection_service import UserCollectionService
from core.logging_utils import get_logger

logger = get_logger("tests.fixtures.services")

# Base Services
@pytest.fixture
def user_service(db_session: Session):
    """Initialize UserService."""
    return UserService(db_session)

@pytest.fixture
def user_team_service(db_session: Session):
    return UserTeamService(db_session)

@pytest.fixture
def llm_provider_service(db_session: Session):
    """Initialize LLMProviderService."""
    return LLMProviderService(db_session)

@pytest.fixture
def llm_model_service(db_session: Session):
    """Initialize LLMModelService."""
    return LLMModelService(db_session)

@pytest.fixture
def llm_provider():
    """hard coded watsonx provider name for now."""
    return "watsonx"

@pytest.fixture
def llm_parameters_service(db_session: Session):
    """Initialize LLMParametersService."""
    return LLMParametersService(db_session)

@pytest.fixture
def prompt_template_service(db_session: Session):
    """Initialize PromptTemplateService."""
    return PromptTemplateService(db_session)

@pytest.fixture(scope="session")
def collection_service(session_db: Session):
    """Initialize CollectionService."""
    return CollectionService(session_db)

@pytest.fixture(scope="session")
def user_collection_service(session_db: Session):
    return UserCollectionService(session_db)

@pytest.fixture
def file_service(db_session: Session):
    """Initialize FileManagementService."""
    return FileManagementService(db_session)

@pytest.fixture
def pipeline_service(db_session: Session):
    """Initialize PipelineService."""
    return PipelineService(db_session)

@pytest.fixture(scope="session")
def question_service(session_db: Session):
    """Initialize QuestionService."""
    return QuestionService(session_db)

@pytest.fixture(scope="session")
def search_service(session_db: Session):
    """Initialize SearchService."""
    return SearchService(session_db)

@pytest.fixture(scope="session")
def team_service(session_db: Session):
    """Initialize TeamService."""
    return TeamService(session_db)

@pytest.fixture(scope="session")
def session_llm_provider_service(db_engine: Engine):
    """Session-scoped LLM provider service."""
    session = sessionmaker(bind=db_engine)()
    return LLMProviderService(session)

@pytest.fixture(scope="session")
def session_llm_model_service(db_engine: Engine):
    """Session-scoped LLM model service."""
    session = sessionmaker(bind=db_engine)()
    return LLMModelService(session)

@pytest.fixture(scope="session")
def session_db(db_engine: Engine) -> Session:
    """Create a session-scoped database session."""
    session = sessionmaker(bind=db_engine)()
    yield session
    session.close()


@pytest.fixture(scope="session")
def session_user_service(session_db: Session):
    """Initialize session-scoped UserService."""
    return UserService(session_db)

@pytest.fixture(scope="session")
def session_llm_model_service(session_db: Session):
    """Initialize session-scoped LLMModelService."""
    return LLMModelService(session_db)

@pytest.fixture(scope="session")
def session_llm_provider_service(session_db: Session):
    """Initialize session-scoped LLMProviderService."""
    return LLMProviderService(session_db)

@pytest.fixture(scope="session")
def session_llm_parameters_service(session_db: Session):
    """Initialize session-scoped LLMParametersService."""
    return LLMParametersService(session_db)


@pytest.fixture(scope="session")
def session_prompt_template_service(session_db: Session):
    """Initialize session-scoped PromptTemplateService."""
    return PromptTemplateService(session_db)

@pytest.fixture(scope="session")
def ensure_watsonx_provider(
    session_llm_provider_service: LLMProviderService, 
    session_llm_model_service: LLMModelService
):
    """Ensure WatsonX provider and models are configured."""
    try:
        # First try to get existing provider
        provider = session_llm_provider_service.get_provider_by_name("watsonx")
        if provider:
            return provider
        
        # Create provider
        provider_input = LLMProviderInput(
            name="watsonx",
            base_url=settings.wx_url or "https://us-south.ml.cloud.ibm.com",
            api_key=SecretStr(settings.wx_api_key or "test_key"),
            project_id=settings.wx_project_id or "test_project",
            is_default=True
        )
        provider = session_llm_provider_service.create_provider(provider_input)
        
        # Create generation model
        gen_model = LLMModelInput(
            provider_id=provider.id,
            model_id=settings.rag_llm or "ibm/granite-3-8b-instruct",
            default_model_id=settings.rag_llm or "ibm/granite-3-8b-instruct",
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
        session_llm_model_service.create_model(gen_model)
        
        # Create embedding model
        embed_model = LLMModelInput(
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
        session_llm_model_service.create_model(embed_model)
        
        logger.info("Successfully configured WatsonX provider")
        return provider
        
    except Exception as e:
        logger.error(f"Failed to configure WatsonX provider: {e}")
        raise

@pytest.fixture(scope="session", autouse=True)
def init_providers(
    session_db,
    ensure_watsonx_provider,  # Gives us provider and models
    ensure_watsonx_models,    # Ensures models are created
    base_prompt_template,     # Base template from prompt_template.py
    base_rag_prompt_template,      # RAG template from prompt_template.py
    base_question_gen_template,    # Question gen template from prompt_template.py
    base_llm_parameters,      # Default parameters from llm.py
):
    """Initialize test providers and related configurations.
    
    This fixture coordinates all the required test configurations by depending on
    other fixtures that set up specific components.
    """
    # All the setup is handled by the dependent fixtures
    # We just need to ensure everything is committed
    session_db.commit()
    
    # Return provider in case other fixtures need it
    return ensure_watsonx_provider
    
@pytest.fixture(scope="session")
def base_user(db_engine: Engine, ensure_watsonx_provider) -> UserOutput:
    """Create a test user once for the entire test session."""
    session = sessionmaker(bind=db_engine)()
    
    try:
        # Delete in correct order to handle foreign key constraints
        cleanup_statements = [
            "DELETE FROM user_collection",
            "DELETE FROM user_team",
            "DELETE FROM prompt_templates",
            "DELETE FROM llm_parameters",
            "DELETE FROM files",
            "DELETE FROM users"  # Now safe to delete users
        ]
        
        for stmt in cleanup_statements:
            session.execute(text(stmt))
            
        session.commit()
        
        user_service = UserService(session)
        test_id = UUID('00000000-0000-4000-a000-000000000001')  # Fixed UUID
        
        user = user_service.create_user(UserInput(
            id=test_id,
            email="test@example.com",
            ibm_id=f"test_user_{test_id}",
            name="Test User",
            role="user"
        ))
        print(f"Created base user with ID: {user.id}")  # Debug print
        session.commit()
        return user
        
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
