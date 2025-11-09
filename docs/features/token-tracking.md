# Token Tracking

RAG Modulo includes comprehensive token tracking for cost monitoring and usage analytics.

## Overview

Token tracking monitors LLM token usage across all operations:

- Search queries
- Conversation messages
- Chain of Thought reasoning steps
- Document summarization

## Token Counting

### Automatic Tracking

Tokens are automatically counted and logged for:

- **Input tokens**: Query + context sent to LLM
- **Output tokens**: Generated response
- **Total tokens**: Sum of input + output

### Storage

Token counts are persisted to PostgreSQL:

```python
{
  "total_tokens": 1250,
  "input_tokens": 800,
  "output_tokens": 450,
  "model": "gpt-4",
  "timestamp": "2025-01-09T10:00:00Z"
}
```

## Usage Monitoring

### Per-User Tracking

```bash
# Get user token usage
./rag-cli users tokens user_123

# Get usage by date range
./rag-cli users tokens user_123 \
  --start 2025-01-01 \
  --end 2025-01-31
```

### Per-Collection Tracking

```bash
# Get collection token usage
./rag-cli collections tokens col_123abc
```

### API Access

```python
GET /api/users/{user_id}/token-usage
GET /api/collections/{collection_id}/token-usage
```

## Cost Estimation

Token costs vary by provider and model:

| Provider | Model | Input (per 1K) | Output (per 1K) |
|----------|-------|----------------|-----------------|
| OpenAI | GPT-4 | $0.03 | $0.06 |
| OpenAI | GPT-3.5 | $0.001 | $0.002 |
| Anthropic | Claude 3 | $0.015 | $0.075 |

Calculate costs:

```python
cost = (input_tokens / 1000) * input_rate + (output_tokens / 1000) * output_rate
```

## Configuration

Set token limits per user:

```env
MAX_TOKENS_PER_USER_DAILY=100000
MAX_TOKENS_PER_QUERY=5000
TOKEN_WARNING_THRESHOLD=80000
```

## Warnings

Users receive warnings when approaching limits:

```json
{
  "warning": "Token usage at 85% of daily limit",
  "current_usage": 85000,
  "limit": 100000,
  "remaining": 15000
}
```

## See Also

- [API Documentation](../api/index.md)
- [Features Overview](index.md)
- [LLM Integration](llm-integration.md)
