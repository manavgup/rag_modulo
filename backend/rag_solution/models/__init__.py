"""Initialize all models for SQLAlchemy."""

from rag_solution.file_management.database import Base

# Import models in dependency order - User first since it's referenced by File
from rag_solution.models.user import User

# Then File since it's referenced by Collection
from rag_solution.models.file import File

# Then Collection since it's referenced by UserCollection
from rag_solution.models.collection import Collection

# Then the rest of the models
from rag_solution.models.team import Team
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.models.provider_config import ProviderModelConfig
from rag_solution.models.question import SuggestedQuestion
from rag_solution.models.user_collection import UserCollection
from rag_solution.models.user_team import UserTeam

# Register all models with Base.metadata
__all__ = [
    'User',
    'Team',
    'File',
    'Collection',
    'LLMParameters',
    'PromptTemplate',
    'ProviderModelConfig',
    'SuggestedQuestion',
    'UserCollection',
    'UserTeam'
]
