from typing import Any

from pydantic import UUID4
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from rag_solution.core.exceptions import ValidationError
from rag_solution.repository.user_provider_repository import UserProviderRepository
from rag_solution.schemas.llm_parameters_schema import LLMParametersOutput
from rag_solution.schemas.llm_provider_schema import LLMProviderOutput
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateOutput, PromptTemplateType
from rag_solution.services.llm_model_service import LLMModelService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.prompt_template_service import PromptTemplateService

logger = get_logger(__name__)


class UserProviderService:
    def __init__(self: Any, db: Session) -> None:
        self.db = db
        self.user_provider_repository = UserProviderRepository(db)
        self.prompt_template_service = PromptTemplateService(db)
        self.llm_model_service = LLMModelService(db)

    def initialize_user_defaults(self, user_id: UUID4) -> tuple[LLMProviderOutput | None, list[PromptTemplateOutput], LLMParametersOutput | None]:
        try:
            # Existing provider initialization
            provider = self.get_user_provider(user_id)
            if not provider:
                provider = self.user_provider_repository.get_default_provider()
                if provider:
                    self.user_provider_repository.set_user_provider(user_id, provider.id)
                else:
                    logger.error("❌ No default LLM provider found in the database!")
                    return None, [], None

            # Existing template initialization
            rag_template = self._create_default_rag_template(user_id)
            question_template = self._create_default_question_template(user_id)

            # Add parameters initialization
            parameters_service = LLMParametersService(self.db)
            default_parameters = parameters_service.initialize_default_parameters(user_id)
            if not default_parameters:
                logger.error("Failed to initialize default parameters")
                return None, [], None
            logger.info(f"Parameters initialized: {default_parameters.id}")

            # Initialize default pipeline
            pipeline_service = PipelineService(self.db)
            pipeline_service.initialize_user_pipeline(user_id, provider.id)

            self.db.commit()
            return provider, [rag_template, question_template], default_parameters

        except Exception as e:
            logger.error(f"Initialization error: {e!s}")
            self.db.rollback()
            raise ValidationError(f"Failed to initialize required user configuration: {e}", field="user_initialization") from e

    def get_user_provider(self, user_id: UUID4) -> LLMProviderOutput | None:
        """Get user's preferred provider or assign the default provider if missing."""
        try:
            logger.info(f"Fetching LLM provider for user {user_id}")

            # Step 1: Try to get the user existing provider
            provider = self.user_provider_repository.get_user_provider(user_id)
            if provider:
                logger.info(f"User {user_id} has provider: {provider.name}")
                return provider

            # Step 2: If no provider found, fetch the system default provider
            logger.warning(f"No provider found for user {user_id}, fetching default provider...")

            default_provider = self.user_provider_repository.get_default_provider()
            if not default_provider:
                logger.error("❌ No default LLM provider found in the database!")
                return None  # Prevents a hard failure, but logs an issue

            # Step 3: Assign the default provider (WatsonX) to the user
            logger.info(f"Assigning default provider {default_provider.name} to user {user_id}")
            self.set_user_provider(user_id, default_provider.id)
            return default_provider

        except Exception as e:
            logger.error(f"Error getting provider for user {user_id}: {e!s}")
            raise ValidationError(f"Error fetching provider: {e}", field="provider_retrieval") from e

    def set_user_provider(self, user_id: UUID4, provider_id: UUID4) -> bool:
        """Set user's preferred provider."""
        result = self.user_provider_repository.set_user_provider(user_id, provider_id)
        if not result:
            raise ValidationError(f"User not found: {user_id}", field="user_id")
        return True

    def _create_default_rag_template(self, user_id: UUID4) -> PromptTemplateOutput:
        """Create default RAG template for user."""
        return self.prompt_template_service.create_template(
            PromptTemplateInput(
                name="default-rag-template",
                user_id=user_id,
                template_type=PromptTemplateType.RAG_QUERY,
                system_prompt="You are a helpful AI assistant specializing in answering questions based on the given context.",
                template_format="{context}\n\n{question}",
                input_variables={
                    "context": "Retrieved context for answering the question",
                    "question": "User's question to answer",
                },
                example_inputs={
                    "context": "Python was created by Guido van Rossum.",
                    "question": "Who created Python?",
                },
                is_default=True,
                max_context_length=2048,  # Default context length
                validation_schema={
                    "model": "PromptVariables",
                    "fields": {
                        "context": {"type": "str", "min_length": 1},
                        "question": {"type": "str", "min_length": 1},
                    },
                    "required": ["context", "question"],
                },
            )
        )

    def _create_default_question_template(self, user_id: UUID4) -> PromptTemplateOutput:
        """Create default question generation template for user."""
        return self.prompt_template_service.create_template(
            PromptTemplateInput(
                name="default-question-template",
                user_id=user_id,
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
                max_context_length=2048,  # Default context length
                validation_schema={
                    "model": "PromptVariables",
                    "fields": {"context": {"type": "str", "min_length": 1}, "num_questions": {"type": "int", "gt": 0}},
                    "required": ["context", "num_questions"],
                },
            )
        )
