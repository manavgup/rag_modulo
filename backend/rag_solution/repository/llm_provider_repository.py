from typing import Any

from pydantic import UUID4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError, ValidationError
from rag_solution.models.llm_provider import LLMProvider
from rag_solution.schemas.llm_provider_schema import LLMProviderInput


class LLMProviderRepository:
    """Handles database operations related to LLM Providers."""

    def __init__(self: Any, session: Session) -> None:
        self.session = session

    def create_provider(self, provider_input: LLMProviderInput) -> LLMProvider:
        """Creates a new LLM provider."""
        try:
            # Convert SecretStr to string before storing
            provider_data = provider_input.model_dump(exclude_unset=True)
            if provider_data.get("api_key") and hasattr(provider_data["api_key"], "get_secret_value"):
                provider_data["api_key"] = provider_data["api_key"].get_secret_value()

            provider = LLMProvider(**provider_data)
            self.session.add(provider)
            self.session.commit()
            self.session.refresh(provider)
            return provider
        except IntegrityError as e:
            self.session.rollback()
            raise AlreadyExistsError(resource_type="LLMProvider", field="name", value=provider_input.name) from e
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception:
            self.session.rollback()
            raise

    def get_provider_by_id(self, provider_id: UUID4) -> LLMProvider:
        """Fetches a provider by ID.

        Raises:
            NotFoundError: If provider not found
        """
        try:
            provider = self.session.query(LLMProvider).filter_by(id=provider_id).first()
            if not provider:
                raise NotFoundError(resource_type="LLMProvider", resource_id=str(provider_id))
            return provider
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception:
            raise

    def get_provider_by_name(self, name: str) -> LLMProvider:
        """Fetches a provider by name, case-insensitive.

        Raises:
            NotFoundError: If provider not found
        """
        try:
            provider = self.session.query(LLMProvider).filter(LLMProvider.name.ilike(name)).first()
            if not provider:
                raise NotFoundError(resource_type="LLMProvider", identifier=name)
            return provider
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception:
            raise

    def get_all_providers(self, is_active: bool | None = None) -> list[LLMProvider]:
        """Fetches all providers, optionally filtering by active status."""
        try:
            query = self.session.query(LLMProvider)
            if is_active is not None:
                query = query.filter_by(is_active=is_active)
            return query.all()
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception:
            raise

    def get_provider_by_name_with_credentials(self, name: str) -> LLMProvider:
        """Fetch provider including credentials by name.

        Raises:
            NotFoundError: If provider not found
        """
        try:
            provider = self.session.query(LLMProvider).filter(LLMProvider.name.ilike(name)).filter(LLMProvider.is_active).first()
            if not provider:
                raise NotFoundError(resource_type="LLMProvider", identifier=name)
            return provider
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception:
            raise

    def update_provider(self, provider_id: UUID4, updates: dict) -> LLMProvider:
        """Updates provider details.

        Raises:
            NotFoundError: If provider not found
        """
        try:
            # Handle SecretStr in updates
            if "api_key" in updates and hasattr(updates["api_key"], "get_secret_value"):
                updates["api_key"] = updates["api_key"].get_secret_value()

            # Find the provider first - this will raise NotFoundError if not found
            provider = self.get_provider_by_id(provider_id)

            # Apply updates
            for key, value in updates.items():
                setattr(provider, key, value)

            self.session.commit()
            self.session.refresh(provider)
            return provider

        except IntegrityError as e:
            self.session.rollback()
            raise AlreadyExistsError(resource_type="LLMProvider", field="name", value=str(provider_id)) from e
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception:
            self.session.rollback()
            raise

    def delete_provider(self, provider_id: UUID4) -> None:
        """Soft deletes a provider by marking it inactive.

        Raises:
            NotFoundError: If provider not found
        """
        try:
            # First check if provider exists - this will raise NotFoundError if not found
            self.get_provider_by_id(provider_id)

            # Mark as inactive
            self.session.query(LLMProvider).filter_by(id=provider_id).update({"is_active": False})
            self.session.commit()
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Failed to delete provider: {e!s}") from e

    def get_default_provider(self) -> LLMProvider:
        """Get the system default provider.

        Raises:
            NotFoundError: If no default provider found
        """
        try:
            provider = self.session.query(LLMProvider).filter(LLMProvider.is_active).filter(LLMProvider.is_default).first()
            if not provider:
                raise NotFoundError(resource_type="LLMProvider", identifier="default provider")
            return provider
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception:
            raise

    def clear_other_default_providers(self, provider_id: UUID4) -> None:
        """Clear default flag from other providers."""
        try:
            self.session.query(LLMProvider).filter(LLMProvider.id != provider_id).update({"is_default": False})
            self.session.commit()
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception:
            self.session.rollback()
            raise
