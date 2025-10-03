# Models Layer - AI Agent Context

## Overview

The models layer contains SQLAlchemy ORM definitions representing database tables. These models define the data structure, relationships, and constraints for the PostgreSQL database. Models are the single source of truth for the database schema.

## Architectural Principles

### 1. Models Define Schema Only
- Database table structure
- Column definitions and types
- Relationships between tables
- Constraints and indexes
- **NO business logic**

### 2. Use SQLAlchemy 2.0 Patterns
- `Mapped[]` type annotations
- `mapped_column()` for column definitions
- `relationship()` for foreign keys
- Type-safe ORM operations

### 3. Relationship Loading Strategies
- `lazy="selectin"`: For collections (eager loading)
- `lazy="joined"`: For single items (eager loading)
- `lazy="noload"`: For optional relationships
- Default: `lazy="select"` (lazy loading)

## Model Categories

### Core Domain Models

#### Collection (`collection.py`)
**Purpose**: Document collection entity

**Key Fields**:
- `id`: UUID primary key
- `name`: Collection name
- `vector_db_name`: Name in vector database
- `status`: CollectionStatus enum (CREATED, PROCESSING, COMPLETED, FAILED)
- `is_private`: Privacy flag
- `created_at`, `updated_at`: Timestamps

**Relationships**:
- `files`: One-to-many with File
- `users`: Many-to-many via UserCollection
- `suggested_questions`: One-to-many with SuggestedQuestion
- `conversation_sessions`: One-to-many with ConversationSession
- `podcasts`: One-to-many with Podcast

**Methods**:
- `is_accessible_by_user()`: Check user access

#### File (`file.py`)
**Purpose**: Document file entity

**Key Fields**:
- `id`: UUID primary key
- `collection_id`: Foreign key to Collection
- `filename`: Original filename
- `file_path`: MinIO object path
- `file_size`: Size in bytes
- `mime_type`: Content type
- `status`: FileStatus enum
- `processing_metadata`: JSON metadata

**Relationships**:
- `collection`: Many-to-one with Collection

### Conversation Models

#### ConversationSession (`conversation_session.py`)
**Purpose**: Chat session entity

**Key Fields**:
- `id`: UUID primary key
- `user_id`: Foreign key to User
- `collection_id`: Foreign key to Collection
- `title`: Session title (LLM-generated)
- `created_at`, `updated_at`: Timestamps

**Relationships**:
- `user`: Many-to-one with User
- `collection`: Many-to-one with Collection
- `messages`: One-to-many with ConversationMessage
- `summary`: One-to-one with ConversationSummary

#### ConversationMessage (`conversation_message.py`)
**Purpose**: Individual chat message

**Key Fields**:
- `id`: UUID primary key
- `session_id`: Foreign key to ConversationSession
- `role`: MessageRole enum (USER, ASSISTANT, SYSTEM)
- `content`: Message text
- `metadata`: JSON metadata (sources, tokens, etc.)
- `created_at`: Timestamp

**Relationships**:
- `session`: Many-to-one with ConversationSession

#### ConversationSummary (`conversation_summary.py`)
**Purpose**: Conversation summary

**Key Fields**:
- `id`: UUID primary key
- `session_id`: Foreign key to ConversationSession
- `summary_text`: Generated summary
- `created_at`, `updated_at`: Timestamps

**Relationships**:
- `session`: One-to-one with ConversationSession

### LLM Configuration Models

#### LLMProvider (`llm_provider.py`)
**Purpose**: LLM provider configuration

**Key Fields**:
- `id`: UUID primary key
- `name`: Provider name (watsonx, openai, anthropic)
- `api_key`: Encrypted API key
- `config`: JSON configuration
- `is_active`: Status flag

**Relationships**:
- `models`: One-to-many with LLMModel
- `pipelines`: One-to-many with Pipeline

#### LLMModel (`llm_model.py`)
**Purpose**: LLM model configuration

**Key Fields**:
- `id`: UUID primary key
- `provider_id`: Foreign key to LLMProvider
- `model_name`: Model identifier
- `config`: JSON model settings

**Relationships**:
- `provider`: Many-to-one with LLMProvider

#### LLMParameters (`llm_parameters.py`)
**Purpose**: LLM generation parameters

**Key Fields**:
- `id`: UUID primary key
- `temperature`: Sampling temperature
- `max_tokens`: Maximum output tokens
- `top_p`, `top_k`: Sampling parameters

### Pipeline Models

#### Pipeline (`pipeline.py`)
**Purpose**: RAG pipeline configuration

**Key Fields**:
- `id`: UUID primary key
- `name`: Pipeline name
- `description`: Pipeline description
- `config`: JSON pipeline settings
- `is_default`: Default flag

**Relationships**:
- `provider`: Many-to-one with LLMProvider

### User Management Models

#### User (`user.py`)
**Purpose**: User account

**Key Fields**:
- `id`: UUID primary key
- `username`: Unique username
- `email`: Email address
- `hashed_password`: Password hash
- `is_active`: Account status
- `created_at`, `updated_at`: Timestamps

**Relationships**:
- `collections`: Many-to-many via UserCollection
- `teams`: Many-to-many via UserTeam
- `conversation_sessions`: One-to-many with ConversationSession

#### Team (`team.py`)
**Purpose**: Team/organization entity

**Key Fields**:
- `id`: UUID primary key
- `name`: Team name
- `description`: Team description

**Relationships**:
- `users`: Many-to-many via UserTeam

#### UserCollection (`user_collection.py`)
**Purpose**: User-Collection association

**Key Fields**:
- `user_id`: Foreign key to User
- `collection_id`: Foreign key to Collection
- `role`: UserRole enum (OWNER, EDITOR, VIEWER)
- `created_at`: Timestamp

**Relationships**:
- `user`: Many-to-one with User
- `collection`: Many-to-one with Collection

#### UserTeam (`user_team.py`)
**Purpose**: User-Team association

**Key Fields**:
- `user_id`: Foreign key to User
- `team_id`: Foreign key to Team
- `role`: TeamRole enum

**Relationships**:
- `user`: Many-to-one with User
- `team`: Many-to-one with Team

### Supporting Models

#### SuggestedQuestion (`question.py`)
**Purpose**: Pre-generated questions for collections

**Key Fields**:
- `id`: UUID primary key
- `collection_id`: Foreign key to Collection
- `question_text`: Question content
- `created_at`: Timestamp

**Relationships**:
- `collection`: Many-to-one with Collection

#### PromptTemplate (`prompt_template.py`)
**Purpose**: Reusable prompt templates

**Key Fields**:
- `id`: UUID primary key
- `name`: Template name
- `template_text`: Prompt template
- `variables`: JSON variable definitions

#### TokenWarning (`token_warning.py`)
**Purpose**: Token usage warnings

**Key Fields**:
- `id`: UUID primary key
- `user_id`: Foreign key to User
- `warning_type`: Warning type
- `threshold`: Usage threshold
- `created_at`: Timestamp

#### Podcast (`podcast.py`)
**Purpose**: Generated podcast entity

**Key Fields**:
- `id`: UUID primary key
- `collection_id`: Foreign key to Collection
- `title`: Podcast title
- `audio_file_path`: MinIO audio path
- `status`: PodcastStatus enum
- `metadata`: JSON podcast metadata

**Relationships**:
- `collection`: Many-to-one with Collection

## Common Patterns

### Model Definition Template

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from rag_solution.file_management.database import Base

if TYPE_CHECKING:
    from rag_solution.models.other_model import OtherModel


class MyModel(Base):
    """
    Represents MyModel entity.

    Attributes:
        id: Primary key
        name: Model name
        ...
    """

    __tablename__ = "my_models"

    # 🆔 Identification
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # ⚙️ Core Attributes
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)

    # 🔗 Foreign Keys
    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parents.id", ondelete="CASCADE")
    )

    # 🟢 Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 📊 Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # 🔗 Relationships
    parent: Mapped["ParentModel"] = relationship(
        "ParentModel",
        back_populates="children"
    )
    children: Mapped[list["ChildModel"]] = relationship(
        "ChildModel",
        back_populates="parent",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"MyModel(id='{self.id}', name='{self.name}')"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }
```

### Relationship Patterns

#### One-to-Many
```python
# Parent side
children: Mapped[list["Child"]] = relationship(
    "Child",
    back_populates="parent",
    cascade="all, delete-orphan"  # Delete children when parent deleted
)

# Child side
parent_id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("parents.id", ondelete="CASCADE")
)
parent: Mapped["Parent"] = relationship(
    "Parent",
    back_populates="children"
)
```

#### Many-to-Many (via association table)
```python
# User side
collections: Mapped[list["UserCollection"]] = relationship(
    "UserCollection",
    back_populates="user"
)

# Collection side
users: Mapped[list["UserCollection"]] = relationship(
    "UserCollection",
    back_populates="collection"
)

# Association model
class UserCollection(Base):
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id"), primary_key=True
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("collections.id"), primary_key=True
    )

    user: Mapped["User"] = relationship("User", back_populates="collections")
    collection: Mapped["Collection"] = relationship("Collection", back_populates="users")
```

### Enum Types

```python
from enum import Enum as PyEnum
from sqlalchemy import Enum

class StatusEnum(str, PyEnum):
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class MyModel(Base):
    status: Mapped[StatusEnum] = mapped_column(
        Enum(StatusEnum, name="status_enum", create_type=False),
        default=StatusEnum.CREATED
    )
```

### JSON Fields

```python
from sqlalchemy.dialects.postgresql import JSON

class MyModel(Base):
    metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )
```

## Best Practices

### 1. Always Use Type Annotations
```python
# ✅ GOOD
id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

# ❌ BAD
id = Column(UUID(as_uuid=True), primary_key=True)
```

### 2. Use Cascade Appropriately
```python
# Delete related records when parent deleted
children: Mapped[list["Child"]] = relationship(
    "Child",
    cascade="all, delete-orphan"
)

# Don't delete parent when child deleted
parent: Mapped["Parent"] = relationship(
    "Parent",
    # No cascade on child side
)
```

### 3. Index Frequently Queried Columns
```python
username: Mapped[str] = mapped_column(
    String,
    unique=True,
    index=True  # Add index for fast lookups
)
```

### 4. Use Server Defaults for Timestamps
```python
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now()  # Database sets value
)
```

### 5. Document Models and Fields
```python
class Collection(Base):
    """
    Represents a collection of documents.

    A collection groups related documents together for RAG operations.
    Each collection has its own vector database collection and can have
    multiple users with different permission levels.

    Attributes:
        id: Unique identifier
        name: Human-readable collection name
        vector_db_name: Name of collection in vector database
        status: Current processing status
        is_private: Whether collection is private to owner
    """
```

## Common Operations

### Creating Models
```python
# In migration or during testing
from rag_solution.file_management.database import Base, engine

Base.metadata.create_all(bind=engine)
```

### Querying Models
Done through repositories, not directly:
```python
# ❌ DON'T do this in services
collection = db.query(Collection).filter(Collection.id == id).first()

# ✅ DO this instead
collection = collection_repository.get(id)
```

## Database Migrations

While models define the schema, migrations are handled separately:
- Migrations in: `/backend/alembic/versions/`
- Create migration: `alembic revision --autogenerate -m "description"`
- Apply migration: `alembic upgrade head`

## Testing Models

### Unit Tests
```python
@pytest.mark.unit
def test_model_creation():
    collection = Collection(
        name="Test Collection",
        vector_db_name="test_collection"
    )
    assert collection.name == "Test Collection"
    assert collection.status == CollectionStatus.CREATED
```

### Integration Tests
```python
@pytest.mark.integration
def test_model_persistence(db_session):
    collection = Collection(name="Test")
    db_session.add(collection)
    db_session.commit()

    retrieved = db_session.query(Collection).filter_by(name="Test").first()
    assert retrieved.id == collection.id
```

## Related Documentation

- Repository Layer: `../repository/AGENTS.md`
- Service Layer: `../services/AGENTS.md`
- Schema Layer: `../schemas/AGENTS.md`
