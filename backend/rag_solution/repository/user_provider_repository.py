import logging
from uuid import UUID
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from rag_solution.models.user import User
from rag_solution.models.llm_provider import LLMProvider
from rag_solution.schemas.llm_provider_schema import LLMProviderOutput
from core.logging_utils import get_logger

logger = get_logger(__name__)

class UserProviderRepository:
    def __init__(self, db: Session):
        self.db = db

    def set_user_provider(self, user_id: UUID, provider_id: UUID, outer_transaction=None) -> bool:
        transaction = outer_transaction or self.db.begin_nested()
        try:
            user = self.db.query(User).filter(User.id == user_id).with_for_update().first()
            if not user:
                return False
                
            user.preferred_provider_id = provider_id
            self.db.flush()
            if not outer_transaction:
                transaction.commit()
            return True
        except Exception as e:
            transaction.rollback()
            logger.error(f"Error setting provider: {str(e)}")
            raise

    def set_user_provider(self, user_id: UUID, provider_id: UUID) -> bool:
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
                
            user.preferred_provider_id = provider_id
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Invalid provider ID")
        except Exception as e:
            logger.error(f"Error setting provider for user {user_id}: {str(e)}")
            self.db.rollback()
            raise
    
    def get_user_provider(self, user_id: UUID) -> Optional[LLMProviderOutput]:
        try:
            # First check if user has a preferred provider
            user = self.db.query(User).filter(User.id == user_id).first()
            if user and user.preferred_provider_id:
                provider = self.db.query(LLMProvider).filter(
                    LLMProvider.id == user.preferred_provider_id
                ).first()
                if provider:
                    return LLMProviderOutput.model_validate(provider)
            
            # Fall back to default provider
            provider = (self.db.query(LLMProvider)
                        .filter(LLMProvider.is_default.is_(True))
                        .first())
            return LLMProviderOutput.model_validate(provider) if provider else None
        except Exception as e:
            logger.error(f"Error fetching provider: {str(e)}")
            raise

    def get_default_provider(self) -> Optional[LLMProviderOutput]:
        try:
            provider = (self.db.query(LLMProvider)
                       .filter(LLMProvider.is_default.is_(True))
                       .first())
            return LLMProviderOutput.model_validate(provider) if provider else None
        except Exception as e:
            logger.error(f"Error fetching default provider: {str(e)}")
            raise
