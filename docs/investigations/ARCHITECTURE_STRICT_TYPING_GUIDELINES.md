# Strict Typing Guidelines: Eliminating Code Smells in CoT Architecture

**Date**: 2025-10-20
**Purpose**: Enforce strict typing discipline, eliminate `dict[str, Any]` and `isinstance()` anti-patterns

---

## Table of Contents

1. [Code Smell Identification](#code-smell-identification)
2. [Strict Typing Principles](#strict-typing-principles)
3. [Revised Type Hierarchy](#revised-type-hierarchy)
4. [Type-Safe Patterns](#type-safe-patterns)
5. [Mypy Configuration](#mypy-configuration)
6. [Pre-commit Enforcement](#pre-commit-enforcement)

---

## Code Smell Identification

### Anti-Pattern 1: `dict[str, Any]` - The Type Safety Killer

**Problem Code**:
```python
# ❌ BAD: Lazy typing
metadata: dict[str, Any] = Field(default_factory=dict)

# ❌ BAD: Runtime type checking
if isinstance(value, str):
    return process_string(value)
elif isinstance(value, int):
    return process_int(value)
```

**Why It's Bad**:
- No compile-time type checking
- Runtime errors instead of type errors
- No IDE autocomplete
- Forces defensive programming with `isinstance()`
- Hides design flaws in type hierarchy

---

### Anti-Pattern 2: `isinstance()` - Type Checking at Runtime

**Problem Code**:
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

**Why It's Bad**:
- Type checking happens at runtime (too late!)
- Indicates union types should be separate functions
- Violates Single Responsibility Principle
- Makes code harder to reason about

---

### Anti-Pattern 3: Optional Chaining Everywhere

**Problem Code**:
```python
# ❌ BAD: Defensive programming due to poor typing
if metadata and "entities" in metadata and metadata["entities"]:
    entities = metadata.get("entities", [])
    if entities and len(entities) > 0:
        first_entity = entities[0]
        if first_entity and "text" in first_entity:
            text = first_entity["text"]
```

**Why It's Bad**:
- Indicates `metadata` should be a typed object
- Excessive None-checking suggests design flaw
- Hard to read and maintain

---

## Strict Typing Principles

### Principle 1: **No `dict[str, Any]` Allowed**

**Rule**: Every dictionary must have explicit types for both keys AND values.

**Allowed**:
```python
# ✅ GOOD: Specific string keys with specific value types
entity_scores: dict[str, float] = {"IBM": 0.95, "revenue": 0.82}

# ✅ GOOD: Use TypedDict for structured dictionaries
from typing import TypedDict

class SourceMetadata(TypedDict):
    document_id: str
    page_number: int
    relevance: float

source_meta: SourceMetadata = {
    "document_id": "doc-123",
    "page_number": 42,
    "relevance": 0.89
}

# ✅ BETTER: Use Pydantic BaseModel instead of TypedDict
class SourceMetadata(BaseModel):
    document_id: str
    page_number: int
    relevance: float
```

**Forbidden**:
```python
# ❌ FORBIDDEN
metadata: dict[str, Any] = {}
config: dict = {}  # Even worse - no types at all!
```

---

### Principle 2: **No `isinstance()` for Type Discrimination**

**Rule**: Use function overloading, type narrowing, or separate functions instead.

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
        return ConversationEntity(entity_text=input_data, entity_type="other", first_mentioned_turn=1)
    else:
        return ConversationEntity(**input_data.dict())
```

**Pattern 2: Separate Functions for Different Types**

```python
# ✅ BETTER: Separate functions
def create_entity_from_text(text: str, entity_type: EntityType = "other") -> ConversationEntity:
    return ConversationEntity(
        entity_text=text,
        entity_type=entity_type,
        first_mentioned_turn=1
    )

def create_entity_from_dict(data: EntityDict) -> ConversationEntity:
    return ConversationEntity(**data.dict())

# Caller chooses the right function based on their data type
entity1 = create_entity_from_text("IBM")
entity2 = create_entity_from_dict(entity_dict)
```

**Pattern 3: Use Pydantic Validators for Flexible Input**

```python
from pydantic import field_validator, model_validator

class ConversationEntity(BaseModel):
    entity_text: str
    entity_type: Literal["organization", "person", "location", "date", "concept", "other"]
    confidence: float = 1.0
    first_mentioned_turn: int

    # ✅ GOOD: Pydantic handles type coercion
    @field_validator("entity_text", mode="before")
    @classmethod
    def ensure_string(cls, v: Any) -> str:
        """Pydantic validator handles type conversion."""
        if not isinstance(v, str):
            raise ValueError(f"entity_text must be str, got {type(v)}")
        return v.strip()
```

---

### Principle 3: **Use Literal Types for Enums**

**Rule**: Use `Literal` for fixed string values, `Enum` for more complex types.

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

---

### Principle 4: **Use NewType for Semantic Typing**

**Rule**: Create distinct types for semantically different strings/ints.

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

---

## Revised Type Hierarchy

### 1. Base Types with Zero `dict[str, Any]`

```python
from typing import Literal, NewType, Protocol
from pydantic import BaseModel, Field, field_validator
from enum import Enum

# Semantic types for IDs
DocumentID = NewType("DocumentID", str)
ChunkID = NewType("ChunkID", str)
SourceID = NewType("SourceID", str)

# Literal types for constrained strings
EntityType = Literal["organization", "person", "location", "date", "concept", "other"]
MessageRole = Literal["user", "assistant", "system"]
OutputFormat = Literal["concise", "detailed", "bullet_points", "structured"]
ReasoningVisibility = Literal["hidden", "brief", "detailed"]
ToneType = Literal["professional", "casual", "technical", "friendly"]


class DocumentContext(BaseModel):
    """Strictly typed document context - NO dict[str, Any]."""

    text: str = Field(..., min_length=1)
    source_id: SourceID
    document_name: str | None = None
    page_number: int | None = Field(None, ge=1)
    chunk_index: int | None = Field(None, ge=0)
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    retrieval_rank: int = Field(..., ge=1)

    # ✅ GOOD: Instead of metadata: dict[str, Any], use specific fields
    document_type: Literal["pdf", "docx", "html", "txt"] | None = None
    author: str | None = None
    created_date: datetime | None = None

    # If you MUST have extensibility, use a TypedDict or separate model
    class Config:
        frozen = True  # Immutable


class ConversationEntity(BaseModel):
    """Strictly typed entity - NO runtime type checking needed."""

    entity_text: str = Field(..., min_length=1, max_length=255)
    entity_type: EntityType  # Literal type enforces valid values
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    first_mentioned_turn: int = Field(..., ge=1)
    mention_count: int = Field(default=1, ge=1)

    class Config:
        frozen = True

    # ✅ GOOD: Factory methods instead of isinstance() checks
    @classmethod
    def from_text(
        cls,
        text: str,
        entity_type: EntityType = "other",
        turn_number: int = 1
    ) -> "ConversationEntity":
        """Create entity from plain text (explicit, no isinstance)."""
        return cls(
            entity_text=text.strip(),
            entity_type=entity_type,
            confidence=1.0,
            first_mentioned_turn=turn_number,
            mention_count=1
        )

    @classmethod
    def from_ner_result(
        cls,
        text: str,
        ner_type: str,
        confidence: float,
        turn_number: int
    ) -> "ConversationEntity":
        """Create entity from NER system output (explicit, no isinstance)."""
        # Map NER types to our EntityType
        type_mapping: dict[str, EntityType] = {
            "ORG": "organization",
            "PERSON": "person",
            "GPE": "location",
            "DATE": "date",
        }
        entity_type = type_mapping.get(ner_type.upper(), "other")

        return cls(
            entity_text=text.strip(),
            entity_type=entity_type,
            confidence=confidence,
            first_mentioned_turn=turn_number,
            mention_count=1
        )


class ConversationTurn(BaseModel):
    """Strictly typed conversation turn."""

    turn_number: int = Field(..., ge=1)
    role: MessageRole  # Literal type
    content: str = Field(..., min_length=1)
    timestamp: datetime | None = None
    entities_mentioned: list[str] = Field(default_factory=list)

    # ✅ GOOD: Specific optional fields instead of metadata: dict[str, Any]
    token_count: int | None = Field(None, ge=0)
    model_used: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)

    class Config:
        frozen = True


class PromptConstraint(BaseModel):
    """Type-safe constraint definition instead of list[str]."""

    constraint_text: str = Field(..., min_length=10)
    priority: Literal["must", "should", "nice_to_have"] = "must"
    enforced: bool = True

    class Config:
        frozen = True


class PromptInstructions(BaseModel):
    """Strictly typed prompt instructions - NO dict[str, Any]."""

    system_role: str = Field(default="You are a helpful AI assistant.", min_length=10)
    task_description: str = Field(
        default="Answer the user's question based on the provided documents.",
        min_length=10
    )
    output_format: OutputFormat = "concise"
    output_constraints: list[PromptConstraint] = Field(
        default_factory=lambda: [
            PromptConstraint(
                constraint_text="Answer based ONLY on the provided documents",
                priority="must"
            ),
            PromptConstraint(
                constraint_text="Do not mention the documents, sources, or your reasoning process",
                priority="must"
            ),
            PromptConstraint(
                constraint_text="If the documents don't contain the answer, say so clearly",
                priority="should"
            )
        ]
    )
    tone: ToneType = "professional"
    max_response_length: int | None = Field(None, ge=50, le=4000)
    include_sources: bool = False
    reasoning_visibility: ReasoningVisibility = "hidden"

    class Config:
        frozen = True

    def format_system_prompt(self) -> str:
        """Format complete system prompt from instructions."""
        # Filter must-have constraints
        must_constraints = [c.constraint_text for c in self.output_constraints if c.priority == "must"]
        should_constraints = [c.constraint_text for c in self.output_constraints if c.priority == "should"]

        parts = [
            self.system_role,
            "",
            f"Task: {self.task_description}",
            "",
            f"Output Format: {self.output_format.replace('_', ' ').title()}",
            f"Tone: {self.tone.title()}",
            "",
            "Required Constraints:"
        ]
        parts.extend([f"- {c}" for c in must_constraints])

        if should_constraints:
            parts.append("")
            parts.append("Recommendations:")
            parts.extend([f"- {c}" for c in should_constraints])

        if self.max_response_length:
            parts.append("")
            parts.append(f"Keep your response concise (max {self.max_response_length} tokens).")

        return "\n".join(parts)
```

---

### 2. Type-Safe Collections (No `list[Any]`)

```python
from typing import Generic, TypeVar, Iterator

T = TypeVar("T", bound=BaseModel)


class TypedCollection(BaseModel, Generic[T]):
    """Generic type-safe collection base class.

    Replaces: list[Any] with proper typing
    """

    items: list[T] = Field(default_factory=list)

    def add(self, item: T) -> None:
        """Add item to collection."""
        self.items.append(item)

    def get_by_index(self, index: int) -> T:
        """Get item by index (raises IndexError if out of range)."""
        return self.items[index]

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[T]:
        return iter(self.items)

    def __getitem__(self, index: int) -> T:
        return self.items[index]


class DocumentContextList(TypedCollection[DocumentContext]):
    """Type-safe document collection - no isinstance() needed."""

    def add_document(self, doc: DocumentContext) -> None:
        """Add document, preventing duplicates by source_id."""
        if not any(d.source_id == doc.source_id for d in self.items):
            self.add(doc)

    def get_top_k(self, k: int) -> list[DocumentContext]:
        """Get top-k documents by relevance score."""
        return sorted(self.items, key=lambda d: d.relevance_score, reverse=True)[:k]

    def format_for_llm(
        self,
        numbered: bool = True,
        include_sources: bool = False,
        max_documents: int | None = None
    ) -> str:
        """Format all documents for LLM prompt."""
        docs_to_format = self.items[:max_documents] if max_documents else self.items

        if numbered:
            return "\n\n".join([
                f"{i+1}. {doc.format_for_llm(include_metadata=include_sources)}"
                for i, doc in enumerate(docs_to_format)
            ])
        else:
            return "\n\n".join([
                doc.format_for_llm(include_metadata=include_sources)
                for doc in docs_to_format
            ])


class ConversationEntityList(TypedCollection[ConversationEntity]):
    """Type-safe entity collection."""

    def get_top_by_mentions(self, k: int) -> list[ConversationEntity]:
        """Get top-k entities by mention count."""
        return sorted(self.items, key=lambda e: e.mention_count, reverse=True)[:k]

    def get_by_type(self, entity_type: EntityType) -> list[ConversationEntity]:
        """Get all entities of a specific type."""
        return [e for e in self.items if e.entity_type == entity_type]

    def to_text_list(self) -> list[str]:
        """Extract just the text values (for query expansion)."""
        return [e.entity_text for e in self.items]


class ConversationTurnList(TypedCollection[ConversationTurn]):
    """Type-safe conversation turn collection."""

    def get_recent(self, n: int = 3) -> list[ConversationTurn]:
        """Get n most recent turns."""
        return self.items[-n:] if self.items else []

    def get_by_role(self, role: MessageRole) -> list[ConversationTurn]:
        """Get all turns by a specific role."""
        return [turn for turn in self.items if turn.role == role]

    def get_last_user_question(self) -> str | None:
        """Get the last user question."""
        user_turns = [t for t in reversed(self.items) if t.role == "user"]
        return user_turns[0].content if user_turns else None
```

---

### 3. Protocol-Based Interfaces (Instead of isinstance())

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class FormattableForLLM(Protocol):
    """Protocol for objects that can be formatted for LLM consumption.

    Use this instead of isinstance() checks.
    """

    def format_for_llm(self, include_metadata: bool = False) -> str:
        """Format this object for LLM prompt."""
        ...


@runtime_checkable
class HasRelevanceScore(Protocol):
    """Protocol for objects with relevance scores."""

    @property
    def relevance_score(self) -> float:
        """Get relevance score (0-1)."""
        ...


# ✅ GOOD: Use protocol instead of isinstance()
def format_items_for_llm(items: list[FormattableForLLM]) -> str:
    """Format any items that implement FormattableForLLM protocol."""
    return "\n\n".join([item.format_for_llm() for item in items])


# ✅ GOOD: Use protocol for generic sorting
def get_top_k_relevant(items: list[HasRelevanceScore], k: int) -> list[HasRelevanceScore]:
    """Get top-k items by relevance (works for any type with relevance_score)."""
    return sorted(items, key=lambda x: x.relevance_score, reverse=True)[:k]
```

---

### 4. Conversation Context (Zero isinstance())

```python
class ConversationContext(BaseModel):
    """Strictly typed conversation metadata."""

    entities: ConversationEntityList = Field(default_factory=ConversationEntityList)
    message_history: ConversationTurnList = Field(default_factory=ConversationTurnList)
    current_topic: str | None = None
    conversation_id: UUID4 | None = None

    # ✅ GOOD: No metadata: dict[str, Any]
    # Instead, specific optional fields for known use cases
    session_start_time: datetime | None = None
    total_turns: int = Field(default=0, ge=0)
    user_preferences: "UserPreferences | None" = None

    def get_recent_turns(self, n: int = 3) -> list[ConversationTurn]:
        """Get the n most recent turns."""
        return self.message_history.get_recent(n)

    def get_top_entities(self, k: int = 5) -> list[ConversationEntity]:
        """Get top-k entities by mention count."""
        return self.entities.get_top_by_mentions(k)

    def format_for_query_expansion(self) -> str:
        """Format conversation context for query expansion (safe usage)."""
        top_entities = self.entities.get_top_by_mentions(k=3)
        return " ".join([e.entity_text for e in top_entities])

    def get_contextual_hints(self) -> "ContextualHints":
        """Get contextual hints for the LLM (type-safe, no dict[str, Any])."""
        return ContextualHints(
            primary_entities=self.entities.to_text_list()[:3],
            current_topic=self.current_topic,
            turns_count=len(self.message_history),
            last_user_question=self.message_history.get_last_user_question()
        )


class ContextualHints(BaseModel):
    """Type-safe contextual hints (replaces dict[str, Any])."""

    primary_entities: list[str] = Field(default_factory=list)
    current_topic: str | None = None
    turns_count: int = Field(default=0, ge=0)
    last_user_question: str | None = None

    class Config:
        frozen = True


class UserPreferences(BaseModel):
    """Type-safe user preferences (instead of dict[str, Any])."""

    preferred_output_format: OutputFormat = "concise"
    preferred_tone: ToneType = "professional"
    include_sources: bool = False
    max_response_length: int = Field(default=800, ge=50, le=4000)

    class Config:
        frozen = True
```

---

### 5. Unified Reasoning Context (100% Type-Safe)

```python
class ReasoningContext(BaseModel):
    """Complete context for LLM reasoning - ZERO dict[str, Any]."""

    documents: DocumentContextList = Field(default_factory=DocumentContextList)
    conversation: ConversationContext | None = None
    instructions: PromptInstructions = Field(default_factory=PromptInstructions)

    # ✅ GOOD: Instead of reasoning_metadata: dict[str, Any]
    reasoning_strategy: Literal["single_shot", "chain_of_thought", "tree_of_thought"] = "single_shot"
    max_reasoning_steps: int = Field(default=3, ge=1, le=10)
    enable_self_critique: bool = False

    class Config:
        frozen = True  # Immutable for thread safety

    def format_for_llm_prompt(
        self,
        question: str,
        include_conversation_hints: bool = False
    ) -> str:
        """Format complete prompt for LLM, safely handling all context types."""
        system_prompt = self.instructions.format_system_prompt()
        documents_text = self.documents.format_for_llm(
            numbered=True,
            include_sources=self.instructions.include_sources,
            max_documents=10
        )

        prompt_parts = [
            system_prompt,
            "",
            "Documents:",
            documents_text,
            "",
            f"Question: {question}"
        ]

        # ✅ GOOD: Type-safe conversation hints (no isinstance checks)
        if include_conversation_hints and self.conversation:
            hints = self.conversation.get_contextual_hints()
            if hints.primary_entities:
                entity_context = ", ".join(hints.primary_entities)
                prompt_parts.append(f"(Context: This question relates to {entity_context})")

        prompt_parts.append("")
        prompt_parts.append("Answer:")

        return "\n".join(prompt_parts)

    def get_metadata_summary(self) -> "ReasoningMetadataSummary":
        """Get summary of all context (type-safe, no dict)."""
        return ReasoningMetadataSummary(
            document_count=len(self.documents),
            top_document_relevance=(
                self.documents.items[0].relevance_score
                if self.documents.items
                else 0.0
            ),
            conversation_turns=(
                len(self.conversation.message_history)
                if self.conversation
                else 0
            ),
            entities_tracked=(
                len(self.conversation.entities)
                if self.conversation
                else 0
            ),
            output_format=self.instructions.output_format,
            reasoning_visibility=self.instructions.reasoning_visibility,
            reasoning_strategy=self.reasoning_strategy
        )


class ReasoningMetadataSummary(BaseModel):
    """Type-safe metadata summary (replaces dict[str, Any])."""

    document_count: int = Field(ge=0)
    top_document_relevance: float = Field(ge=0.0, le=1.0)
    conversation_turns: int = Field(ge=0)
    entities_tracked: int = Field(ge=0)
    output_format: OutputFormat
    reasoning_visibility: ReasoningVisibility
    reasoning_strategy: Literal["single_shot", "chain_of_thought", "tree_of_thought"]

    class Config:
        frozen = True
```

---

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
            **kwargs  # Type checker validates against DocumentContext fields
        )
        self._documents.add_document(doc)
        return self

    def with_conversation(
        self,
        conversation: ConversationContext
    ) -> "ReasoningContextBuilder":
        """Set conversation context (explicit type)."""
        self._conversation = conversation
        return self

    def with_instructions(
        self,
        instructions: PromptInstructions
    ) -> "ReasoningContextBuilder":
        """Set prompt instructions (explicit type)."""
        self._instructions = instructions
        return self

    def build(self) -> ReasoningContext:
        """Build final ReasoningContext."""
        return ReasoningContext(
            documents=self._documents,
            conversation=self._conversation,
            instructions=self._instructions
        )


# Usage (100% type-safe)
context = (
    ReasoningContextBuilder()
    .add_document("IBM revenue was $57.4B", source_id=SourceID("doc1"), relevance_score=0.95)
    .add_document("IBM operates in 175 countries", source_id=SourceID("doc2"), relevance_score=0.88)
    .with_conversation(ConversationContext(
        entities=ConversationEntityList(items=[
            ConversationEntity.from_text("IBM", entity_type="organization", turn_number=1)
        ])
    ))
    .with_instructions(PromptInstructions(
        output_format="concise",
        reasoning_visibility="hidden"
    ))
    .build()
)
```

---

### Pattern 2: Factory Methods (Instead of Runtime Checking)

```python
class ConversationContextFactory:
    """Factory for creating ConversationContext from various sources.

    Explicit methods instead of isinstance() checks.
    """

    @staticmethod
    def from_search_input(search_input: SearchInput) -> ConversationContext:
        """Create from SearchInput (explicit, type-safe)."""
        # Extract typed config metadata
        config = search_input.config_metadata or {}

        # Build entities (type-safe conversion)
        entities = ConversationEntityList()
        for entity_text in config.get("conversation_entities", []):
            if isinstance(entity_text, str):  # Acceptable here - validating external input
                entities.add(ConversationEntity.from_text(entity_text, turn_number=1))

        # Build turn history
        turn_history = ConversationTurnList()
        for i, msg in enumerate(config.get("message_history", []), start=1):
            if isinstance(msg, str):  # Acceptable here - validating external input
                turn_history.add(ConversationTurn(
                    turn_number=i,
                    role="user",
                    content=msg
                ))

        return ConversationContext(
            entities=entities,
            message_history=turn_history,
            current_topic=config.get("conversation_context")
        )

    @staticmethod
    def from_session(session: ConversationSession) -> ConversationContext:
        """Create from ConversationSession (explicit, type-safe)."""
        # All types already validated by ConversationSession
        return ConversationContext(
            entities=session.tracked_entities,
            message_history=session.messages,
            current_topic=session.current_topic,
            conversation_id=session.id,
            session_start_time=session.created_at
        )

    @staticmethod
    def empty() -> ConversationContext:
        """Create empty context (for new conversations)."""
        return ConversationContext()
```

---

## Mypy Configuration

### Strict Mypy Settings

```ini
# pyproject.toml or mypy.ini
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_unimported = false
disallow_any_expr = false
disallow_any_decorated = false
disallow_any_explicit = true  # ✅ Forbid explicit Any
disallow_any_generics = true  # ✅ Forbid generic types without parameters
disallow_subclassing_any = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
strict_concatenate = true

# Forbid dict[str, Any] and similar patterns
[[tool.mypy.overrides]]
module = "rag_solution.services.*"
disallow_any_explicit = true
disallow_any_generics = true

# Custom error messages
[tool.mypy-rag_solution.services.chain_of_thought_service]
disallow_any_explicit = true  # No dict[str, Any] allowed
```

---

## Pre-commit Enforcement

### Ruff Rules for Type Safety

```toml
# pyproject.toml
[tool.ruff]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "ANN",  # flake8-annotations (require type hints)
    "S",    # bandit (security)
    "PL",   # pylint
    "RUF",  # ruff-specific rules
]

[tool.ruff.lint.per-file-ignores]
# Disable some rules for test files
"tests/*" = ["S101", "ANN201", "ANN001"]

[tool.ruff.lint.flake8-annotations]
allow-star-arg-any = false
ignore-fully-untyped = false
suppress-none-returning = false
suppress-dummy-args = false
mypy-init-return = true
```

### Custom Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      # Custom hook to detect dict[str, Any]
      - id: forbid-dict-any
        name: Forbid dict[str, Any]
        entry: bash -c 'if grep -rn "dict\[str, Any\]" backend/rag_solution/services/ backend/rag_solution/schemas/; then echo "ERROR: dict[str, Any] is forbidden. Use TypedDict or Pydantic models."; exit 1; fi'
        language: system
        pass_filenames: false

      # Custom hook to detect excessive isinstance()
      - id: warn-isinstance
        name: Warn about isinstance()
        entry: bash -c 'if grep -rn "isinstance(" backend/rag_solution/services/ | grep -v "# type: ignore" | grep -v "test_"; then echo "WARNING: Found isinstance() calls. Consider using @overload or separate functions."; fi'
        language: system
        pass_filenames: false
        stages: [push]  # Only warn on push, not commit

      # Mypy strict checking
      - id: mypy-strict
        name: Mypy (strict)
        entry: mypy
        args: [
          "--strict",
          "--disallow-any-explicit",
          "--disallow-any-generics",
          "backend/rag_solution"
        ]
        language: system
        types: [python]
        pass_filenames: false
```

---

## Summary: Code Smell Elimination Checklist

### ✅ Allowed Patterns
- ✅ `Literal["option1", "option2", ...]` for constrained strings
- ✅ `NewType("SemanticType", str)` for semantic typing
- ✅ `TypedDict` for structured dictionaries (or better: Pydantic)
- ✅ `Protocol` for interface-based typing
- ✅ `@overload` for multiple input types
- ✅ Separate functions for different types
- ✅ Factory methods with explicit names
- ✅ Builder pattern for complex object construction
- ✅ `Generic[T]` for type-safe collections

### ❌ Forbidden Patterns
- ❌ `dict[str, Any]` (use TypedDict or Pydantic)
- ❌ `dict` without type parameters
- ❌ `list[Any]` (use `list[SpecificType]`)
- ❌ `isinstance()` for type discrimination (use @overload)
- ❌ Excessive None-checking (indicates poor type design)
- ❌ Type comments instead of type hints
- ❌ `# type: ignore` without explanation

### Enforcement
1. **Mypy**: `--strict --disallow-any-explicit --disallow-any-generics`
2. **Ruff**: Enable `ANN` (annotations) rules
3. **Pre-commit**: Custom hooks to detect anti-patterns
4. **Code Review**: Reject PRs with `dict[str, Any]` or excessive `isinstance()`

---

## Migration Strategy

### Phase 1: Add Strict Types (Week 1)
- Create new modules with strict typing
- All new code uses strict types
- No modifications to existing code

### Phase 2: Update Services (Week 2-3)
- Refactor CoT service to use strict types
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

**Result**: 100% type-safe codebase with zero runtime type checking.
