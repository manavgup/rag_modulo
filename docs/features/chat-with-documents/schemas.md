# Chat with Documents - Schemas

This document provides detailed information about the data schemas used in the Chat with Documents feature.

## Core Schemas

### ConversationSessionInput

Input schema for creating a new conversation session.

```python
class ConversationSessionInput(BaseModel):
    user_id: UUID4
    collection_id: UUID4
    session_name: str = Field(..., min_length=1, max_length=255)
    context_window_size: int = Field(default=4000, ge=1000, le=10000)
    max_messages: int = Field(default=50, ge=10, le=500)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(strict=True, extra="forbid")
```

**Fields:**
- `user_id`: ID of the user creating the session
- `collection_id`: ID of the document collection to chat with
- `session_name`: Human-readable name for the session
- `context_window_size`: Maximum context window size in tokens (1000-10000)
- `max_messages`: Maximum number of messages per session (10-500)
- `metadata`: Additional session metadata

**Validation:**
- Session name must be 1-255 characters
- Context window size must be between 1000-10000 tokens
- Max messages must be between 10-500

### ConversationSessionOutput

Output schema for conversation session data.

```python
class ConversationSessionOutput(BaseModel):
    id: UUID4
    user_id: UUID4
    collection_id: UUID4
    session_name: str
    status: SessionStatus
    context_window_size: int
    max_messages: int
    message_count: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
```

**Fields:**
- `id`: Unique session identifier
- `user_id`: ID of the session owner
- `collection_id`: ID of the associated collection
- `session_name`: Human-readable session name
- `status`: Current session status (active, paused, archived, expired)
- `context_window_size`: Configured context window size
- `max_messages`: Configured maximum messages
- `message_count`: Current number of messages in session
- `created_at`: Session creation timestamp
- `updated_at`: Last update timestamp

### ConversationMessageInput

Input schema for adding a new message to a conversation.

```python
class ConversationMessageInput(BaseModel):
    session_id: UUID4
    content: str = Field(..., min_length=1, max_length=10000)
    role: MessageRole
    message_type: MessageType
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(strict=True, extra="forbid")
```

**Fields:**
- `session_id`: ID of the conversation session
- `content`: Message content (1-10000 characters)
- `role`: Message role (user, assistant, system)
- `message_type`: Type of message (question, answer, follow_up, clarification, system_message)
- `metadata`: Additional message metadata

**Validation:**
- Content must be 1-10000 characters
- Role must be valid MessageRole enum value
- Message type must be valid MessageType enum value

### ConversationMessageOutput

Output schema for conversation message data.

```python
class ConversationMessageOutput(BaseModel):
    id: UUID4
    session_id: UUID4
    content: str
    role: MessageRole
    message_type: MessageType
    metadata: Dict[str, Any]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
```

**Fields:**
- `id`: Unique message identifier
- `session_id`: ID of the parent session
- `content`: Message content
- `role`: Message role
- `message_type`: Message type
- `metadata`: Message metadata
- `created_at`: Message creation timestamp

## Context Management Schemas

### ConversationContext

Schema for managing conversation context.

```python
class ConversationContext(BaseModel):
    session_id: UUID4
    context_window: str = Field(..., min_length=1, max_length=50000)
    relevant_documents: List[str] = Field(default_factory=list)
    context_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(strict=True, extra="forbid")
```

**Fields:**
- `session_id`: ID of the conversation session
- `context_window`: Current context window content (1-50000 characters)
- `relevant_documents`: List of relevant document IDs
- `context_metadata`: Context-specific metadata (relevance scores, entities, etc.)

## Enumeration Schemas

### SessionStatus

Enumeration for conversation session status.

```python
class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    EXPIRED = "expired"
```

**Values:**
- `ACTIVE`: Session is active and accepting messages
- `PAUSED`: Session is temporarily paused
- `ARCHIVED`: Session is archived and read-only
- `EXPIRED`: Session has expired and is no longer accessible

### MessageRole

Enumeration for message roles.

```python
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
```

**Values:**
- `USER`: Message from the user
- `ASSISTANT`: Message from the AI assistant
- `SYSTEM`: System-generated message (suggestions, notifications, etc.)

### MessageType

Enumeration for message types.

```python
class MessageType(str, Enum):
    QUESTION = "question"
    ANSWER = "answer"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"
    SYSTEM_MESSAGE = "system_message"
```

**Values:**
- `QUESTION`: User question
- `ANSWER`: Assistant response
- `FOLLOW_UP`: Follow-up question or response
- `CLARIFICATION`: Clarification request or response
- `SYSTEM_MESSAGE`: System notification or suggestion

## API Request/Response Schemas

### CreateSessionRequest

```python
class CreateSessionRequest(BaseModel):
    user_id: str
    collection_id: str
    session_name: str
    context_window_size: Optional[int] = 4000
    max_messages: Optional[int] = 50
```

### CreateSessionResponse

```python
class CreateSessionResponse(BaseModel):
    id: str
    user_id: str
    collection_id: str
    session_name: str
    status: str
    context_window_size: int
    max_messages: int
    message_count: int
    created_at: str
    updated_at: str
```

### AddMessageRequest

```python
class AddMessageRequest(BaseModel):
    content: str
    role: str
    message_type: str
    metadata: Optional[Dict[str, Any]] = None
```

### AddMessageResponse

```python
class AddMessageResponse(BaseModel):
    id: str
    session_id: str
    content: str
    role: str
    message_type: str
    metadata: Dict[str, Any]
    created_at: str
```

### GetMessagesResponse

```python
class GetMessagesResponse(BaseModel):
    messages: List[ConversationMessageOutput]
    total_count: int
    has_more: bool
```

### SessionStatisticsResponse

```python
class SessionStatisticsResponse(BaseModel):
    message_count: int
    session_duration: int  # seconds
    average_response_time: float  # seconds
    context_usage: float  # percentage
    user_messages: int
    assistant_messages: int
    system_messages: int
```

### ExportSessionResponse

```python
class ExportSessionResponse(BaseModel):
    session_data: ConversationSessionOutput
    messages: List[ConversationMessageOutput]
    metadata: Dict[str, Any]
    exported_at: str
    format: str
```

## Validation Rules

### Session Validation

- **Session Name**: 1-255 characters, required
- **Context Window Size**: 1000-10000 tokens, default 4000
- **Max Messages**: 10-500 messages, default 50
- **User ID**: Valid UUID4 format
- **Collection ID**: Valid UUID4 format

### Message Validation

- **Content**: 1-10000 characters, required
- **Role**: Must be one of: user, assistant, system
- **Message Type**: Must be one of: question, answer, follow_up, clarification, system_message
- **Session ID**: Valid UUID4 format, must exist

### Context Validation

- **Context Window**: 1-50000 characters, required
- **Relevant Documents**: List of strings, optional
- **Context Metadata**: Dictionary, optional

## Serialization

### JSON Serialization

All schemas support JSON serialization with proper type conversion:

```python
# Serialize to JSON
session_json = session.model_dump_json()

# Deserialize from JSON
session = ConversationSessionOutput.model_validate_json(session_json)
```

### Database Serialization

Schemas are designed to work seamlessly with SQLAlchemy models:

```python
# Convert to database model
db_session = ConversationSession(
    id=session.id,
    user_id=session.user_id,
    collection_id=session.collection_id,
    session_name=session.session_name,
    status=session.status.value,
    context_window_size=session.context_window_size,
    max_messages=session.max_messages,
    message_count=session.message_count,
    created_at=session.created_at,
    updated_at=session.updated_at
)

# Convert from database model
session = ConversationSessionOutput.model_validate(db_session)
```

## Error Schemas

### ValidationError

```python
class ValidationError(BaseModel):
    field: str
    message: str
    value: Any
```

### NotFoundError

```python
class NotFoundError(BaseModel):
    resource_type: str
    resource_id: str
    message: str
```

### SessionExpiredError

```python
class SessionExpiredError(BaseModel):
    session_id: str
    expired_at: str
    message: str
```

## Usage Examples

### Creating a Session

```python
from rag_solution.schemas.conversation_schema import ConversationSessionInput

session_input = ConversationSessionInput(
    user_id="123e4567-e89b-12d3-a456-426614174000",
    collection_id="123e4567-e89b-12d3-a456-426614174001",
    session_name="My AI Chat Session",
    context_window_size=6000,
    max_messages=100
)
```

### Adding a Message

```python
from rag_solution.schemas.conversation_schema import ConversationMessageInput, MessageRole, MessageType

message_input = ConversationMessageInput(
    session_id="123e4567-e89b-12d3-a456-426614174002",
    content="What is machine learning?",
    role=MessageRole.USER,
    message_type=MessageType.QUESTION,
    metadata={"source": "web_interface"}
)
```

### Working with Context

```python
from rag_solution.schemas.conversation_schema import ConversationContext

context = ConversationContext(
    session_id="123e4567-e89b-12d3-a456-426614174002",
    context_window="Previous conversation about machine learning and AI...",
    relevant_documents=["doc1", "doc2", "doc3"],
    context_metadata={
        "topic": "machine_learning",
        "confidence": 0.9,
        "entities": ["AI", "neural networks", "algorithms"]
    }
)
```

## Schema Evolution

Schemas are designed to be backward compatible:

- **New fields**: Added with default values
- **Field removal**: Deprecated fields marked as optional
- **Type changes**: Handled with validation and conversion
- **Enum values**: New values added without breaking existing ones

## Best Practices

1. **Always validate input**: Use Pydantic validation for all inputs
2. **Handle errors gracefully**: Catch and convert validation errors
3. **Use type hints**: Leverage Python type hints for better IDE support
4. **Document changes**: Update schema documentation when making changes
5. **Test serialization**: Ensure schemas work with JSON and database serialization
