"""DEPRECATED: This file will be removed in Phase 7.

Use rag_solution.models.conversation.ConversationSummary instead.
This file is maintained for backward compatibility during Phases 3-6.
"""

import warnings

# Import from unified conversation module
from rag_solution.models.conversation import ConversationSummary

# Issue deprecation warning when this module is imported
warnings.warn(
    "conversation_summary.py is deprecated and will be removed in Phase 7. "
    "Use rag_solution.models.conversation.ConversationSummary instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ConversationSummary"]
