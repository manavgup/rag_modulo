"""Core service fixtures for pytest."""

from collections.abc import Generator
from uuid import uuid4

import pytest
from pydantic import UUID4, SecretStr
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from core.config import get_settings
from core.logging_utils import get_logger
from rag_solution.schemas.llm_parameters_schema import LLMParametersOutput
from rag_solution.schemas.llm_provider_schema import LLMProviderOutput
from rag_solution.schemas.prompt_template_schema import PromptTemplateOutput
from rag_solution.schemas.user_schema import UserInput, UserOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.llm_model_service import LLMModelInput, LLMModelService, ModelType
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderInput, LLMProviderService
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.question_service import QuestionService
from rag_solution.services.search_service import SearchService
from rag_solution.services.team_service import TeamService
from rag_solution.services.user_collection_service import UserCollectionService
from rag_solution.services.user_service import UserService
from rag_solution.services.user_team_service import UserTeamService

logger = get_logger("tests.fixtures.services")


# Base Services
@pytest.fixture
def user_service(db_session: Session) -> UserService:
    """Initialize UserService."""
    settings = get_settings()
    return UserService(db_session, settings)


@pytest.fixture
def user_team_service(db_session: Session) -> UserTeamService:
    settings = get_settings()
    return UserTeamService(db_session, settings)


@pytest.fixture
def llm_provider_service(db_session: Session) -> LLMProviderService:
    """Initialize LLMProviderService."""
    settings = get_settings()
    return LLMProviderService(db_session, settings)


@pytest.fixture
def llm_model_service(db_session: Session) -> LLMModelService:
    """Initialize LLMModelService."""
    settings = get_settings()
    return LLMModelService(db_session, settings)


@pytest.fixture
def llm_provider() -> str:
    """hard coded watsonx provider name for now."""
    return "watsonx"


@pytest.fixture
def llm_parameters_service(db_session: Session) -> LLMParametersService:
    """Initialize LLMParametersService."""
    settings = get_settings()
    return LLMParametersService(db_session, settings)


@pytest.fixture
def prompt_template_service(db_session: Session) -> PromptTemplateService:
    """Initialize PromptTemplateService."""
    settings = get_settings()
    return PromptTemplateService(db_session, settings)


@pytest.fixture(scope="session")
def collection_service(session_db: Session) -> CollectionService:
    """Initialize CollectionService."""
    settings = get_settings()
    return CollectionService(session_db, settings)


@pytest.fixture(scope="session")
def user_collection_service(session_db: Session) -> UserCollectionService:
    settings = get_settings()
    return UserCollectionService(session_db, settings)


@pytest.fixture
def file_service(db_session: Session) -> FileManagementService:
    """Initialize FileManagementService."""
    settings = get_settings()
    return FileManagementService(db_session, settings)


@pytest.fixture
def pipeline_service(db_session: Session) -> PipelineService:
    """Initialize PipelineService."""
    settings = get_settings()
    return PipelineService(db_session, settings)


@pytest.fixture(scope="session")
def question_service(session_db: Session) -> QuestionService:
    """Initialize QuestionService."""
    settings = get_settings()
    return QuestionService(session_db, settings)


@pytest.fixture(scope="session")
def search_service(session_db: Session) -> SearchService:
    """Initialize SearchService."""
    settings = get_settings()
    return SearchService(session_db, settings)


@pytest.fixture(scope="session")
def team_service(session_db: Session) -> TeamService:
    """Initialize TeamService."""
    settings = get_settings()
    return TeamService(session_db, settings)


@pytest.fixture(scope="session")
def session_llm_provider_service(db_engine: Engine) -> LLMProviderService:
    """Session-scoped LLM provider service."""
    session = sessionmaker(bind=db_engine)()
    settings = get_settings()
    return LLMProviderService(session, settings)


@pytest.fixture(scope="session")
def session_llm_model_service(db_engine: Engine) -> LLMModelService:
    """Session-scoped LLM model service."""
    session = sessionmaker(bind=db_engine)()
    settings = get_settings()
    return LLMModelService(session, settings)


@pytest.fixture(scope="session")
def session_db(db_engine: Engine) -> Generator[Session, None, None]:
    """Create a session-scoped database session."""
    session = sessionmaker(bind=db_engine)()
    yield session
    session.close()


@pytest.fixture(scope="session")
def session_user_service(session_db: Session) -> UserService:
    """Initialize session-scoped UserService."""
    settings = get_settings()
    return UserService(session_db, settings)


@pytest.fixture(scope="session")
def session_llm_parameters_service(session_db: Session) -> LLMParametersService:
    """Initialize session-scoped LLMParametersService."""
    settings = get_settings()
    return LLMParametersService(session_db, settings)


@pytest.fixture(scope="session")
def session_prompt_template_service(session_db: Session) -> PromptTemplateService:
    """Initialize session-scoped PromptTemplateService."""
    settings = get_settings()
    return PromptTemplateService(session_db, settings)


@pytest.fixture(scope="session")
def ensure_watsonx_provider(session_llm_provider_service: LLMProviderService, session_llm_model_service: LLMModelService) -> LLMProviderOutput:
    """Ensure WatsonX provider and models are configured."""
    try:
        # First try to get existing provider
        provider_config = session_llm_provider_service.get_provider_by_name("watsonx")
        if provider_config:
            # Convert from LLMProviderConfig to LLMProviderOutput
            return LLMProviderOutput(  # type: ignore[return-value]
                id=provider_config.id,
                name=provider_config.name,
                base_url=provider_config.base_url,
                org_id=provider_config.org_id,
                project_id=provider_config.project_id,
                is_active=provider_config.is_active,
                is_default=provider_config.is_default,
                created_at=provider_config.created_at,
                updated_at=provider_config.updated_at,
            )

        # Create provider
        settings = get_settings()
        provider_input = LLMProviderInput(
            name="watsonx",
            base_url=settings.wx_url or "https://us-south.ml.cloud.ibm.com",
            api_key=SecretStr(settings.wx_api_key or "test_key"),
            project_id=settings.wx_project_id or "test_project",
            is_default=True,
            org_id="test_org",  # type: ignore[call-arg]
            is_active=True,  # type: ignore[call-arg]
            user_id=uuid4(),  # type: ignore[call-arg]
        )
        created_provider = session_llm_provider_service.create_provider(provider_input)

        # Create generation model
        gen_model = LLMModelInput(
            provider_id=created_provider.id,
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
            is_active=True,
        )
        session_llm_model_service.create_model(gen_model)

        # Create embedding model
        embed_model = LLMModelInput(
            provider_id=created_provider.id,
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
            is_active=True,
        )
        session_llm_model_service.create_model(embed_model)

        logger.info("Successfully configured WatsonX provider")
        return created_provider  # type: ignore[return-value]

    except Exception as e:
        logger.error(f"Failed to configure WatsonX provider: {e}")
        raise


@pytest.fixture(scope="session", autouse=True)
def init_providers(
    session_db: Session,
    ensure_watsonx_provider: LLMProviderOutput,  # Gives us provider and models
    ensure_watsonx_models: LLMProviderOutput,  # Ensures models are created
    base_prompt_template: PromptTemplateOutput,  # Base template from prompt_template.py
    base_rag_prompt_template: PromptTemplateOutput,  # RAG template from prompt_template.py
    base_question_gen_template: PromptTemplateOutput,  # Question gen template from prompt_template.py
    base_llm_parameters: LLMParametersOutput,  # Default parameters from llm.py
) -> LLMProviderOutput:
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
def base_user(db_engine: Engine, ensure_watsonx_provider: LLMProviderOutput) -> UserOutput:
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
            "DELETE FROM users",  # Now safe to delete users
        ]

        for stmt in cleanup_statements:
            session.execute(text(stmt))

        session.commit()

        settings = get_settings()
        user_service = UserService(session, settings)
        test_id = UUID4("00000000-0000-4000-a000-000000000001")  # Fixed UUID

        user = user_service.create_user(UserInput(id=test_id, email="test@example.com", ibm_id=f"test_user_{test_id}", name="Test User", role="user"))
        print(f"Created base user with ID: {user.id}")  # Debug print
        session.commit()
        return user

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
