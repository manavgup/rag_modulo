# Strict Typing Guidelines

!!! info "Purpose"
    This guide enforces strict typing discipline in the RAG Modulo backend,
    eliminating `dict[str, Any]` and `isinstance()` anti-patterns for a fully
    type-safe codebase.

## Code Smell Identification

### Anti-Pattern 1: `dict[str, Any]` - The Type Safety Killer

**Problem Code:**

```python
# ❌ BAD: Lazy typing
metadata: dict[str, Any] = Field(default_factory=dict)

# ❌ BAD: Runtime type checking
if isinstance(value, str):
    return process_string(value)
elif isinstance(value, int):
    return process_int(value)
```

**Why It's Bad:**

- No compile-time type checking
- Runtime errors instead of type errors
- No IDE autocomplete
- Forces defensive programming with `isinstance()`
- Hides design flaws in type hierarchy

### Anti-Pattern 2: `isinstance()` - Type Checking at Runtime

**Problem Code:**

```python
# ❌ BAD: Runtime type discrimination
def process_entity(entity: str | dict | ConversationEntity):
    if isinstance(entity, str):
        return ConversationEntity(entity_text=entity, ...)
    elif isinstance(entity, dict):
        return ConversationEntity(**entity)
    else:
        return entity
```

**Why It's Bad:**

- Type checking happens at runtime (too late!)
- Indicates union types should be separate functions
- Violates Single Responsibility Principle
- Makes code harder to reason about

### Anti-Pattern 3: Optional Chaining Everywhere

**Problem Code:**

```python
# ❌ BAD: Defensive programming due to poor typing
if metadata and "entities" in metadata and metadata["entities"]:
    entities = metadata.get("entities", [])
    if entities and len(entities) > 0:
        first_entity = entities[0]
        if first_entity and "text" in first_entity:
            text = first_entity["text"]
```

**Why It's Bad:**

- Indicates `metadata` should be a typed object
- Excessive None-checking suggests design flaw
- Hard to read and maintain

## Strict Typing Principles

### Principle 1: No `dict[str, Any]` Allowed

!!! rule "Rule"
    Every dictionary must have explicit types for both keys AND values.

**Allowed:**

```python
# ✅ GOOD: Specific string keys with specific value types
entity_scores: dict[str, float] = {"IBM": 0.95, "revenue": 0.82}

# ✅ GOOD: Use TypedDict for structured dictionaries
from typing import TypedDict

class SourceMetadata(TypedDict):
    document_id: str
    page_number: int
    relevance: float

# ✅ BETTER: Use Pydantic BaseModel instead of TypedDict
class SourceMetadata(BaseModel):
    document_id: str
    page_number: int
    relevance: float
```

**Forbidden:**

```python
# ❌ FORBIDDEN
metadata: dict[str, Any] = {}
config: dict = {}  # Even worse - no types at all!
```

### Principle 2: No `isinstance()` for Type Discrimination

!!! rule "Rule"
    Use function overloading, type narrowing, or separate functions instead.

**Pattern 1: Use `@overload` for Multiple Input Types**

```python
from typing import overload

# ✅ GOOD: Explicit overloads
@overload
def create_entity(text: str) -> ConversationEntity: ...

@overload
def create_entity(data: EntityDict) -> ConversationEntity: ...

def create_entity(input_data: str | EntityDict) -> ConversationEntity:
    # Type checker knows which branch based on input type
    if isinstance(input_data, str):  # OK here - validated by overload
        return ConversationEntity(entity_text=input_data, entity_type="other")
    else:
        return ConversationEntity(**input_data.dict())
```

#### Pattern 2: Separate Functions for Different Types

```python
# ✅ BETTER: Separate functions
def create_entity_from_text(
    text: str,
    entity_type: EntityType = "other"
) -> ConversationEntity:
    return ConversationEntity(
        entity_text=text,
        entity_type=entity_type,
        first_mentioned_turn=1
    )

def create_entity_from_dict(data: EntityDict) -> ConversationEntity:
    return ConversationEntity(**data.dict())
```

### Principle 3: Use Literal Types for Enums

!!! rule "Rule"
    Use `Literal` for fixed string values, `Enum` for more complex types.

```python
from typing import Literal
from enum import Enum

# ✅ GOOD: Literal for simple string constants
EntityType = Literal["organization", "person", "location", "date", "concept", "other"]

class ConversationEntity(BaseModel):
    entity_type: EntityType  # Type checker enforces valid values

# ✅ GOOD: Enum for values with behavior
class OutputFormat(str, Enum):
    CONCISE = "concise"
    DETAILED = "detailed"
    BULLET_POINTS = "bullet_points"
    STRUCTURED = "structured"

    def get_max_length(self) -> int:
        """Different formats have different max lengths."""
        return {
            OutputFormat.CONCISE: 200,
            OutputFormat.DETAILED: 800,
            OutputFormat.BULLET_POINTS: 500,
            OutputFormat.STRUCTURED: 600
        }[self]
```

### Principle 4: Use NewType for Semantic Typing

!!! rule "Rule"
    Create distinct types for semantically different strings/ints.

```python
from typing import NewType

# ✅ GOOD: Semantic types prevent mistakes
DocumentID = NewType("DocumentID", str)
ChunkID = NewType("ChunkID", str)
UserID = NewType("UserID", UUID4)

def get_document(doc_id: DocumentID) -> Document:
    ...

def get_chunk(chunk_id: ChunkID) -> Chunk:
    ...

# Type checker prevents mixing them up
doc_id = DocumentID("doc-123")
chunk_id = ChunkID("chunk-456")

get_document(chunk_id)  # ❌ Type error! chunk_id is not DocumentID
```

## Type-Safe Patterns

### Pattern 1: Builder Pattern (No isinstance)

```python
class ReasoningContextBuilder:
    """Type-safe builder for ReasoningContext - no isinstance() needed."""

    def __init__(self) -> None:
        self._documents = DocumentContextList()
        self._conversation: ConversationContext | None = None
        self._instructions = PromptInstructions()

    def add_document(
        self,
        text: str,
        source_id: SourceID,
        relevance_score: float,
        **kwargs: Any
    ) -> "ReasoningContextBuilder":
        """Add a document (type-safe, no dict unpacking)."""
        doc = DocumentContext(
            text=text,
            source_id=source_id,
            relevance_score=relevance_score,
            retrieval_rank=len(self._documents) + 1,
            **kwargs
        )
        self._documents.add_document(doc)
        return self

    def build(self) -> ReasoningContext:
        """Build final ReasoningContext."""
        return ReasoningContext(
            documents=self._documents,
            conversation=self._conversation,
            instructions=self._instructions
        )
```

### Pattern 2: Factory Methods (Instead of Runtime Checking)

```python
class ConversationContextFactory:
    """Factory for creating ConversationContext from various sources."""

    @staticmethod
    def from_search_input(search_input: SearchInput) -> ConversationContext:
        """Create from SearchInput (explicit, type-safe)."""
        config = search_input.config_metadata or {}

        # Build entities (type-safe conversion)
        entities = ConversationEntityList()
        for entity_text in config.get("conversation_entities", []):
            # Acceptable - validating external input
            if isinstance(entity_text, str):
                entities.add(ConversationEntity.from_text(entity_text))

        return ConversationContext(entities=entities)

    @staticmethod
    def from_session(session: ConversationSession) -> ConversationContext:
        """Create from ConversationSession (explicit, type-safe)."""
        return ConversationContext(
            entities=session.tracked_entities,
            message_history=session.messages
        )
```

### Pattern 3: Protocol-Based Interfaces

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class FormattableForLLM(Protocol):
    """Protocol for objects that can be formatted for LLM consumption."""

    def format_for_llm(self, include_metadata: bool = False) -> str:
        """Format this object for LLM prompt."""
        ...

# ✅ GOOD: Use protocol instead of isinstance()
def format_items_for_llm(items: list[FormattableForLLM]) -> str:
    """Format any items that implement FormattableForLLM protocol."""
    return "\n\n".join([item.format_for_llm() for item in items])
```

## Enforcement

### Mypy Configuration

Add to `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_explicit = true  # ✅ Forbid explicit Any
disallow_any_generics = true  # ✅ Forbid unparameterized generics
warn_redundant_casts = true
warn_unused_ignores = true
strict_equality = true
```

### Ruff Rules for Type Safety

```toml
[tool.ruff]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "ANN",  # flake8-annotations (require type hints)
    "PL",   # pylint
]

[tool.ruff.lint.flake8-annotations]
allow-star-arg-any = false
ignore-fully-untyped = false
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      # Forbid dict[str, Any]
      - id: forbid-dict-any
        name: Forbid dict[str, Any]
        entry: bash -c 'if grep -rn "dict\[str, Any\]" backend/rag_solution/;
          then echo "ERROR: dict[str, Any] is forbidden. Use Pydantic models.";
          exit 1; fi'
        language: system
        pass_filenames: false

      # Mypy strict checking
      - id: mypy-strict
        name: Mypy (strict)
        entry: mypy
        args: ["--strict", "--disallow-any-explicit"]
        language: system
        types: [python]
```

## Code Smell Checklist

### ✅ Allowed Patterns

- ✅ `Literal["option1", "option2"]` for constrained strings
- ✅ `NewType("SemanticType", str)` for semantic typing
- ✅ `TypedDict` for structured dictionaries
- ✅ `Protocol` for interface-based typing
- ✅ `@overload` for multiple input types
- ✅ Separate functions for different types
- ✅ Factory methods with explicit names
- ✅ Builder pattern for complex objects
- ✅ `Generic[T]` for type-safe collections

### ❌ Forbidden Patterns

- ❌ `dict[str, Any]` (use TypedDict or Pydantic)
- ❌ `dict` without type parameters
- ❌ `list[Any]` (use `list[SpecificType]`)
- ❌ `isinstance()` for type discrimination (use @overload)
- ❌ Excessive None-checking (indicates poor type design)
- ❌ `# type: ignore` without explanation

## Migration Strategy

### Phase 1: Add Strict Types (Week 1)

- Create new modules with strict typing
- All new code uses strict types
- No modifications to existing code

### Phase 2: Update Services (Week 2-3)

- Refactor services to use strict types
- Add factory methods and builders
- Keep legacy adapters for compatibility

### Phase 3: Enable Enforcement (Week 4)

- Enable strict mypy checking
- Add pre-commit hooks
- Fix any violations in new code

### Phase 4: Migrate Legacy Code (Ongoing)

- Gradually replace `dict[str, Any]` with typed models
- Remove `isinstance()` checks with proper overloads
- Update tests to use new types

## Related Documentation

- [Backend Development](index.md) - Backend development overview
- [Code Quality Standards](../code-quality-standards.md) - General code quality guidelines
- [Contributing Guidelines](../contributing.md) - How to contribute

## Summary

!!! success "Goal"
    Achieve 100% type-safe codebase with:

    - Zero `dict[str, Any]` usage
    - Zero runtime type checking via `isinstance()`
    - Complete IDE autocomplete support
    - Compile-time error detection
    - Self-documenting code through types
