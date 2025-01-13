from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List
from rag_solution.repository.llm_parameters_repository import LLMParametersRepository
from rag_solution.schemas.llm_parameters_schema import (
    LLMParametersInput,
    LLMParametersOutput,
    LLMParametersInDB
)
from rag_solution.models.llm_parameters import LLMParameters


class LLMParametersService:
    """
    Service layer for managing LLM Parameters.
    Handles business logic, validation, and repository interaction.
    """

    def __init__(self, db: Session):
        self.repository = LLMParametersRepository(db)

    # 📝 Create or Update Parameters
    def create_or_update_parameters(self, user_id: UUID, params: LLMParametersInput) -> LLMParametersOutput:
        """Create or update LLM Parameters for a user."""
        llm_params = self.repository.create_or_update_by_user_id(user_id, params)
        return LLMParametersOutput.model_validate({
            "id": llm_params.id,
            "user_id": llm_params.user_id,
            "name": llm_params.name,
            "description": llm_params.description,
            "max_new_tokens": llm_params.max_new_tokens,
            "temperature": llm_params.temperature,
            "top_k": llm_params.top_k,
            "top_p": llm_params.top_p,
            "repetition_penalty": llm_params.repetition_penalty,
            "is_default": llm_params.is_default,
            "created_at": llm_params.created_at,
            "updated_at": llm_params.updated_at
        })

    # 🔍 Fetch by Collection ID
    def get_parameters(self, user_id: UUID) -> Optional[LLMParametersOutput]:
        """Fetch LLM Parameters for a specific user."""
        llm_params = self.repository.get_by_user_id(user_id)
        if not llm_params:
            return None
        return LLMParametersOutput.model_validate({
            "id": llm_params.id,
            "user_id": llm_params.user_id,
            "name": llm_params.name,
            "description": llm_params.description,
            "max_new_tokens": llm_params.max_new_tokens,
            "temperature": llm_params.temperature,
            "top_k": llm_params.top_k,
            "top_p": llm_params.top_p,
            "repetition_penalty": llm_params.repetition_penalty,
            "is_default": llm_params.is_default,
            "created_at": llm_params.created_at,
            "updated_at": llm_params.updated_at
        })

    # 🗑️ Delete Parameters by Collection ID
    def delete_parameters(self, user_id: UUID) -> bool:
        """Delete LLM Parameters associated with a specific user."""
        return self.repository.delete_by_user_id(user_id)

    # 🔍 Fetch Default Parameters
    def get_user_default(self, user_id: UUID) -> Optional[LLMParametersOutput]:
        """Fetch default LLM Parameters for a user."""
        llm_params = self.repository.get_user_default(user_id)
        if not llm_params:
            return None
        return LLMParametersOutput.model_validate({
            "id": llm_params.id,
            "user_id": llm_params.user_id,
            "name": llm_params.name,
            "description": llm_params.description,
            "max_new_tokens": llm_params.max_new_tokens,
            "temperature": llm_params.temperature,
            "top_k": llm_params.top_k,
            "top_p": llm_params.top_p,
            "repetition_penalty": llm_params.repetition_penalty,
            "is_default": llm_params.is_default,
            "created_at": llm_params.created_at,
            "updated_at": llm_params.updated_at
        })
