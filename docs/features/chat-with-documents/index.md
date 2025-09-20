# Chat with Documents - Conversational Interface

Chat with Documents is an advanced conversational interface that enables users to have multi-turn conversations with their document collections, maintaining context across interactions and providing a more natural, interactive experience compared to single-turn Q&A systems.

## Overview

The Chat with Documents system transforms traditional document search into an engaging conversational experience by:

1. **Maintaining conversation sessions** with persistent context and history
2. **Managing context intelligently** with relevance-based pruning and entity extraction
3. **Generating follow-up suggestions** to guide users through deeper exploration
4. **Integrating seamlessly** with existing RAG search capabilities
5. **Providing session management** with archiving, export, and analytics

## Key Features

### 🗣️ **Conversational Interface**
- **Multi-turn conversations** with context preservation
- **Natural follow-up questions** with pronoun resolution
- **Session-based interactions** with persistent state
- **Real-time message streaming** for responsive UX

### 🧠 **Intelligent Context Management**
- **Context window management** with configurable limits
- **Relevance-based pruning** to maintain focus
- **Entity extraction** and pronoun resolution
- **Follow-up question detection** for natural flow

### 💡 **Smart Suggestions**
- **Question suggestions** based on document content
- **Follow-up recommendations** from conversation context
- **Cached suggestions** for performance optimization
- **Quality validation** to ensure helpful recommendations

### 🔍 **RAG Integration**
- **Seamless search integration** with existing RAG pipeline
- **Source attribution** in conversation context
- **Document-aware responses** with proper citations
- **Multi-collection support** for cross-document conversations

### 📊 **Session Management**
- **Session lifecycle** management (create, archive, restore, delete)
- **Export capabilities** (JSON, Markdown, PDF)
- **Analytics and statistics** for session insights
- **User isolation** with proper access controls

## Architecture Components

### Core Services

1. **[ConversationService](./services.md#conversationservice)** - Main session and message management
2. **[ContextManagerService](./services.md#contextmanagerservice)** - Context building and pruning
3. **[QuestionSuggestionService](./services.md#questionsuggestionservice)** - Smart suggestion generation
4. **[ChatRouter](./api-reference.md#chat-router)** - RESTful API endpoints

### Data Models

- **[Conversation Schemas](./schemas.md)** - Session and message data structures
- **[Context Management](./context-management.md)** - Context and entity models
- **[API Schemas](./api-reference.md#schemas)** - Request/response models

## Quick Start

### Basic Usage

```python
from rag_solution.services.conversation_service import ConversationService
from rag_solution.schemas.conversation_schema import ConversationSessionInput, ConversationMessageInput

# Initialize service
conversation_service = ConversationService(db=db, settings=settings)

# Create a new conversation session
session_input = ConversationSessionInput(
    user_id=user_uuid,
    collection_id=collection_uuid,
    session_name="My Chat Session"
)
session = conversation_service.create_session(session_input)

# Add a user message
user_message = ConversationMessageInput(
    session_id=session.id,
    content="What is machine learning?",
    role=MessageRole.USER,
    message_type=MessageType.QUESTION
)
user_response = conversation_service.add_message(user_message)

# Add an assistant response
assistant_message = ConversationMessageInput(
    session_id=session.id,
    content="Machine learning is a subset of AI...",
    role=MessageRole.ASSISTANT,
    message_type=MessageType.ANSWER
)
assistant_response = conversation_service.add_message(assistant_message)
```

### Integration with RAG Search

```python
# In your search service
async def search_with_conversation(search_input: SearchInput, session_id: UUID4):
    # Perform RAG search
    search_result = await self.perform_rag_search(search_input)

    # Add search result to conversation
    message = ConversationMessageInput(
        session_id=session_id,
        content=search_result.answer,
        role=MessageRole.ASSISTANT,
        message_type=MessageType.ANSWER,
        metadata={"sources": search_result.sources}
    )

    return await self.conversation_service.add_message(message)
```

### API Usage

```bash
# Create a new session
curl -X POST "/api/chat/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-uuid",
    "collection_id": "collection-uuid",
    "session_name": "My Chat Session"
  }'

# Add a message
curl -X POST "/api/chat/sessions/{session_id}/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What is artificial intelligence?",
    "role": "user",
    "message_type": "question"
  }'

# Get conversation history
curl -X GET "/api/chat/sessions/{session_id}/messages?user_id={user_id}"
```

## Configuration

Chat with Documents behavior is configurable through environment variables:

```python
# Session configuration
CHAT_SESSION_TIMEOUT_MINUTES=30
CHAT_MAX_CONTEXT_WINDOW_SIZE=8000
CHAT_MAX_MESSAGES_PER_SESSION=100

# Context management
CHAT_CONTEXT_PRUNING_THRESHOLD=0.7
CHAT_ENTITY_EXTRACTION_ENABLED=true

# Suggestions
CHAT_SUGGESTION_CACHE_TTL=3600
CHAT_MAX_SUGGESTIONS=5
```

## User Experience

### Conversation Flow

1. **Start Session**: User creates a new conversation session
2. **Ask Questions**: User asks questions about their documents
3. **Get Responses**: System provides AI-generated answers with sources
4. **Follow-up**: User asks follow-up questions naturally
5. **Suggestions**: System offers relevant follow-up questions
6. **Context Management**: System maintains conversation context
7. **Export/Archive**: User can save or export conversations

### Example Conversation

```
User: What is machine learning?
Assistant: Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data...

User: Tell me more about it
Assistant: Machine learning algorithms can be categorized into supervised, unsupervised, and reinforcement learning...

User: What are the applications?
Assistant: Machine learning has applications in healthcare, finance, transportation, and many other fields...

[System suggests: "How does deep learning differ from machine learning?", "What are the challenges in ML?"]
```

## Benefits

### Enhanced User Experience
- **Natural conversation flow** vs single queries
- **Context preservation** across interactions
- **Intelligent suggestions** for deeper exploration
- **Familiar chat interface** like ChatGPT

### Improved Understanding
- **Multi-turn exploration** of complex topics
- **Follow-up questions** without repeating context
- **Source attribution** for transparency
- **Conversation history** for reference

### Higher Engagement
- **Interactive sessions** keep users engaged longer
- **Suggested questions** guide exploration
- **Session management** for organized conversations
- **Export capabilities** for sharing insights

## Documentation Structure

- **[Services](./services.md)** - Detailed service documentation
- **[Schemas](./schemas.md)** - Data model specifications
- **[Context Management](./context-management.md)** - Context handling system
- **[API Reference](./api-reference.md)** - Complete API documentation
- **[Examples](./examples.md)** - Usage examples and patterns
- **[Testing](./testing.md)** - Testing approach and examples
- **[Configuration](./configuration.md)** - Configuration options

## Next Steps

1. **[Read the Services Guide](./services.md)** to understand the core components
2. **[Explore Context Management](./context-management.md)** to see how context is handled
3. **[Check out Examples](./examples.md)** for practical implementation patterns
4. **[Review the API Reference](./api-reference.md)** for complete technical details

## Related Features

- **[Chain of Thought Reasoning](../chain-of-thought/)** - Enhanced reasoning capabilities
- **[Search API](../../api/search_api.md)** - Core RAG search functionality
- **[Question Suggestions](../../api/question_suggestion.md)** - Smart question generation
