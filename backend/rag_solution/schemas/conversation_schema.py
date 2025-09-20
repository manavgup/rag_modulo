"""Conversation schemas for Chat with Documents feature.

This module defines Pydantic schemas for conversation sessions, messages,
context management, and question suggestions.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, UUID4


class SessionStatus(str, Enum):
    """Status of a conversation session."""
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    EXPIRED = "expired"
    DELETED = "deleted"


class MessageRole(str, Enum):
    """Role of a message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    """Type of message content."""
    QUESTION = "question"
    ANSWER = "answer"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"
    ERROR = "error"
    SYSTEM = "system"
    SYSTEM_MESSAGE = "system_message"


class ExportFormat(str, Enum):
    """Format for exporting conversation data."""
    JSON = "json"
    CSV = "csv"
    TXT = "txt"
    PDF = "pdf"


class ConversationSessionInput(BaseModel):
    """Input schema for creating a conversation session."""
    user_id: UUID4 = Field(..., description="ID of the user creating the session")
    collection_id: UUID4 = Field(..., description="ID of the collection to chat with")
    session_name: str = Field(..., min_length=1, max_length=255, description="Name of the session")
    context_window_size: int = Field(default=4000, ge=1000, le=8000, description="Size of context window")
    max_messages: int = Field(default=50, ge=10, le=200, description="Maximum number of messages")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class ConversationSessionOutput(BaseModel):
    """Output schema for conversation session."""
    id: UUID4 = Field(default_factory=uuid4, description="Unique session ID")
    user_id: UUID4 = Field(..., description="ID of the user")
    collection_id: UUID4 = Field(..., description="ID of the collection")
    session_name: str = Field(..., description="Name of the session")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE, description="Status of the session")
    context_window_size: int = Field(..., description="Size of context window")
    max_messages: int = Field(..., description="Maximum number of messages")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConversationMessageInput(BaseModel):
    """Input schema for conversation messages."""
    session_id: UUID4 = Field(..., description="ID of the session")
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    role: MessageRole = Field(..., description="Role of the message sender")
    message_type: MessageType = Field(..., description="Type of message")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class ConversationMessageOutput(BaseModel):
    """Output schema for conversation messages."""
    id: UUID4 = Field(default_factory=uuid4, description="Unique message ID")
    session_id: UUID4 = Field(..., description="ID of the session")
    content: str = Field(..., description="Message content")
    role: MessageRole = Field(..., description="Role of the message sender")
    message_type: MessageType = Field(..., description="Type of message")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConversationContext(BaseModel):
    """Schema for conversation context."""
    session_id: UUID4 = Field(..., description="ID of the session")
    context_window: str = Field(..., description="Current context window content")
    relevant_documents: List[str] = Field(default_factory=list, description="Relevant document IDs")
    context_metadata: Dict[str, Any] = Field(default_factory=dict, description="Context metadata")


class ContextInput(BaseModel):
    """Input schema for context management."""
    session_id: UUID4 = Field(..., description="ID of the session")
    messages: List[ConversationMessageOutput] = Field(..., description="Messages to build context from")
    max_tokens: int = Field(default=2000, ge=500, le=4000, description="Maximum tokens in context")


class ContextOutput(BaseModel):
    """Output schema for context management."""
    context: ConversationContext = Field(..., description="Generated context")
    token_count: int = Field(..., ge=0, description="Number of tokens in context")
    entities: List[str] = Field(default_factory=list, description="Extracted entities")
    topics: List[str] = Field(default_factory=list, description="Identified topics")


class QuestionSuggestionInput(BaseModel):
    """Input schema for question suggestions."""
    session_id: UUID4 = Field(..., description="ID of the session")
    current_message: str = Field(..., description="Current message content")
    context: ConversationContext = Field(..., description="Current conversation context")
    max_suggestions: int = Field(default=3, ge=1, le=10, description="Maximum number of suggestions")


class QuestionSuggestionOutput(BaseModel):
    """Output schema for question suggestions."""
    suggestions: List[str] = Field(..., description="Suggested follow-up questions")
    confidence_scores: List[float] = Field(..., description="Confidence scores for suggestions")
    reasoning: str = Field(..., description="Reasoning for suggestions")


class ExportOutput(BaseModel):
    """Output schema for conversation export."""
    session_data: ConversationSessionOutput = Field(..., description="Session information")
    messages: List[ConversationMessageOutput] = Field(..., description="All messages in session")
    export_format: ExportFormat = Field(..., description="Format of the export")
    export_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Export timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Export metadata")


class SessionStatistics(BaseModel):
    """Schema for session statistics."""
    session_id: UUID4 = Field(..., description="ID of the session")
    message_count: int = Field(..., ge=0, description="Total number of messages")
    user_messages: int = Field(..., ge=0, description="Number of user messages")
    assistant_messages: int = Field(..., ge=0, description="Number of assistant messages")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    cot_usage_count: int = Field(default=0, ge=0, description="Number of times CoT was used")
    context_enhancement_count: int = Field(default=0, ge=0, description="Number of context enhancements")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional statistics")
