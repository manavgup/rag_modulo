"""Initialize all models for SQLAlchemy."""

from rag_solution.file_management.database import Base

# Then Collection since it's referenced by UserCollection
from rag_solution.models.collection import Collection

# Conversation models
from rag_solution.models.conversation_message import ConversationMessage
from rag_solution.models.conversation_session import ConversationSession
from rag_solution.models.conversation_summary import ConversationSummary

# Then File since it's referenced by Collection
from rag_solution.models.file import File
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.podcast import Podcast
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.models.question import SuggestedQuestion

# Then the rest of the models
from rag_solution.models.team import Team
from rag_solution.models.token_warning import TokenWarning

# Import models in dependency order - User first since it's referenced by File
from rag_solution.models.user import User
from rag_solution.models.user_collection import UserCollection
from rag_solution.models.user_team import UserTeam

# Register all models with Base.metadata
__all__ = [
    "Base",
    "Collection",
    "ConversationMessage",
    "ConversationSession",
    "ConversationSummary",
    "File",
    "LLMParameters",
    "Podcast",
    "PromptTemplate",
    "SuggestedQuestion",
    "Team",
    "TokenWarning",
    "User",
    "UserCollection",
    "UserTeam",
]
