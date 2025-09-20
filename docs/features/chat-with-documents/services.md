# Chat with Documents - Services

This document provides detailed information about the core services that power the Chat with Documents feature.

## ConversationService

The main service for managing conversation sessions and messages.

### Overview

The `ConversationService` handles the complete lifecycle of conversation sessions, including creation, message management, session updates, and cleanup operations.

### Key Methods

#### Session Management

```python
async def create_session(session_input: ConversationSessionInput) -> ConversationSessionOutput
```
Creates a new conversation session with the specified configuration.

**Parameters:**
- `session_input`: Session configuration including user_id, collection_id, and settings

**Returns:**
- `ConversationSessionOutput`: Created session with generated ID and metadata

**Example:**
```python
session_input = ConversationSessionInput(
    user_id=user_uuid,
    collection_id=collection_uuid,
    session_name="My Chat Session",
    context_window_size=4000,
    max_messages=50
)
session = await conversation_service.create_session(session_input)
```

#### Message Management

```python
async def add_message(message_input: ConversationMessageInput) -> ConversationMessageOutput
```
Adds a new message to an existing conversation session.

**Parameters:**
- `message_input`: Message content, role, type, and metadata

**Returns:**
- `ConversationMessageOutput`: Created message with generated ID and timestamp

**Example:**
```python
message_input = ConversationMessageInput(
    session_id=session.id,
    content="What is machine learning?",
    role=MessageRole.USER,
    message_type=MessageType.QUESTION
)
message = await conversation_service.add_message(message_input)
```

#### Session Retrieval

```python
async def get_session(session_id: UUID4, user_id: UUID4) -> ConversationSessionOutput
async def get_user_sessions(user_id: UUID4, status: SessionStatus = None) -> List[ConversationSessionOutput]
async def get_session_messages(session_id: UUID4, user_id: UUID4, limit: int = 50, offset: int = 0) -> List[ConversationMessageOutput]
```

#### Session Updates

```python
async def update_session(session_id: UUID4, user_id: UUID4, updates: Dict[str, Any]) -> ConversationSessionOutput
async def archive_session(session_id: UUID4, user_id: UUID4) -> ConversationSessionOutput
async def restore_session(session_id: UUID4, user_id: UUID4) -> ConversationSessionOutput
async def delete_session(session_id: UUID4, user_id: UUID4) -> bool
```

#### Analytics and Export

```python
async def get_session_statistics(session_id: UUID4, user_id: UUID4) -> Dict[str, Any]
async def export_session(session_id: UUID4, user_id: UUID4, format: str = "json") -> Dict[str, Any]
async def search_sessions(user_id: UUID4, query: str) -> List[ConversationSessionOutput]
```

### Error Handling

The service raises specific exceptions for different error conditions:

- `NotFoundError`: Session or message not found
- `ValidationError`: Invalid input data
- `SessionExpiredError`: Session has expired
- `PermissionError`: User lacks access to session

## ContextManagerService

Manages conversation context, including building context from messages, pruning irrelevant content, and handling entity extraction.

### Overview

The `ContextManagerService` is responsible for maintaining conversation context intelligently, ensuring that relevant information is preserved while managing token limits and context window constraints.

### Key Methods

#### Context Building

```python
async def build_context_from_messages(session_id: UUID4, messages: List[ConversationMessageOutput]) -> ConversationContext
```
Builds conversation context from a list of messages, extracting key information and maintaining coherence.

**Parameters:**
- `session_id`: ID of the conversation session
- `messages`: List of conversation messages

**Returns:**
- `ConversationContext`: Structured context with window, documents, and metadata

**Example:**
```python
context = await context_manager.build_context_from_messages(session_id, messages)
print(f"Context window: {context.context_window}")
print(f"Relevant documents: {context.relevant_documents}")
```

#### Context Pruning

```python
async def prune_context_by_relevance(context: ConversationContext, threshold: float = 0.7) -> ConversationContext
```
Removes less relevant content from context to stay within token limits.

**Parameters:**
- `context`: Current conversation context
- `threshold`: Relevance threshold (0.0 to 1.0)

**Returns:**
- `ConversationContext`: Pruned context with reduced content

#### Entity Extraction

```python
async def extract_key_entities(text: str) -> List[str]
async def resolve_pronouns(current_message: str, context: str) -> str
async def detect_follow_up_question(current_message: str, previous_messages: List[ConversationMessageOutput]) -> bool
```

#### Context Analysis

```python
async def calculate_context_relevance(context: str, query: str) -> float
async def merge_contexts(contexts: List[ConversationContext]) -> ConversationContext
```

### Context Management Strategies

#### Sliding Window
Maintains a fixed-size context window that slides as new messages are added.

#### Relevance-Based Pruning
Removes content below a relevance threshold while preserving important information.

#### Entity-Aware Context
Tracks key entities and ensures they remain in context even when other content is pruned.

## QuestionSuggestionService

Generates intelligent question suggestions based on conversation context and document content.

### Overview

The `QuestionSuggestionService` provides smart suggestions to help users explore their documents more effectively through guided questions and follow-up recommendations.

### Key Methods

#### Suggestion Generation

```python
async def generate_suggestions_from_context(context: str, max_suggestions: int = 5) -> List[str]
```
Generates question suggestions based on conversation context.

**Parameters:**
- `context`: Current conversation context
- `max_suggestions`: Maximum number of suggestions to generate

**Returns:**
- `List[str]`: List of suggested questions

**Example:**
```python
suggestions = await suggestion_service.generate_suggestions_from_context(
    "This conversation is about machine learning and neural networks",
    max_suggestions=3
)
# Returns: ["What are the different types of neural networks?", 
#           "How do neural networks learn?", 
#           "What are the applications of neural networks?"]
```

#### Document-Based Suggestions

```python
async def generate_suggestions_from_documents(documents: List[Dict[str, Any]], max_suggestions: int = 5) -> List[str]
```
Generates suggestions based on document content and metadata.

#### Follow-up Suggestions

```python
async def generate_follow_up_suggestions(current_message: str, context: str, max_suggestions: int = 3) -> List[str]
```
Generates follow-up questions based on the current message and conversation context.

#### Suggestion Management

```python
async def cache_suggestions(cache_key: str, suggestions: List[str]) -> bool
async def get_cached_suggestions(cache_key: str) -> Optional[List[str]]
async def validate_suggestion_quality(suggestions: List[str]) -> List[str]
async def rank_suggestions_by_relevance(suggestions: List[str], context: str) -> List[str]
```

### Suggestion Strategies

#### Context-Aware Generation
Analyzes conversation context to generate relevant follow-up questions.

#### Document-Driven Suggestions
Uses document content and metadata to suggest exploration paths.

#### Quality Filtering
Validates suggestions for relevance, clarity, and usefulness.

#### Caching
Caches suggestions for performance optimization and consistency.

## Service Integration

### Database Integration

All services integrate with the database layer for persistent storage:

```python
# Database models
class ConversationSession(Base):
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

class ConversationMessage(Base):
    id: UUID4
    session_id: UUID4
    content: str
    role: MessageRole
    message_type: MessageType
    metadata: Dict[str, Any]
    created_at: datetime
```

### RAG Integration

Services integrate with existing RAG components:

```python
# Integration with search service
async def search_with_conversation_context(search_input: SearchInput, context: ConversationContext):
    # Enhance search with conversation context
    enhanced_query = await context_manager.enhance_query_with_context(
        search_input.question, 
        context
    )
    
    # Perform RAG search
    search_result = await search_service.search(enhanced_query)
    
    # Update context with search results
    updated_context = await context_manager.update_context_with_search_results(
        context, 
        search_result
    )
    
    return search_result, updated_context
```

### Error Handling

All services implement comprehensive error handling:

```python
try:
    result = await conversation_service.create_session(session_input)
except ValidationError as e:
    logger.error(f"Validation error: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

## Performance Considerations

### Caching Strategy

- **Session caching**: Frequently accessed sessions cached in Redis
- **Context caching**: Computed contexts cached to avoid recomputation
- **Suggestion caching**: Generated suggestions cached with TTL

### Database Optimization

- **Indexed queries**: Proper indexing on user_id, session_id, created_at
- **Pagination**: Efficient pagination for large message histories
- **Connection pooling**: Database connection pooling for scalability

### Memory Management

- **Context pruning**: Automatic pruning to stay within memory limits
- **Message archiving**: Old messages archived to reduce memory usage
- **Garbage collection**: Regular cleanup of expired sessions

## Testing

Services are thoroughly tested with:

- **Unit tests**: Individual method testing with mocks
- **Integration tests**: Service interaction testing
- **Performance tests**: Load testing and benchmarking
- **Error handling tests**: Exception scenario testing

See the [Testing Guide](./testing.md) for detailed testing information.
