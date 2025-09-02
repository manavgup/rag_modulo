from pydantic import UUID4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rag_solution.core.exceptions import NotFoundError, AlreadyExistsError, ValidationError
from core.custom_exceptions import RepositoryError
from core.logging_utils import get_logger
from rag_solution.models.llm_provider import LLMProvider
from rag_solution.models.user import User
from rag_solution.schemas.llm_provider_schema import LLMProviderOutput

logger = get_logger(__name__)


class UserProviderRepository:
    def __init__(self, db: Session):
        self.db = db

    def set_user_provider(self, user_id: UUID4, provider_id: UUID4, outer_transaction: Session | None = None) -> bool:
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
            logger.error(f"Error setting provider: {e!s}")
            raise RepositoryError(f"Failed to set user provider: {e!s}") from e

    def set_user_provider_simple(self, user_id: UUID4, provider_id: UUID4) -> None:
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise NotFoundError(
                    resource_type="User",
                    resource_id=str(user_id)
                )

            user.preferred_provider_id = provider_id
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            raise NotFoundError(
                resource_type="LLMProvider",
                resource_id=str(provider_id)
            ) from e
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error setting provider for user {user_id}: {e!s}")
            self.db.rollback()
            raise Exception(f"Failed to set user provider simple: {e!s}") from e

    def get_user_provider(self, user_id: UUID4) -> LLMProviderOutput | None:
        try:
            # First check if user has a preferred provider
            user = self.db.query(User).filter(User.id == user_id).first()
            if user and user.preferred_provider_id:
                provider = self.db.query(LLMProvider).filter(LLMProvider.id == user.preferred_provider_id).first()
                if provider:
                    return LLMProviderOutput.model_validate(provider)

            # Fall back to default provider
            provider = self.db.query(LLMProvider).filter(LLMProvider.is_default.is_(True)).first()
            return LLMProviderOutput.model_validate(provider) if provider else None
        except Exception as e:
            logger.error(f"Error fetching provider: {e!s}")
            raise RepositoryError(f"Failed to get user provider: {e!s}") from e

    def get_default_provider(self) -> LLMProviderOutput:
        try:
            provider = self.db.query(LLMProvider).filter(LLMProvider.is_default.is_(True)).first()
            if not provider:
                raise NotFoundError(
                    resource_type="LLMProvider",
                    identifier="default provider"
                )
            return LLMProviderOutput.model_validate(provider)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error fetching default provider: {e!s}")
            raise Exception(f"Failed to get default provider: {e!s}") from e
