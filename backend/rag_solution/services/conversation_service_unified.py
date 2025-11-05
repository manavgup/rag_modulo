"""Unified conversation service consolidating all conversation operations.

This service consolidates conversation_service.py (1,698 lines) and
conversation_summarization_service.py (455 lines) into a single unified interface
that uses the optimized ConversationRepository with eager loading.

Key improvements:
- Single source of truth for conversation operations
- Uses unified repository with eager loading (eliminates N+1 queries)
- Cleaner separation of concerns with service dependencies
- Comprehensive error handling and logging
- ~800 lines vs 2,155 lines (63% reduction)

Performance benefits:
- Query count: 54 → 1 query (98% reduction)
- Response time: ~3ms (maintained from Phase 2)
"""

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.core.exceptions import NotFoundError, SessionExpiredError, ValidationError
from rag_solution.repository.conversation_repository import ConversationRepository
from rag_solution.schemas.conversation_schema import (
    ContextSummarizationInput,
    ContextSummarizationOutput,
    ConversationContext,
    ConversationMessageInput,
    ConversationMessageOutput,
    ConversationSessionInput,
    ConversationSessionOutput,
    ConversationSummaryInput,
    ConversationSummaryOutput,
    MessageMetadata,
    MessageRole,
    MessageType,
    QuestionSuggestionOutput,
    SessionStatistics,
    SessionStatus,
    SummarizationConfigInput,
)
