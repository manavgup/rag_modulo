from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput


class LLMParametersRepository:
    """
    Repository for managing LLM Parameters in the database.
    Provides CRUD operations and utility methods.
    """

    def __init__(self, db: Session):
        self.db = db

    # 📝 Create or Update by Collection ID
    def create_or_update_by_user_id(self, user_id: UUID, params: LLMParametersInput) -> LLMParameters:
        """Create or update LLM Parameters for a specific user."""
        db_params = (
            self.db.query(LLMParameters)
            .filter(LLMParameters.user_id == user_id)
            .filter(LLMParameters.name == params.name)
            .first()
        )

        if db_params:
            # Update existing
            for field, value in params.model_dump(exclude_unset=True).items():
                setattr(db_params, field, value)
        else:
            # Create new
            db_params = LLMParameters(**params.model_dump(exclude={'user_id'}), user_id=user_id)

        self.db.add(db_params)
        self.db.commit()
        self.db.refresh(db_params)
        return db_params

    # 🔍 Get by ID
    def get_by_id(self, id: UUID) -> Optional[LLMParameters]:
        """Fetch LLM Parameters by ID."""
        return self.db.query(LLMParameters).filter(LLMParameters.id == id).first()

    # 🔍 Get by Collection ID
    def get_by_user_id(self, user_id: UUID) -> List[LLMParameters]:
        """Fetch all LLM Parameters for a user."""
        return (
            self.db.query(LLMParameters)
            .filter(LLMParameters.user_id == user_id)
            .all()
        )

    # 🌟 Get Default Parameters
    def get_user_default(self, user_id: UUID) -> Optional[LLMParameters]:
        """Fetch Default LLM Parameters for a user."""
        return (
            self.db.query(LLMParameters)
            .filter(LLMParameters.user_id == user_id)
            .filter(LLMParameters.is_default == True)
            .first()
        )

    # 🛠️ Update
    def update(self, id: UUID, params: LLMParametersInput) -> Optional[LLMParameters]:
        """Update existing LLM Parameters."""
        db_params = self.get_by_id(id)
        if not db_params:
            return None

        for field, value in params.model_dump(exclude_unset=True).items():
            setattr(db_params, field, value)

        self.db.commit()
        self.db.refresh(db_params)
        return db_params

    # 🗑️ Delete by ID
    def delete(self, id: UUID) -> bool:
        """Delete LLM Parameters by ID."""
        db_params = self.get_by_id(id)
        if not db_params:
            return False

        self.db.delete(db_params)
        self.db.commit()
        return True

    # 🗑️ Delete by Collection ID
    def delete_by_user_id(self, user_id: UUID) -> bool:
        """Delete all LLM Parameters for a user."""
        result = (
            self.db.query(LLMParameters)
            .filter(LLMParameters.user_id == user_id)
            .delete()
        )
        self.db.commit()
        return True
