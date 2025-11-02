"""DEPRECATED: This file will be removed in Phase 7.

Use rag_solution.models.conversation.ConversationMessage instead.
This file is maintained for backward compatibility during Phases 3-6.
"""

import warnings

# Import from unified conversation module
from rag_solution.models.conversation import ConversationMessage

# Issue deprecation warning when this module is imported
warnings.warn(
    "conversation_message.py is deprecated and will be removed in Phase 7. "
    "Use rag_solution.models.conversation.ConversationMessage instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ConversationMessage"]
