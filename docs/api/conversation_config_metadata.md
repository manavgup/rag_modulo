# Conversation Config Metadata

This page documents the `config_metadata` feature for conversation messages, which allows clients to override default behavior on a per-request basis.

## Overview

The `config_metadata` field enables fine-grained control over conversation message processing by allowing clients to pass configuration overrides. These settings take precedence over default system configuration.

**Key Features:**
- Per-request configuration overrides
- Whitelist-based security validation
- Graceful fallback on invalid config
- Type-safe TypeScript interface

**Use Cases:**
- Enable/disable Chain of Thought (CoT) reasoning for specific queries
- Control structured output formatting
- Show/hide reasoning steps in responses
- Adjust conversation context settings

## API Reference

### MessageMetadata Schema

The `config_metadata` field is part of the `MessageMetadata` schema:

```python
{
  "source_documents": list[str] | None,     # Source document names
  "token_analysis": dict | None,            # Token usage details
  "sources": list[dict] | None,             # Full source data
  "cot_output": dict | None,                # Chain of Thought output
  "config_metadata": dict[str, Any] | None  # User config overrides
}
```

### ConversationConfigMetadata Fields

The following configuration keys are whitelisted for security:

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `structured_output_enabled` | `bool` | Enable/disable structured output formatting | Varies by provider |
| `cot_enabled` | `bool` | Enable/disable Chain of Thought reasoning | `true` |
| `show_cot_steps` | `bool` | Show/hide CoT reasoning steps in response | `false` |
| `conversation_context` | `str` | Conversation context window for this request | Auto-generated |
| `session_id` | `str` | Session ID for conversation continuity | From request |
| `message_history` | `list[str]` | Message history to include in context | Last 10 messages |
| `conversation_entities` | `list[str]` | Extracted entities from conversation | Auto-extracted |
| `conversation_aware` | `bool` | Enable/disable conversation-aware enhancements | `true` |

## Security

### Whitelist-Based Validation

Only the fields listed above are accepted. Any additional fields are **automatically filtered out** and logged for security auditing.

**Example - Security Filtering:**
```python
# Input with malicious keys
{
  "config_metadata": {
    "cot_enabled": true,           # ✅ Allowed
    "malicious_key": "bad_value",  # ❌ Filtered out
    "__proto__": {"admin": true}   # ❌ Filtered out (prototype pollution)
  }
}

# Result after validation
{
  "config_metadata": {
    "cot_enabled": true  # Only whitelisted keys remain
  }
}
```

### Error Handling

Invalid `config_metadata` is handled gracefully:

1. **Invalid Type** (non-dict): Logged as warning, request continues with base config
2. **Disallowed Keys**: Filtered out, logged for audit trail
3. **Validation Error**: Caught, logged, request continues
4. **Unexpected Error**: Caught, logged, request continues

No `config_metadata` errors will cause request failures.

## Usage Examples

### Python (Backend)

```python
from rag_solution.schemas.conversation_schema import ConversationMessageInput

# Send message with config overrides
message_input = ConversationMessageInput(
    session_id="123e4567-e89b-12d3-a456-426614174000",
    content="Explain how neural networks work",
    role="user",
    message_type="question",
    metadata={
        "config_metadata": {
            "cot_enabled": True,
            "show_cot_steps": True,
            "structured_output_enabled": False
        }
    }
)

# Process message
result = await orchestrator.process_user_message(message_input)
```

### TypeScript (Frontend)

```typescript
import { apiClient, ConversationConfigMetadata } from './services/apiClient';

// Define config overrides with type safety
const config: ConversationConfigMetadata = {
  cot_enabled: true,
  show_cot_steps: true,
  structured_output_enabled: false
};

// Send message with config
const message = await apiClient.sendConversationMessage(
  sessionId,
  "Explain how neural networks work",
  config
);
```

### REST API

**Endpoint:** `POST /api/conversations/{session_id}/messages`

**Request Body:**
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "content": "Explain how neural networks work",
  "role": "user",
  "message_type": "question",
  "metadata": {
    "config_metadata": {
      "cot_enabled": true,
      "show_cot_steps": true,
      "structured_output_enabled": false
    }
  }
}
```

**Response:**
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174000",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "content": "Neural networks are computational models...",
  "role": "assistant",
  "message_type": "answer",
  "metadata": {
    "cot_output": {
      "reasoning_steps": [
        "First, I'll explain the basic concept...",
        "Then, I'll describe the architecture..."
      ],
      "final_answer": "Neural networks are..."
    },
    "sources": [
      {
        "document_name": "neural-networks.pdf - Page 5",
        "content": "...",
        "metadata": {"score": 0.95, "page_number": 5}
      }
    ],
    "token_analysis": {
      "user_tokens": 8,
      "assistant_tokens": 150,
      "total_tokens": 158
    }
  }
}
```

## Common Patterns

### Enable CoT for Complex Questions

```typescript
// Automatically enable CoT for complex multi-part questions
const isComplexQuestion = content.includes("how") && content.includes("why");

const config: ConversationConfigMetadata = {
  cot_enabled: isComplexQuestion,
  show_cot_steps: isComplexQuestion
};

await apiClient.sendConversationMessage(sessionId, content, config);
```

### Disable Structured Output for Raw Responses

```typescript
// Get raw unstructured response
const config: ConversationConfigMetadata = {
  structured_output_enabled: false
};

await apiClient.sendConversationMessage(sessionId, content, config);
```

### Control Conversation Context

```typescript
// Use specific context window
const config: ConversationConfigMetadata = {
  conversation_context: "User asked about ML. Previous discussion covered AI basics.",
  message_history: ["What is AI?", "AI is...", "What about ML?"],
  conversation_aware: true
};

await apiClient.sendConversationMessage(sessionId, content, config);
```

## Migration Guide

### For API Clients

**Before (without config_metadata):**
```typescript
// No way to override default behavior
await apiClient.sendConversationMessage(sessionId, content);
```

**After (with config_metadata):**
```typescript
// Override defaults as needed
await apiClient.sendConversationMessage(sessionId, content, {
  cot_enabled: false,  // Disable CoT for this request
  show_cot_steps: false
});
```

### TypeScript Migration

**Before:**
```typescript
async sendConversationMessage(
  sessionId: string,
  content: string,
  configMetadata?: Record<string, any>  // ❌ No type safety
): Promise<ConversationMessage>
```

**After:**
```typescript
async sendConversationMessage(
  sessionId: string,
  content: string,
  configMetadata?: ConversationConfigMetadata  // ✅ Type-safe
): Promise<ConversationMessage>
```

## Best Practices

1. **Use TypeScript Interface**: Always use `ConversationConfigMetadata` for type safety
2. **Set Minimal Overrides**: Only override what you need; rely on defaults otherwise
3. **Handle Gracefully**: Don't assume config will be applied; system may fall back to defaults
4. **Avoid Sensitive Data**: Never include credentials or PII in `config_metadata`
5. **Log Unexpected Behavior**: If config doesn't apply, check backend logs for validation warnings

## Troubleshooting

### Config Not Being Applied

**Problem:** Your `config_metadata` settings are being ignored

**Solutions:**
1. Check backend logs for validation warnings
2. Verify you're using whitelisted keys only
3. Ensure `config_metadata` is a dict/object, not a string
4. Confirm the field is nested inside `metadata`: `metadata.config_metadata`

**Example Debug Log:**
```
⚠️ MESSAGE ORCHESTRATOR: Filtered disallowed config keys: {'malicious_key', '__proto__'}
```

### TypeScript Type Errors

**Problem:** Type errors when using `config_metadata`

**Solution:**
```typescript
// Import the interface
import { ConversationConfigMetadata } from './services/apiClient';

// Use it for type checking
const config: ConversationConfigMetadata = {
  cot_enabled: true,  // ✅ Auto-complete works
  invalid_key: true   // ❌ TypeScript error
};
```

### Invalid Config Type

**Problem:** Passing string instead of object

**Wrong:**
```json
{
  "metadata": {
    "config_metadata": "cot_enabled=true"  // ❌ String
  }
}
```

**Correct:**
```json
{
  "metadata": {
    "config_metadata": {  // ✅ Object
      "cot_enabled": true
    }
  }
}
```

## Related Documentation

- [Conversation API Overview](./endpoints.md#conversation-endpoints)
- [Message Schemas](./schemas.md#message-schemas)
- [Chain of Thought](../features/chain-of-thought.md)
- [Error Handling](./error-handling.md)

## Changelog

### Version 1.1.0 (PR #631)

**Added:**
- `config_metadata` field to `MessageMetadata` schema
- Whitelist-based security validation
- TypeScript `ConversationConfigMetadata` interface
- Enhanced error handling with graceful fallbacks

**Security:**
- Implemented whitelist validation to prevent injection attacks
- Protection against prototype pollution
- Comprehensive audit logging for filtered keys
