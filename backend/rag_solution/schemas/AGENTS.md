# Schemas Layer - AI Agent Context

## Overview

The schemas layer contains Pydantic models for API request/response validation and serialization. Schemas define the contract between the API and clients, ensuring data integrity and type safety.

## Purpose

- **Input Validation**: Validate incoming API requests
- **Output Serialization**: Format API responses consistently
- **Type Safety**: Provide type hints for API operations
- **Documentation**: Auto-generate OpenAPI/Swagger docs

## Key Schemas

### Search Schemas (`search_schema.py`)
```python
class SearchInput(BaseModel):
    question: str
    collection_id: UUID4
    user_id: UUID4
    config_metadata: dict[str, Any] | None = None

class SearchOutput(BaseModel):
    answer: str
    sources: list[DocumentMetadata]
    cot_steps: list[ReasoningStep] | None = None
    token_usage: TokenUsage
```

### Collection Schemas (`collection_schema.py`)
```python
class CollectionCreate(BaseModel):
    name: str
    is_private: bool = False

class CollectionResponse(BaseModel):
    id: UUID4
    name: str
    status: CollectionStatus
    file_count: int
    created_at: datetime
```

### Conversation Schemas (`conversation_schema.py`)
```python
class ConversationSessionCreate(BaseModel):
    collection_id: UUID4

class MessageCreate(BaseModel):
    role: MessageRole
    content: str
    metadata: dict[str, Any] | None = None
```

## Patterns

### Request/Response Pairs
```python
# Input schema for POST/PUT
class ItemCreate(BaseModel):
    name: str
    config: dict[str, Any]

# Output schema for responses
class ItemResponse(BaseModel):
    id: UUID4
    name: str
    config: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True  # Allow ORM model conversion
```

### Validation
```python
from pydantic import field_validator

class MySchema(BaseModel):
    email: str

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Invalid email')
        return v.lower()
```

### Nested Schemas
```python
class Address(BaseModel):
    street: str
    city: str

class User(BaseModel):
    name: str
    address: Address  # Nested validation
```

## Best Practices

1. **Use Descriptive Names**: `CollectionCreate` not `CollectionInput`
2. **Version Schemas**: Keep old schemas for backward compatibility
3. **Document Fields**: Use `Field()` with description
4. **Default Values**: Provide sensible defaults
5. **Optional Fields**: Use `| None = None` for optional fields

## Related Documentation

- Models: `../models/AGENTS.md`
- Services: `../services/AGENTS.md`
- Router: `../router/AGENTS.md`
