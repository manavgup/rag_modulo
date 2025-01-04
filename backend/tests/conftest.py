"""Pytest configuration and shared fixtures."""

import logging
import os
import pytest
from sqlalchemy.orm import scoped_session, sessionmaker, Session

from core.config import settings
from rag_solution.file_management.database import Base, engine
from rag_solution.services.provider_config_service import ProviderConfigService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.schemas.llm_parameters_schema import LLMParametersCreate
from rag_solution.schemas.provider_config_schema import ProviderConfig, ProviderRuntimeSettings
from rag_solution.schemas.prompt_template_schema import PromptTemplateCreate
from rag_solution.models.user_collection import UserCollection
from rag_solution.models.user_team import UserTeam
from rag_solution.models.file import File
from rag_solution.models.collection import Collection
from rag_solution.models.team import Team
from rag_solution.models.user import User
from rag_solution.models.user_provider_preference import UserProviderPreference
from rag_solution.models.provider_config import ProviderModelConfig
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.question import SuggestedQuestion

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# -------------------------------------------
# 🛠️ Session-level Database Engine Fixture
# -------------------------------------------
@pytest.fixture(scope="session")
def db_engine():
    """Initialize the database for the test session."""
    with engine.connect() as conn:
        try:
            logger.info("Dropping all tables in Base.metadata.")
            Base.metadata.drop_all(bind=engine)
            logger.info("Recreating all tables in Base.metadata.")
            Base.metadata.create_all(bind=engine)
            conn.commit()
        except Exception as e:
            logger.error(f"Error during DB setup: {e}")
            raise

    yield engine

    # Cleanup after all tests
    with engine.connect() as conn:
        try:
            logger.info("Dropping all tables in Base.metadata during teardown.")
            Base.metadata.drop_all(bind=engine)
            conn.commit()
        except Exception as e:
            logger.error(f"Error during DB teardown: {e}")
            raise


# -------------------------------------------
# 🛠️ Function-level Database Session Fixture
# -------------------------------------------
@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provide a fresh database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    yield session

    transaction.rollback()
    session.close()
    connection.close()


# -------------------------------------------
# 🛡️ Ensure WatsonX Provider Configuration
# -------------------------------------------
@pytest.fixture(autouse=True)
def ensure_watsonx_provider(db_session: Session):
    """Ensure WatsonX provider is configured."""
    provider_service = ProviderConfigService(db_session)

    # Create parameters using schema
    params_schema = LLMParametersCreate(
        name="default-parameters",
        max_new_tokens=settings.max_new_tokens,
        temperature=settings.temperature,
        top_k=settings.top_k,
        top_p=settings.top_p,
        is_default=True
    )

    # Create runtime configuration
    runtime_config = ProviderRuntimeSettings(
        timeout=30,
        max_retries=3,
        batch_size=10,
        retry_delay=1.0,
        concurrency_limit=10,
        stream=False,
        rate_limit=10
    )

    # Create provider using schema
    provider_schema = ProviderConfig(
        model_id=settings.rag_llm,
        provider_name="watsonx",
        api_key=settings.wx_api_key or "dummy-api-key",
        api_url=settings.wx_url or "https://us-south.ml.cloud.ibm.com",
        project_id=settings.wx_project_id or "dummy-project-id",
        default_model_id=settings.rag_llm,
        embedding_model=settings.embedding_model,  # Add embedding model
        runtime=runtime_config,
        is_active=True
    )

    # Create template using schema
    template_schema = PromptTemplateCreate(
        name="default-template",
        provider="watsonx",
        description="Default RAG template for WatsonX",
        system_prompt="You are a helpful AI assistant specializing in answering questions based on the given context.",
        context_prefix="Context:",
        query_prefix="Question:",
        answer_prefix="Answer:",
        is_default=True,
        input_variables=["context", "question"],
        template_format="{question}"  # The question will be formatted with the context in the pipeline
    )

    # Register provider with parameters and create template
    provider = provider_service.register_provider_model(
        provider="watsonx",
        model_id=settings.rag_llm,
        parameters=params_schema,
        provider_config=provider_schema,
        prompt_template=template_schema
    )


# -------------------------------------------
# 🧼 Autouse Fixture for Database Cleanup
# -------------------------------------------
@pytest.fixture(autouse=True)
def clean_db(db_session):
    """Clean up the database before each test."""
    try:
        logger.info("Cleaning database tables in reverse dependency order.")
        # Delete in the correct order to avoid foreign key violations
        db_session.query(UserProviderPreference).delete()
        db_session.query(UserCollection).delete()
        db_session.query(UserTeam).delete()
        db_session.query(File).delete()
        db_session.query(Collection).delete()
        db_session.query(Team).delete()
        db_session.query(User).delete()
        db_session.query(SuggestedQuestion).delete()
        db_session.query(ProviderModelConfig).delete()
        db_session.query(LLMParameters).delete()
        db_session.query(PromptTemplate).delete()
        
        db_session.commit()
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}")
        db_session.rollback()
        raise


# -------------------------------------------
# ⚙️ Environment Variable Fixture
# -------------------------------------------
@pytest.fixture(autouse=True)
def env_setup():
    """Set up environment variables for testing."""
    os.environ['RAG_LLM'] = 'watsonx'
    os.environ['JWT_SECRET_KEY'] = 'test_secret_key'
    yield
