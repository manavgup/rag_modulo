# Conversation Router Migration Guide

## Overview

As part of Phase 4 (Router Unification) of the conversation system refactoring (Issue #558), the `/api/chat` router has been **deprecated** and all functionality has been consolidated into the `/api/conversations` router.

This document provides a comprehensive migration guide for updating your code to use the new unified API.

## Timeline

- **Phase 4 Complete**: Router unification implemented
- **Deprecation Period**: 2-3 releases (both routers functional with warnings)
- **Removal**: `/api/chat` router will be removed in a future major release

## Benefits of Migration

1. **Single Source of Truth**: All conversation endpoints in one place
2. **Consistent API Design**: Uniform error handling and response models
3. **Enhanced Features**: Access to all conversation management features
4. **Better Documentation**: Comprehensive OpenAPI documentation
5. **Improved Maintainability**: Simplified codebase with 42% code reduction

## Quick Reference

### Endpoint Mapping

| Old Endpoint (`/api/chat`) | New Endpoint (`/api/conversations`) | Notes |
|----------------------------|-------------------------------------|-------|
| `POST /sessions` | `POST /` | Create conversation session |
| `GET /sessions` | `GET /` | List conversation sessions |
| `GET /sessions/{id}` | `GET /{session_id}` | Get conversation session |
| `PUT /sessions/{id}` | `PUT /{session_id}` | Update conversation session |
| `DELETE /sessions/{id}` | `DELETE /{session_id}` | Delete conversation session |
| `POST /sessions/{id}/messages` | `POST /{session_id}/messages` | Add message to session |
| `GET /sessions/{id}/messages` | `GET /{session_id}/messages` | Get session messages |
| `POST /sessions/{id}/process` | `POST /{session_id}/process` | Process user message (LLM) |
| `GET /sessions/{id}/statistics` | `GET /{session_id}/statistics` | Get session statistics |
| `GET /sessions/{id}/export` | `POST /{session_id}/export` | Export session (method changed) |
| `GET /sessions/{id}/suggestions` | `GET /{session_id}/suggestions` | Get question suggestions |
| `POST /sessions/{id}/summaries` | `POST /{session_id}/summaries` | Create summary |
| `GET /sessions/{id}/summaries` | `GET /{session_id}/summaries` | Get summaries |
| `POST /sessions/{id}/context-summarization` | `POST /{session_id}/context-summarization` | Context summarization |
| `GET /sessions/{id}/context-threshold` | `GET /{session_id}/context-threshold` | Check context threshold |
| `POST /sessions/{id}/conversation-suggestions` | `POST /{session_id}/conversation-suggestions` | Enhanced suggestions |
| `POST /sessions/{id}/enhanced-export` | `POST /{session_id}/enhanced-export` | Enhanced export |

### Additional Endpoints (New in Unified Router)

These endpoints are available in `/api/conversations` and were not present in `/api/chat`:

| Endpoint | Description |
|----------|-------------|
| `POST /{session_id}/archive` | Archive conversation session |
| `POST /{session_id}/restore` | Restore archived session |
| `GET /{session_id}/summary` | Get conversation summary |
| `POST /{session_id}/generate-name` | Auto-generate conversation name |
| `POST /bulk-rename` | Bulk rename all user conversations |

## Migration Steps

### Step 1: Update Base URL

**Before**:
```python
BASE_URL = "https://api.example.com/api/chat"
```

**After**:
```python
BASE_URL = "https://api.example.com/api/conversations"
```

### Step 2: Update Endpoint Paths

#### Example 1: Create Session

**Before**:
```python
response = requests.post(
    f"{BASE_URL}/sessions",
    json={
        "collection_id": collection_id,
        "session_name": "My Chat Session",
        "user_id": user_id
    }
)
```

**After**:
```python
response = requests.post(
    BASE_URL,  # Note: No /sessions suffix
    json={
        "collection_id": collection_id,
        "session_name": "My Chat Session"
        # user_id is now extracted from JWT token automatically
    }
)
```

#### Example 2: List Sessions

**Before**:
```python
response = requests.get(f"{BASE_URL}/sessions")
```

**After**:
```python
response = requests.get(BASE_URL)  # Note: No /sessions suffix
```

#### Example 3: Process Message (LLM)

**Before**:
```python
response = requests.post(
    f"{BASE_URL}/sessions/{session_id}/process",
    json={
        "session_id": session_id,
        "content": "What is machine learning?",
        "role": "user",
        "message_type": "question"
    }
)
```

**After**:
```python
response = requests.post(
    f"{BASE_URL}/{session_id}/process",  # Note: /sessions removed
    json={
        "session_id": session_id,
        "content": "What is machine learning?",
        "role": "user",
        "message_type": "question"
    }
)
```

#### Example 4: Export Session

**Before** (GET):
```python
response = requests.get(
    f"{BASE_URL}/sessions/{session_id}/export",
    params={"export_format": "json"}
)
```

**After** (POST):
```python
response = requests.post(
    f"{BASE_URL}/{session_id}/export",  # Note: Method changed to POST
    json={"export_format": "json"}
)
```

### Step 3: Update Frontend API Calls

#### JavaScript/TypeScript Example

**Before**:
```typescript
// Old API client
class ChatAPI {
  private baseURL = '/api/chat';

  async createSession(data: SessionCreateInput): Promise<Session> {
    const response = await fetch(`${this.baseURL}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  }

  async getMessages(sessionId: string): Promise<Message[]> {
    const response = await fetch(`${this.baseURL}/sessions/${sessionId}/messages`);
    return response.json();
  }
}
```

**After**:
```typescript
// New unified API client
class ConversationAPI {
  private baseURL = '/api/conversations';

  async createSession(data: SessionCreateInput): Promise<Session> {
    const response = await fetch(this.baseURL, {  // Note: No /sessions
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  }

  async getMessages(sessionId: string): Promise<Message[]> {
    const response = await fetch(`${this.baseURL}/${sessionId}/messages`);
    return response.json();
  }
}
```

#### React Hook Example

**Before**:
```typescript
const useChatSession = (sessionId: string) => {
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    fetch(`/api/chat/sessions/${sessionId}/messages`)
      .then(res => res.json())
      .then(setMessages);
  }, [sessionId]);

  return { messages };
};
```

**After**:
```typescript
const useConversation = (sessionId: string) => {
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    fetch(`/api/conversations/${sessionId}/messages`)
      .then(res => res.json())
      .then(setMessages);
  }, [sessionId]);

  return { messages };
};
```

### Step 4: Update OpenAPI/Swagger Clients

If you're using auto-generated API clients from OpenAPI/Swagger:

1. Regenerate clients using the new OpenAPI spec from `/api/conversations`
2. Update import statements to use the new client classes
3. Update method calls to match the new endpoint structure

### Step 5: Update Tests

**Before**:
```python
def test_create_session():
    response = client.post(
        "/api/chat/sessions",
        json={"collection_id": str(collection_id), "session_name": "Test"}
    )
    assert response.status_code == 200
```

**After**:
```python
def test_create_session():
    response = client.post(
        "/api/conversations",  # Note: No /sessions
        json={"collection_id": str(collection_id), "session_name": "Test"}
    )
    assert response.status_code == 201  # Note: Status code changed to 201 Created
```

## Breaking Changes

### 1. Create Session Endpoint

**Change**: User ID is now extracted from JWT token automatically

**Before**:
```json
{
  "user_id": "uuid-here",
  "collection_id": "collection-uuid",
  "session_name": "My Session"
}
```

**After**:
```json
{
  "collection_id": "collection-uuid",
  "session_name": "My Session"
}
```

**Migration**: Remove `user_id` from request body. The system will automatically extract it from the authentication token.

### 2. Export Endpoint Method

**Change**: Export endpoint changed from GET to POST

**Before**: `GET /api/chat/sessions/{id}/export?export_format=json`

**After**: `POST /api/conversations/{id}/export` with JSON body

**Migration**:
```python
# Before
response = requests.get(f"/api/chat/sessions/{id}/export", params={"export_format": "json"})

# After
response = requests.post(f"/api/conversations/{id}/export", json={"export_format": "json"})
```

### 3. Status Codes

Some endpoints now return different status codes:

- **Create Session**: Changed from `200 OK` to `201 Created`
- **Delete Session**: Changed from `200 OK` to `204 No Content`

### 4. URL Structure

- Removed `/sessions` from paths (except for nested resources)
- More RESTful resource naming

## Common Migration Patterns

### Pattern 1: Search and Replace

For simple migrations, you can use search and replace:

```bash
# Update base URL
find . -type f -name "*.py" -exec sed -i 's|/api/chat|/api/conversations|g' {} +

# Update /sessions paths
find . -type f -name "*.py" -exec sed -i 's|/api/conversations/sessions/|/api/conversations/|g' {} +
find . -type f -name "*.py" -exec sed -i 's|/api/conversations/sessions"|/api/conversations"|g' {} +
```

### Pattern 2: Wrapper Function

Create a compatibility wrapper during the migration period:

```python
class ConversationAPIClient:
    """Unified conversation API client."""

    def __init__(self, base_url: str):
        self.base_url = f"{base_url}/api/conversations"

    def create_session(self, collection_id: str, session_name: str) -> dict:
        """Create a new conversation session."""
        response = requests.post(
            self.base_url,
            json={
                "collection_id": collection_id,
                "session_name": session_name
            }
        )
        response.raise_for_status()
        return response.json()

    def process_message(self, session_id: str, content: str) -> dict:
        """Process a user message and get LLM response."""
        response = requests.post(
            f"{self.base_url}/{session_id}/process",
            json={
                "session_id": session_id,
                "content": content,
                "role": "user",
                "message_type": "question"
            }
        )
        response.raise_for_status()
        return response.json()
```

### Pattern 3: Configuration-Based Migration

Use environment variables or configuration files:

```python
# config.py
import os

API_VERSION = os.getenv("API_VERSION", "v2")  # v1 = /api/chat, v2 = /api/conversations

if API_VERSION == "v1":
    CONVERSATION_BASE_URL = "/api/chat"
    USE_SESSIONS_PREFIX = True
elif API_VERSION == "v2":
    CONVERSATION_BASE_URL = "/api/conversations"
    USE_SESSIONS_PREFIX = False

def get_session_url(session_id: str = None) -> str:
    """Get the appropriate session URL based on API version."""
    if USE_SESSIONS_PREFIX:
        base = f"{CONVERSATION_BASE_URL}/sessions"
    else:
        base = CONVERSATION_BASE_URL

    if session_id:
        return f"{base}/{session_id}"
    return base
```

## Validation and Testing

### 1. Functional Testing

Test all migrated endpoints to ensure they work correctly:

```python
import pytest
import requests

BASE_URL = "http://localhost:8000/api/conversations"

def test_conversation_crud():
    # Create session
    response = requests.post(
        BASE_URL,
        json={"collection_id": "test-collection", "session_name": "Test Session"}
    )
    assert response.status_code == 201
    session = response.json()

    # Get session
    response = requests.get(f"{BASE_URL}/{session['id']}")
    assert response.status_code == 200

    # Update session
    response = requests.put(
        f"{BASE_URL}/{session['id']}",
        json={"session_name": "Updated Session"}
    )
    assert response.status_code == 200

    # Delete session
    response = requests.delete(f"{BASE_URL}/{session['id']}")
    assert response.status_code == 204
```

### 2. Integration Testing

Ensure end-to-end flows work correctly:

```python
def test_full_conversation_flow():
    # Create session
    session = create_session("test-collection", "Test Chat")

    # Send message and get LLM response
    response = process_message(session['id'], "What is AI?")
    assert "assistant" in response["role"]

    # Get message history
    messages = get_messages(session['id'])
    assert len(messages) >= 2  # User message + assistant response

    # Export conversation
    export_data = export_session(session['id'], "json")
    assert export_data["total_messages"] >= 2
```

### 3. Performance Testing

Verify the unified router maintains or improves performance:

```bash
# Before migration
ab -n 1000 -c 10 http://localhost:8000/api/chat/sessions

# After migration
ab -n 1000 -c 10 http://localhost:8000/api/conversations
```

## Troubleshooting

### Issue 1: 404 Not Found

**Symptom**: Endpoints return 404 after migration

**Cause**: Still using old `/api/chat/sessions/{id}` paths

**Solution**: Update paths to remove `/sessions` suffix:
- `/api/chat/sessions/{id}` → `/api/conversations/{id}`

### Issue 2: 401 Unauthorized

**Symptom**: Authentication fails after migration

**Cause**: User ID included in request body instead of JWT token

**Solution**: Remove `user_id` from request body. Ensure JWT token is included in Authorization header.

### Issue 3: 405 Method Not Allowed

**Symptom**: Export endpoint returns 405

**Cause**: Using GET method instead of POST for export

**Solution**: Change export requests from GET to POST:
```python
# Before
requests.get(f"{base_url}/{id}/export?format=json")

# After
requests.post(f"{base_url}/{id}/export", json={"export_format": "json"})
```

### Issue 4: Deprecation Warnings

**Symptom**: Python deprecation warnings in logs

**Cause**: Still importing from `/api/chat` router

**Solution**: These warnings are intentional. Migrate to `/api/conversations` to remove them.

## Rollback Plan

If you encounter issues during migration, you can temporarily rollback:

1. **Configuration Rollback**: Set environment variable to use old API:
   ```bash
   export CONVERSATION_API_BASE=/api/chat
   ```

2. **Code Rollback**: Revert to previous commit before migration:
   ```bash
   git revert <migration-commit-hash>
   ```

3. **Partial Rollback**: Use feature flags to selectively enable new API:
   ```python
   if feature_flags.is_enabled("unified_conversation_api"):
       base_url = "/api/conversations"
   else:
       base_url = "/api/chat"
   ```

## Support

If you encounter issues during migration:

1. Check this migration guide for common issues
2. Review the [Conversation System Refactoring](conversation-system-refactoring.md) documentation
3. Check the OpenAPI documentation at `/docs` endpoint
4. Create an issue on GitHub with the `migration` label

## Related Documentation

- [Conversation System Refactoring](conversation-system-refactoring.md) - Full refactoring plan
- [API Documentation](../api/index.md) - Complete API reference
- [Phase 4 Implementation](conversation-refactoring-project-board-setup.md) - Project tracking

## Changelog

- **2025-01**: Phase 4 completed - Router unification implemented
- **2025-01**: Deprecation warnings added to `/api/chat` router
- **Future**: `/api/chat` router removal (TBD)
