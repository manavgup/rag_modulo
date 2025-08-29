from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.custom_exceptions import RepositoryError
from rag_solution.models.llm_provider import LLMProvider
from rag_solution.schemas.llm_provider_schema import LLMProviderInput


class LLMProviderRepository:
    """Handles database operations related to LLM Providers."""

    def __init__(self, session: Session):
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
            raise RepositoryError(f"Failed to create provider: {e!s}")

    def get_provider_by_id(self, provider_id: UUID) -> LLMProvider | None:
        """Fetches a provider by ID, returns None if not found."""
        return self.session.query(LLMProvider).filter_by(id=provider_id).first()

    def get_provider_by_name(self, name: str) -> LLMProvider | None:
        """Fetches a provider by name, case-insensitive."""
        return self.session.query(LLMProvider).filter(LLMProvider.name.ilike(name)).first()

    def get_all_providers(self, is_active: bool | None = None) -> list[LLMProvider]:
        """Fetches all providers, optionally filtering by active status."""
        query = self.session.query(LLMProvider)
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        return query.all()

    def get_provider_by_name_with_credentials(self, name: str) -> LLMProvider | None:
        """Fetch provider including credentials by name."""
        try:
            return (
                self.session.query(LLMProvider)
                .filter(LLMProvider.name.ilike(name))
                .filter(LLMProvider.is_active == True)
                .first()
            )
        except Exception as e:
            raise RepositoryError(f"Error fetching provider {name}: {e!s}")

    def update_provider(self, provider_id: UUID, updates: dict) -> LLMProvider | None:
        """Updates provider details."""
        try:
            # Handle SecretStr in updates
            if "api_key" in updates and hasattr(updates["api_key"], "get_secret_value"):
                updates["api_key"] = updates["api_key"].get_secret_value()

            # Find the provider first
            provider = self.get_provider_by_id(provider_id)
            if not provider:
                return None

            # Apply updates
            for key, value in updates.items():
                setattr(provider, key, value)

            self.session.commit()
            self.session.refresh(provider)
            return provider

        except IntegrityError as e:
            self.session.rollback()
            raise RepositoryError(f"Failed to update provider: {e!s}")

    def delete_provider(self, provider_id: UUID) -> bool:
        """Soft deletes a provider by marking it inactive."""
        provider = self.get_provider_by_id(provider_id)
        if not provider:
            return False

        # Instead of deleting, mark as inactive for a soft delete.
        provider.is_active = False
        self.session.commit()
        return True

    def get_default_provider(self) -> LLMProvider | None:
        """Get the system default provider."""
        try:
            return (
                self.session.query(LLMProvider)
                .filter(LLMProvider.is_active == True)
                .filter(LLMProvider.is_default == True)
                .first()
            )
        except Exception as e:
            raise RepositoryError(f"Error fetching default provider: {e!s}")

    def clear_other_default_providers(self, provider_id: UUID):
        """Clear default flag from other providers."""
        try:
            self.session.query(LLMProvider).filter(LLMProvider.id != provider_id).update({"is_default": False})
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise RepositoryError(f"Failed to clear default providers: {e!s}")
