# **feat: Implement Comprehensive Runtime Configuration Service** #227

## **Executive Summary**

Transform RAG Modulo's fragmented configuration management into a unified runtime configuration service that eliminates container restarts, enables per-collection optimization, and provides hierarchical configuration precedence while maintaining full backward compatibility.

## **Problem Statement**

### **Current State Analysis**

RAG Modulo currently suffers from **fragmented configuration management**:

1. **Static Environment Variables** (80+ parameters in `.env`)
   - Requires container restarts for any changes
   - No per-collection or per-user customization
   - Poor operational flexibility

2. **Database-Configurable Services** (partial coverage)
   - `LLMParametersService`: User-specific LLM parameters
   - `LLMProviderService`: System-wide provider settings
   - `PromptTemplateService`: User-specific templates
   - But missing: chunking, embedding, retrieval, query processing configs

3. **Architectural Inconsistency**
   - Some parameters runtime-configurable, others static
   - No unified precedence rules
   - Scattered configuration logic across multiple services

### **Impact on Users**

- **Poor RAG Quality**: Fixed chunking (400 chars, 10 overlap) creates fragmented context
- **Operational Overhead**: Container restarts for simple parameter changes
- **No Optimization**: Cannot tune parameters per document type or collection
- **Limited Experimentation**: No A/B testing or real-time optimization

## **Proposed Solution**

Implement a **Unified Runtime Configuration Service** that:
1. Consolidates all configurable parameters
2. Provides hierarchical precedence (Collection > User > Global > Environment)
3. Integrates seamlessly with existing services
4. Maintains full backward compatibility
5. Enables real-time parameter optimization

## **Detailed Technical Design**

### **1. Database Schema Changes**

#### **1.1 New Table: runtime_configs**

**Location**: `backend/alembic/versions/XXX_add_runtime_configs_table.py`

```sql
CREATE TABLE runtime_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,

    -- Configuration Type and Data
    config_type VARCHAR(50) NOT NULL CHECK (config_type IN (
        'chunking', 'llm', 'embedding', 'retrieval', 'query_rewriting',
        'question_generation', 'pipeline', 'provider', 'template'
    )),
    config_data JSONB NOT NULL,

    -- Metadata
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version INTEGER DEFAULT 1,
    parent_version UUID REFERENCES runtime_configs(id), -- For version tracking

    -- Precedence Flags
    is_default BOOLEAN DEFAULT false,
    is_global BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,

    -- Audit Trail
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),

    -- Constraints
    CONSTRAINT unique_user_default_per_type
        EXCLUDE (user_id, config_type) WHERE (is_default = true),
    CONSTRAINT unique_global_default_per_type
        EXCLUDE (config_type) WHERE (is_global = true AND is_default = true),
    CONSTRAINT unique_collection_config
        EXCLUDE (collection_id, config_type) WHERE (collection_id IS NOT NULL)
);

-- Performance Indexes
CREATE INDEX idx_runtime_configs_user_id ON runtime_configs(user_id);
CREATE INDEX idx_runtime_configs_collection_id ON runtime_configs(collection_id);
CREATE INDEX idx_runtime_configs_type ON runtime_configs(config_type);
CREATE INDEX idx_runtime_configs_default ON runtime_configs(is_default) WHERE is_default = true;
CREATE INDEX idx_runtime_configs_global ON runtime_configs(is_global) WHERE is_global = true;
CREATE INDEX idx_runtime_configs_active ON runtime_configs(is_active) WHERE is_active = true;
CREATE INDEX idx_runtime_configs_data ON runtime_configs USING GIN(config_data);
```

#### **1.2 New Table: runtime_config_history**

**Location**: `backend/alembic/versions/XXX_add_runtime_config_history.py`

```sql
CREATE TABLE runtime_config_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID REFERENCES runtime_configs(id) ON DELETE CASCADE,
    operation VARCHAR(20) NOT NULL CHECK (operation IN ('CREATE', 'UPDATE', 'DELETE')),
    old_data JSONB,
    new_data JSONB,
    changed_by UUID REFERENCES users(id),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reason TEXT
);

CREATE INDEX idx_config_history_config_id ON runtime_config_history(config_id);
CREATE INDEX idx_config_history_changed_at ON runtime_config_history(changed_at);
```

### **2. SQLAlchemy Models**

#### **2.1 RuntimeConfig Model**

**File**: `backend/rag_solution/models/runtime_config.py` (NEW)

```python
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import relationship

from rag_solution.models.base import Base


class ConfigType(str, Enum):
    CHUNKING = "chunking"
    LLM = "llm"
    EMBEDDING = "embedding"
    RETRIEVAL = "retrieval"
    QUERY_REWRITING = "query_rewriting"
    QUESTION_GENERATION = "question_generation"
    PIPELINE = "pipeline"
    PROVIDER = "provider"
    TEMPLATE = "template"


class RuntimeConfig(Base):
    __tablename__ = "runtime_configs"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    collection_id = Column(PGUUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"))

    config_type = Column(String(50), nullable=False)
    config_data = Column(JSONB, nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(Integer, default=1)
    parent_version = Column(PGUUID(as_uuid=True), ForeignKey("runtime_configs.id"))

    is_default = Column(Boolean, default=False)
    is_global = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    updated_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="runtime_configs")
    collection = relationship("Collection", back_populates="runtime_configs")
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])
    parent = relationship("RuntimeConfig", remote_side=[id])
    history = relationship("RuntimeConfigHistory", back_populates="config", cascade="all, delete-orphan")
```

### **3. Pydantic Schemas**

#### **3.1 Runtime Config Schemas**

**File**: `backend/rag_solution/schemas/runtime_config_schema.py` (NEW)

```python
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import UUID4, BaseModel, Field, field_validator


class ConfigType(str, Enum):
    CHUNKING = "chunking"
    LLM = "llm"
    EMBEDDING = "embedding"
    RETRIEVAL = "retrieval"
    QUERY_REWRITING = "query_rewriting"
    QUESTION_GENERATION = "question_generation"
    PIPELINE = "pipeline"
    PROVIDER = "provider"
    TEMPLATE = "template"


class RuntimeConfigBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    config_type: ConfigType
    config_data: Dict[str, Any]
    is_default: bool = False


class RuntimeConfigInput(RuntimeConfigBase):
    collection_id: Optional[UUID4] = None


class RuntimeConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    config_data: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class RuntimeConfigOutput(RuntimeConfigBase):
    id: UUID4
    user_id: UUID4
    collection_id: Optional[UUID4]
    version: int
    parent_version: Optional[UUID4]
    is_global: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID4]
    updated_by: Optional[UUID4]


# Specific Configuration Schemas

class ChunkingConfig(BaseModel):
    strategy: str = Field(..., pattern="^(fixed|semantic|paragraph|sentence)$")
    min_chunk_size: int = Field(..., ge=50, le=10000)
    max_chunk_size: int = Field(..., ge=100, le=50000)
    chunk_overlap: int = Field(..., ge=0, le=5000)
    semantic_threshold: float = Field(0.5, ge=0.0, le=1.0)

    @field_validator('max_chunk_size')
    def validate_max_chunk_size(cls, v, values):
        if 'min_chunk_size' in values and v <= values['min_chunk_size']:
            raise ValueError('max_chunk_size must be greater than min_chunk_size')
        return v

    @field_validator('chunk_overlap')
    def validate_chunk_overlap(cls, v, values):
        if 'min_chunk_size' in values and v >= values['min_chunk_size']:
            raise ValueError('chunk_overlap must be less than min_chunk_size')
        return v


class LLMConfig(BaseModel):
    provider_id: UUID4
    model_id: str
    max_new_tokens: int = Field(100, ge=1, le=4096)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    top_k: int = Field(50, ge=1, le=100)
    top_p: float = Field(0.95, ge=0.0, le=1.0)
    repetition_penalty: float = Field(1.1, ge=1.0, le=2.0)
    timeout: int = Field(30, ge=5, le=300)
    max_retries: int = Field(3, ge=1, le=10)


class EmbeddingConfig(BaseModel):
    provider_id: UUID4
    model_id: str
    embedding_dim: int = Field(384, ge=1, le=4096)
    batch_size: int = Field(100, ge=1, le=1000)
    timeout: int = Field(30, ge=5, le=300)


class RetrievalConfig(BaseModel):
    retrieval_type: str = Field("hybrid", pattern="^(vector|keyword|hybrid)$")
    number_of_results: int = Field(5, ge=1, le=100)
    vector_weight: float = Field(0.7, ge=0.0, le=1.0)
    keyword_weight: float = Field(0.3, ge=0.0, le=1.0)
    similarity_threshold: float = Field(0.6, ge=0.0, le=1.0)
    rerank: bool = False

    @field_validator('keyword_weight')
    def validate_weights(cls, v, values):
        if 'vector_weight' in values and abs(v + values['vector_weight'] - 1.0) > 0.01:
            raise ValueError('vector_weight + keyword_weight must equal 1.0')
        return v


class EffectiveConfig(BaseModel):
    """Complete effective configuration for a user/collection"""
    chunking: Optional[ChunkingConfig]
    llm: Optional[LLMConfig]
    embedding: Optional[EmbeddingConfig]
    retrieval: Optional[RetrievalConfig]
    query_rewriting: Optional[Dict[str, Any]]
    question_generation: Optional[Dict[str, Any]]
    template: Optional[Dict[str, Any]]

    # Metadata about config resolution
    resolution_path: Dict[str, str]  # Shows where each config came from
```

### **4. Service Layer**

#### **4.1 Runtime Configuration Service**

**File**: `backend/rag_solution/services/runtime_config_service.py` (NEW)

```python
import json
from functools import lru_cache
from typing import Any, Dict, Optional

from core.config import Settings
from core.custom_exceptions import NotFoundError, ValidationError
from core.logging_utils import get_logger
from pydantic import UUID4
from sqlalchemy.orm import Session

from rag_solution.models.runtime_config import ConfigType, RuntimeConfig
from rag_solution.repository.runtime_config_repository import RuntimeConfigRepository
from rag_solution.schemas.runtime_config_schema import (
    ChunkingConfig,
    EffectiveConfig,
    EmbeddingConfig,
    LLMConfig,
    RetrievalConfig,
    RuntimeConfigInput,
    RuntimeConfigOutput,
    RuntimeConfigUpdate,
)
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.prompt_template_service import PromptTemplateService

logger = get_logger("services.runtime_config")


class RuntimeConfigService:
    """Unified service for all runtime configuration management."""

    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.repository = RuntimeConfigRepository(db)

        # Integration with existing services for backward compatibility
        self.llm_parameters_service = LLMParametersService(db)
        self.llm_provider_service = LLMProviderService(db)
        self.prompt_template_service = PromptTemplateService(db)

        # Cache configuration
        self._cache_ttl = 300  # 5 minutes
        self._cache = {}

    # ========== CRUD Operations ==========

    def create_config(
        self,
        user_id: UUID4,
        config_input: RuntimeConfigInput
    ) -> RuntimeConfigOutput:
        """Create a new runtime configuration."""
        try:
            # Validate config_data based on config_type
            self._validate_config_data(config_input.config_type, config_input.config_data)

            # Check for existing default if setting as default
            if config_input.is_default:
                self._reset_defaults(user_id, config_input.config_type, config_input.collection_id)

            config = self.repository.create(user_id, config_input)

            # Clear cache
            self._clear_cache(user_id, config_input.collection_id)

            # Log configuration change
            logger.info(f"Created {config_input.config_type} config for user {user_id}")

            return RuntimeConfigOutput.model_validate(config)
        except Exception as e:
            logger.error(f"Failed to create config: {e}")
            raise ValidationError(f"Failed to create configuration: {str(e)}")

    def get_config(self, config_id: UUID4) -> RuntimeConfigOutput:
        """Get a specific configuration by ID."""
        config = self.repository.get_by_id(config_id)
        if not config:
            raise NotFoundError("RuntimeConfig", str(config_id))
        return RuntimeConfigOutput.model_validate(config)

    def update_config(
        self,
        config_id: UUID4,
        user_id: UUID4,
        config_update: RuntimeConfigUpdate
    ) -> RuntimeConfigOutput:
        """Update an existing configuration."""
        config = self.repository.get_by_id(config_id)
        if not config:
            raise NotFoundError("RuntimeConfig", str(config_id))

        # Verify ownership
        if config.user_id != user_id and not config.is_global:
            raise ValidationError("Cannot update configuration owned by another user")

        # Validate new config_data if provided
        if config_update.config_data:
            self._validate_config_data(config.config_type, config_update.config_data)

        updated_config = self.repository.update(config_id, config_update, user_id)

        # Clear cache
        self._clear_cache(config.user_id, config.collection_id)

        return RuntimeConfigOutput.model_validate(updated_config)

    def delete_config(self, config_id: UUID4, user_id: UUID4) -> bool:
        """Delete a configuration."""
        config = self.repository.get_by_id(config_id)
        if not config:
            raise NotFoundError("RuntimeConfig", str(config_id))

        # Verify ownership
        if config.user_id != user_id and not config.is_global:
            raise ValidationError("Cannot delete configuration owned by another user")

        success = self.repository.delete(config_id)

        if success:
            self._clear_cache(config.user_id, config.collection_id)

        return success

    # ========== Configuration Resolution ==========

    def get_effective_config(
        self,
        user_id: UUID4,
        collection_id: Optional[UUID4] = None,
        config_types: Optional[list[ConfigType]] = None
    ) -> EffectiveConfig:
        """
        Get complete effective configuration with hierarchical precedence.

        Precedence Order:
        1. Collection-specific configuration
        2. User-specific configuration
        3. Existing service defaults (for backward compatibility)
        4. Global runtime defaults
        5. Environment variable fallback
        """
        cache_key = f"effective:{user_id}:{collection_id}:{config_types}"

        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Build effective configuration
        effective = EffectiveConfig(
            chunking=None,
            llm=None,
            embedding=None,
            retrieval=None,
            query_rewriting=None,
            question_generation=None,
            template=None,
            resolution_path={}
        )

        # Get requested config types or all
        types_to_fetch = config_types or list(ConfigType)

        for config_type in types_to_fetch:
            config_data, source = self._resolve_config(
                user_id,
                collection_id,
                config_type
            )

            if config_data:
                # Map to appropriate field
                if config_type == ConfigType.CHUNKING:
                    effective.chunking = ChunkingConfig(**config_data)
                elif config_type == ConfigType.LLM:
                    effective.llm = LLMConfig(**config_data)
                elif config_type == ConfigType.EMBEDDING:
                    effective.embedding = EmbeddingConfig(**config_data)
                elif config_type == ConfigType.RETRIEVAL:
                    effective.retrieval = RetrievalConfig(**config_data)
                else:
                    # Store as raw dict for other types
                    setattr(effective, config_type.value, config_data)

                effective.resolution_path[config_type.value] = source

        # Cache the result
        self._cache[cache_key] = effective

        return effective

    def get_chunking_config(
        self,
        user_id: UUID4,
        collection_id: Optional[UUID4] = None
    ) -> ChunkingConfig:
        """Get effective chunking configuration."""
        config_data, _ = self._resolve_config(user_id, collection_id, ConfigType.CHUNKING)
        if config_data:
            return ChunkingConfig(**config_data)

        # Fallback to environment variables
        return ChunkingConfig(
            strategy=self.settings.chunking_strategy,
            min_chunk_size=self.settings.min_chunk_size,
            max_chunk_size=self.settings.max_chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            semantic_threshold=self.settings.semantic_threshold
        )

    def get_llm_config(
        self,
        user_id: UUID4,
        collection_id: Optional[UUID4] = None
    ) -> LLMConfig:
        """Get effective LLM configuration."""
        config_data, _ = self._resolve_config(user_id, collection_id, ConfigType.LLM)
        if config_data:
            return LLMConfig(**config_data)

        # Try existing LLMParametersService for backward compatibility
        llm_params = self.llm_parameters_service.get_latest_or_default_parameters(user_id)
        if llm_params:
            provider = self.llm_provider_service.get_user_provider(user_id)
            if provider:
                return LLMConfig(
                    provider_id=provider.id,
                    model_id=self.settings.rag_llm,
                    max_new_tokens=llm_params.max_new_tokens,
                    temperature=llm_params.temperature,
                    top_k=llm_params.top_k,
                    top_p=llm_params.top_p,
                    repetition_penalty=llm_params.repetition_penalty,
                    timeout=30,
                    max_retries=3
                )

        raise ValidationError("No LLM configuration available")

    # ========== Helper Methods ==========

    def _resolve_config(
        self,
        user_id: UUID4,
        collection_id: Optional[UUID4],
        config_type: ConfigType
    ) -> tuple[Optional[Dict[str, Any]], str]:
        """
        Resolve configuration with hierarchical precedence.
        Returns (config_data, source_description)
        """
        # 1. Collection-specific
        if collection_id:
            config = self.repository.get_collection_config(collection_id, config_type)
            if config:
                return config.config_data, f"collection:{collection_id}"

        # 2. User-specific
        config = self.repository.get_user_config(user_id, config_type)
        if config:
            return config.config_data, f"user:{user_id}"

        # 3. Global runtime default
        config = self.repository.get_global_config(config_type)
        if config:
            return config.config_data, "global"

        # 4. None (caller should check existing services or env)
        return None, "none"

    def _validate_config_data(self, config_type: ConfigType, config_data: Dict[str, Any]):
        """Validate configuration data based on type."""
        try:
            if config_type == ConfigType.CHUNKING:
                ChunkingConfig(**config_data)
            elif config_type == ConfigType.LLM:
                LLMConfig(**config_data)
            elif config_type == ConfigType.EMBEDDING:
                EmbeddingConfig(**config_data)
            elif config_type == ConfigType.RETRIEVAL:
                RetrievalConfig(**config_data)
            # Add more validation as needed
        except Exception as e:
            raise ValidationError(f"Invalid {config_type} configuration: {str(e)}")

    def _reset_defaults(
        self,
        user_id: UUID4,
        config_type: ConfigType,
        collection_id: Optional[UUID4]
    ):
        """Reset existing defaults when setting a new default."""
        if collection_id:
            # Collection-level defaults don't need resetting (unique constraint)
            pass
        else:
            # Reset user-level defaults
            self.repository.reset_user_defaults(user_id, config_type)

    def _clear_cache(self, user_id: UUID4, collection_id: Optional[UUID4] = None):
        """Clear cached configurations for a user/collection."""
        keys_to_remove = []
        for key in self._cache:
            if str(user_id) in key:
                if collection_id is None or str(collection_id) in key:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

    # ========== System Initialization ==========

    def sync_defaults_from_env(self):
        """
        Synchronize default configurations from environment variables.
        Called by SystemInitializationService at startup.
        """
        try:
            # Create global chunking default
            chunking_default = {
                "strategy": self.settings.chunking_strategy,
                "min_chunk_size": self.settings.min_chunk_size,
                "max_chunk_size": self.settings.max_chunk_size,
                "chunk_overlap": self.settings.chunk_overlap,
                "semantic_threshold": self.settings.semantic_threshold
            }

            self._ensure_global_default(ConfigType.CHUNKING, chunking_default)

            # Create global retrieval default
            retrieval_default = {
                "retrieval_type": getattr(self.settings, 'retrieval_type', 'hybrid'),
                "number_of_results": getattr(self.settings, 'number_of_results', 5),
                "vector_weight": getattr(self.settings, 'vector_weight', 0.7),
                "keyword_weight": getattr(self.settings, 'keyword_weight', 0.3),
                "similarity_threshold": getattr(self.settings, 'similarity_threshold', 0.6),
                "rerank": False
            }

            self._ensure_global_default(ConfigType.RETRIEVAL, retrieval_default)

            logger.info("Synchronized default configurations from environment")

        except Exception as e:
            logger.error(f"Failed to sync defaults from environment: {e}")
            # Don't fail startup on config sync failure

    def _ensure_global_default(self, config_type: ConfigType, config_data: Dict[str, Any]):
        """Ensure a global default configuration exists."""
        existing = self.repository.get_global_config(config_type)
        if not existing:
            self.repository.create_global_default(config_type, config_data)
```

#### **4.2 Repository Layer**

**File**: `backend/rag_solution/repository/runtime_config_repository.py` (NEW)

```python
from typing import Any, Dict, List, Optional

from pydantic import UUID4
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from rag_solution.models.runtime_config import ConfigType, RuntimeConfig
from rag_solution.schemas.runtime_config_schema import RuntimeConfigInput, RuntimeConfigUpdate


class RuntimeConfigRepository:
    """Repository for runtime configuration management."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: UUID4, config_input: RuntimeConfigInput) -> RuntimeConfig:
        """Create a new configuration."""
        config = RuntimeConfig(
            user_id=user_id,
            collection_id=config_input.collection_id,
            config_type=config_input.config_type,
            config_data=config_input.config_data,
            name=config_input.name,
            description=config_input.description,
            is_default=config_input.is_default,
            created_by=user_id,
            updated_by=user_id
        )

        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)

        return config

    def get_by_id(self, config_id: UUID4) -> Optional[RuntimeConfig]:
        """Get configuration by ID."""
        return self.db.query(RuntimeConfig).filter(
            RuntimeConfig.id == config_id,
            RuntimeConfig.is_active == True
        ).first()

    def get_collection_config(
        self,
        collection_id: UUID4,
        config_type: ConfigType
    ) -> Optional[RuntimeConfig]:
        """Get collection-specific configuration."""
        return self.db.query(RuntimeConfig).filter(
            RuntimeConfig.collection_id == collection_id,
            RuntimeConfig.config_type == config_type,
            RuntimeConfig.is_active == True
        ).first()

    def get_user_config(
        self,
        user_id: UUID4,
        config_type: ConfigType
    ) -> Optional[RuntimeConfig]:
        """Get user-specific configuration."""
        return self.db.query(RuntimeConfig).filter(
            RuntimeConfig.user_id == user_id,
            RuntimeConfig.collection_id.is_(None),
            RuntimeConfig.config_type == config_type,
            RuntimeConfig.is_default == True,
            RuntimeConfig.is_active == True
        ).first()

    def get_global_config(self, config_type: ConfigType) -> Optional[RuntimeConfig]:
        """Get global default configuration."""
        return self.db.query(RuntimeConfig).filter(
            RuntimeConfig.is_global == True,
            RuntimeConfig.config_type == config_type,
            RuntimeConfig.is_default == True,
            RuntimeConfig.is_active == True
        ).first()

    def update(
        self,
        config_id: UUID4,
        config_update: RuntimeConfigUpdate,
        user_id: UUID4
    ) -> RuntimeConfig:
        """Update an existing configuration."""
        config = self.get_by_id(config_id)

        # Track old version
        old_data = config.config_data.copy()

        # Update fields
        for field, value in config_update.model_dump(exclude_unset=True).items():
            setattr(config, field, value)

        config.version += 1
        config.updated_by = user_id

        self.db.commit()
        self.db.refresh(config)

        return config

    def delete(self, config_id: UUID4) -> bool:
        """Soft delete a configuration."""
        config = self.get_by_id(config_id)
        if config:
            config.is_active = False
            self.db.commit()
            return True
        return False

    def reset_user_defaults(self, user_id: UUID4, config_type: ConfigType):
        """Reset default flags for user configurations."""
        configs = self.db.query(RuntimeConfig).filter(
            RuntimeConfig.user_id == user_id,
            RuntimeConfig.config_type == config_type,
            RuntimeConfig.is_default == True
        ).all()

        for config in configs:
            config.is_default = False

        self.db.commit()

    def create_global_default(
        self,
        config_type: ConfigType,
        config_data: Dict[str, Any]
    ) -> RuntimeConfig:
        """Create a global default configuration."""
        config = RuntimeConfig(
            config_type=config_type,
            config_data=config_data,
            name=f"Global {config_type} Default",
            description=f"System-wide default configuration for {config_type}",
            is_default=True,
            is_global=True
        )

        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)

        return config
```

### **5. API Layer**

#### **5.1 Router Implementation**

**File**: `backend/rag_solution/router/runtime_config_router.py` (NEW)

```python
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.database import get_db
from rag_solution.schemas.runtime_config_schema import (
    ConfigType,
    EffectiveConfig,
    RuntimeConfigInput,
    RuntimeConfigOutput,
    RuntimeConfigUpdate,
)
from rag_solution.services.auth_service import AuthService
from rag_solution.services.runtime_config_service import RuntimeConfigService

router = APIRouter(prefix="/runtime-configs", tags=["Runtime Configuration"])


@router.post("/", response_model=RuntimeConfigOutput, status_code=status.HTTP_201_CREATED)
def create_runtime_config(
    config_input: RuntimeConfigInput,
    current_user=Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
    settings=Depends(get_settings)
):
    """Create a new runtime configuration."""
    service = RuntimeConfigService(db, settings)
    return service.create_config(current_user.id, config_input)


@router.get("/{config_id}", response_model=RuntimeConfigOutput)
def get_runtime_config(
    config_id: UUID4,
    current_user=Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
    settings=Depends(get_settings)
):
    """Get a specific runtime configuration."""
    service = RuntimeConfigService(db, settings)
    return service.get_config(config_id)


@router.put("/{config_id}", response_model=RuntimeConfigOutput)
def update_runtime_config(
    config_id: UUID4,
    config_update: RuntimeConfigUpdate,
    current_user=Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
    settings=Depends(get_settings)
):
    """Update an existing runtime configuration."""
    service = RuntimeConfigService(db, settings)
    return service.update_config(config_id, current_user.id, config_update)


@router.delete("/{config_id}")
def delete_runtime_config(
    config_id: UUID4,
    current_user=Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
    settings=Depends(get_settings)
):
    """Delete a runtime configuration."""
    service = RuntimeConfigService(db, settings)
    success = service.delete_config(config_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration deleted successfully"}


@router.get("/effective/{user_id}", response_model=EffectiveConfig)
def get_effective_config(
    user_id: UUID4,
    collection_id: Optional[UUID4] = Query(None),
    config_types: Optional[List[ConfigType]] = Query(None),
    current_user=Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
    settings=Depends(get_settings)
):
    """Get effective configuration for a user/collection."""
    service = RuntimeConfigService(db, settings)
    return service.get_effective_config(user_id, collection_id, config_types)


@router.post("/test")
def test_configuration(
    config_input: RuntimeConfigInput,
    sample_data: str = Query(..., description="Sample text to test chunking"),
    current_user=Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
    settings=Depends(get_settings)
):
    """Test a configuration against sample data."""
    # Implementation for testing configuration
    pass


@router.post("/sync-defaults")
def sync_defaults_from_env(
    current_user=Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
    settings=Depends(get_settings)
):
    """Sync default configurations from environment variables (admin only)."""
    # Check if user is admin
    service = RuntimeConfigService(db, settings)
    service.sync_defaults_from_env()
    return {"message": "Default configurations synchronized"}
```

### **6. Integration Points**

#### **6.1 SystemInitializationService Integration**

**File**: `backend/rag_solution/services/system_initialization_service.py` (MODIFY)

```python
# Add to __init__ method
from rag_solution.services.runtime_config_service import RuntimeConfigService

class SystemInitializationService:
    def __init__(self, db: Session, settings: Settings) -> None:
        # ... existing code ...
        self.runtime_config_service = RuntimeConfigService(db, settings)

    def initialize_system(self):
        """Run all system initialization tasks."""
        logger.info("Starting system initialization")

        # Existing initialization
        self.initialize_providers()

        # NEW: Sync runtime configurations from environment
        try:
            self.runtime_config_service.sync_defaults_from_env()
            logger.info("Runtime configurations synchronized")
        except Exception as e:
            logger.warning(f"Failed to sync runtime configurations: {e}")
            # Don't fail startup on config sync failure

        logger.info("System initialization complete")
```

#### **6.2 DataIngestionService Integration**

**File**: `backend/rag_solution/services/data_ingestion_service.py` (MODIFY)

```python
# Modify chunking configuration retrieval
from rag_solution.services.runtime_config_service import RuntimeConfigService

class DataIngestionService:
    def __init__(self, db: Session, settings: Settings):
        # ... existing code ...
        self.runtime_config_service = RuntimeConfigService(db, settings)

    def process_document(
        self,
        document_id: UUID4,
        user_id: UUID4,
        collection_id: UUID4
    ):
        # Get chunking configuration
        chunking_config = self.runtime_config_service.get_chunking_config(
            user_id=user_id,
            collection_id=collection_id
        )

        # Use configuration
        chunks = self._chunk_document(
            document.content,
            strategy=chunking_config.strategy,
            min_size=chunking_config.min_chunk_size,
            max_size=chunking_config.max_chunk_size,
            overlap=chunking_config.chunk_overlap
        )
```

#### **6.3 SearchService Integration**

**File**: `backend/rag_solution/services/search_service.py` (MODIFY)

```python
# Modify retrieval configuration
from rag_solution.services.runtime_config_service import RuntimeConfigService

class SearchService:
    def __init__(self, db: Session, settings: Settings):
        # ... existing code ...
        self.runtime_config_service = RuntimeConfigService(db, settings)

    def search(
        self,
        user_id: UUID4,
        collection_id: UUID4,
        query: str
    ):
        # Get retrieval configuration
        retrieval_config = self.runtime_config_service.get_retrieval_config(
            user_id=user_id,
            collection_id=collection_id
        )

        # Use configuration
        results = self._perform_search(
            query=query,
            retrieval_type=retrieval_config.retrieval_type,
            num_results=retrieval_config.number_of_results,
            vector_weight=retrieval_config.vector_weight,
            keyword_weight=retrieval_config.keyword_weight
        )
```

#### **6.4 PipelineService Integration**

**File**: `backend/rag_solution/services/pipeline_service.py` (MODIFY)

```python
# Modify configuration validation
from rag_solution.services.runtime_config_service import RuntimeConfigService

class PipelineService:
    def __init__(self, db: Session, settings: Settings):
        # ... existing code ...
        self.runtime_config_service = RuntimeConfigService(db, settings)

    def _validate_configuration(
        self,
        user_id: UUID4,
        collection_id: Optional[UUID4] = None
    ) -> PipelineConfiguration:
        # Get effective configuration
        effective_config = self.runtime_config_service.get_effective_config(
            user_id=user_id,
            collection_id=collection_id
        )

        # Build pipeline configuration
        return PipelineConfiguration(
            llm_config=effective_config.llm or self._get_fallback_llm_config(user_id),
            embedding_config=effective_config.embedding,
            retrieval_config=effective_config.retrieval,
            chunking_config=effective_config.chunking,
            template_config=effective_config.template
        )
```

### **7. Testing Requirements**

#### **7.1 Unit Tests**

**File**: `backend/tests/unit/test_runtime_config_service.py` (NEW)

```python
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from rag_solution.services.runtime_config_service import RuntimeConfigService
from rag_solution.schemas.runtime_config_schema import (
    ConfigType,
    RuntimeConfigInput,
    ChunkingConfig
)


class TestRuntimeConfigService:

    @pytest.fixture
    def service(self):
        db_mock = Mock()
        settings_mock = Mock()
        settings_mock.chunking_strategy = "semantic"
        settings_mock.min_chunk_size = 100
        settings_mock.max_chunk_size = 1200
        settings_mock.chunk_overlap = 150
        settings_mock.semantic_threshold = 0.5

        return RuntimeConfigService(db_mock, settings_mock)

    def test_create_config_success(self, service):
        """Test successful configuration creation."""
        user_id = uuid4()
        config_input = RuntimeConfigInput(
            name="Test Chunking Config",
            config_type=ConfigType.CHUNKING,
            config_data={
                "strategy": "semantic",
                "min_chunk_size": 200,
                "max_chunk_size": 1500,
                "chunk_overlap": 200,
                "semantic_threshold": 0.6
            },
            is_default=True
        )

        # Mock repository
        service.repository.create = Mock(return_value=Mock(id=uuid4()))

        result = service.create_config(user_id, config_input)

        assert result is not None
        service.repository.create.assert_called_once()

    def test_config_validation_chunking(self, service):
        """Test chunking configuration validation."""
        # Valid config
        valid_config = {
            "strategy": "semantic",
            "min_chunk_size": 200,
            "max_chunk_size": 1500,
            "chunk_overlap": 150,
            "semantic_threshold": 0.6
        }

        # Should not raise
        service._validate_config_data(ConfigType.CHUNKING, valid_config)

        # Invalid config (max < min)
        invalid_config = {
            "strategy": "semantic",
            "min_chunk_size": 1500,
            "max_chunk_size": 200,
            "chunk_overlap": 150,
            "semantic_threshold": 0.6
        }

        with pytest.raises(ValidationError):
            service._validate_config_data(ConfigType.CHUNKING, invalid_config)

    def test_effective_config_precedence(self, service):
        """Test configuration precedence resolution."""
        user_id = uuid4()
        collection_id = uuid4()

        # Mock repository responses
        collection_config = Mock(config_data={"strategy": "semantic"})
        user_config = Mock(config_data={"strategy": "fixed"})
        global_config = Mock(config_data={"strategy": "paragraph"})

        # Test collection precedence
        service.repository.get_collection_config = Mock(return_value=collection_config)
        service.repository.get_user_config = Mock(return_value=user_config)
        service.repository.get_global_config = Mock(return_value=global_config)

        config_data, source = service._resolve_config(
            user_id, collection_id, ConfigType.CHUNKING
        )

        assert config_data["strategy"] == "semantic"
        assert "collection" in source

        # Test user precedence (no collection config)
        service.repository.get_collection_config = Mock(return_value=None)

        config_data, source = service._resolve_config(
            user_id, collection_id, ConfigType.CHUNKING
        )

        assert config_data["strategy"] == "fixed"
        assert "user" in source

    def test_cache_invalidation(self, service):
        """Test cache invalidation on config change."""
        user_id = uuid4()
        collection_id = uuid4()

        # Add to cache
        cache_key = f"effective:{user_id}:{collection_id}:None"
        service._cache[cache_key] = Mock()

        # Clear cache
        service._clear_cache(user_id, collection_id)

        assert cache_key not in service._cache

    def test_backward_compatibility_llm_params(self, service):
        """Test backward compatibility with LLMParametersService."""
        user_id = uuid4()

        # Mock no runtime config
        service.repository.get_user_config = Mock(return_value=None)
        service.repository.get_global_config = Mock(return_value=None)

        # Mock existing LLMParametersService
        mock_llm_params = Mock(
            max_new_tokens=500,
            temperature=0.7,
            top_k=50,
            top_p=0.95,
            repetition_penalty=1.1
        )
        service.llm_parameters_service.get_latest_or_default_parameters = Mock(
            return_value=mock_llm_params
        )

        mock_provider = Mock(id=uuid4())
        service.llm_provider_service.get_user_provider = Mock(return_value=mock_provider)

        llm_config = service.get_llm_config(user_id)

        assert llm_config.max_new_tokens == 500
        assert llm_config.temperature == 0.7
```

#### **7.2 Integration Tests**

**File**: `backend/tests/integration/test_runtime_config_integration.py` (NEW)

```python
import pytest
from uuid import uuid4

from rag_solution.services.runtime_config_service import RuntimeConfigService
from rag_solution.services.data_ingestion_service import DataIngestionService
from rag_solution.schemas.runtime_config_schema import ConfigType, RuntimeConfigInput


class TestRuntimeConfigIntegration:

    @pytest.mark.integration
    def test_chunking_config_affects_ingestion(self, db_session, settings):
        """Test that chunking config changes affect document processing."""
        user_id = uuid4()
        collection_id = uuid4()

        # Create runtime config service
        config_service = RuntimeConfigService(db_session, settings)

        # Create two different chunking configs
        config1 = RuntimeConfigInput(
            name="Small Chunks",
            config_type=ConfigType.CHUNKING,
            config_data={
                "strategy": "fixed",
                "min_chunk_size": 100,
                "max_chunk_size": 200,
                "chunk_overlap": 10,
                "semantic_threshold": 0.5
            },
            collection_id=collection_id
        )

        config2 = RuntimeConfigInput(
            name="Large Chunks",
            config_type=ConfigType.CHUNKING,
            config_data={
                "strategy": "semantic",
                "min_chunk_size": 500,
                "max_chunk_size": 1500,
                "chunk_overlap": 150,
                "semantic_threshold": 0.5
            },
            collection_id=collection_id
        )

        # Create ingestion service
        ingestion_service = DataIngestionService(db_session, settings)

        # Test with config1
        config_service.create_config(user_id, config1)
        chunks1 = ingestion_service.process_test_document(
            "Test document content " * 100,
            user_id,
            collection_id
        )

        # Delete config1 and create config2
        # ... test with config2

        assert len(chunks1) > len(chunks2)  # Smaller chunks = more pieces

    @pytest.mark.integration
    def test_config_precedence_full_stack(self, db_session, settings):
        """Test configuration precedence through full stack."""
        user_id = uuid4()
        collection_id = uuid4()

        config_service = RuntimeConfigService(db_session, settings)

        # Create global default
        global_config = RuntimeConfigInput(
            name="Global Default",
            config_type=ConfigType.CHUNKING,
            config_data={
                "strategy": "fixed",
                "min_chunk_size": 100,
                "max_chunk_size": 400,
                "chunk_overlap": 10,
                "semantic_threshold": 0.5
            },
            is_default=True
        )
        # Need to handle global config creation differently

        # Create user default
        user_config = RuntimeConfigInput(
            name="User Default",
            config_type=ConfigType.CHUNKING,
            config_data={
                "strategy": "semantic",
                "min_chunk_size": 200,
                "max_chunk_size": 800,
                "chunk_overlap": 50,
                "semantic_threshold": 0.5
            },
            is_default=True
        )
        config_service.create_config(user_id, user_config)

        # Create collection-specific
        collection_config = RuntimeConfigInput(
            name="Collection Specific",
            config_type=ConfigType.CHUNKING,
            config_data={
                "strategy": "paragraph",
                "min_chunk_size": 300,
                "max_chunk_size": 1200,
                "chunk_overlap": 100,
                "semantic_threshold": 0.5
            },
            collection_id=collection_id
        )
        config_service.create_config(user_id, collection_config)

        # Test resolution
        effective = config_service.get_effective_config(user_id, collection_id)

        assert effective.chunking.strategy == "paragraph"  # Collection wins
        assert "collection" in effective.resolution_path["chunking"]
```

#### **7.3 API Tests**

**File**: `backend/tests/api/test_runtime_config_api.py` (NEW)

```python
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


class TestRuntimeConfigAPI:

    @pytest.mark.api
    def test_create_runtime_config(self, client: TestClient, auth_headers):
        """Test creating a runtime configuration via API."""
        config_data = {
            "name": "Test Config",
            "config_type": "chunking",
            "config_data": {
                "strategy": "semantic",
                "min_chunk_size": 200,
                "max_chunk_size": 1200,
                "chunk_overlap": 150,
                "semantic_threshold": 0.5
            },
            "is_default": True
        }

        response = client.post(
            "/api/runtime-configs/",
            json=config_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        result = response.json()
        assert result["name"] == "Test Config"
        assert result["config_type"] == "chunking"

    @pytest.mark.api
    def test_get_effective_config(self, client: TestClient, auth_headers):
        """Test getting effective configuration via API."""
        user_id = uuid4()

        response = client.get(
            f"/api/runtime-configs/effective/{user_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        result = response.json()
        assert "chunking" in result
        assert "resolution_path" in result

    @pytest.mark.api
    def test_update_config_validation(self, client: TestClient, auth_headers):
        """Test configuration validation on update."""
        # Create a config first
        config_data = {
            "name": "Test Config",
            "config_type": "chunking",
            "config_data": {
                "strategy": "semantic",
                "min_chunk_size": 200,
                "max_chunk_size": 1200,
                "chunk_overlap": 150,
                "semantic_threshold": 0.5
            }
        }

        response = client.post(
            "/api/runtime-configs/",
            json=config_data,
            headers=auth_headers
        )
        config_id = response.json()["id"]

        # Try invalid update (max < min)
        update_data = {
            "config_data": {
                "strategy": "semantic",
                "min_chunk_size": 1500,
                "max_chunk_size": 200,
                "chunk_overlap": 150,
                "semantic_threshold": 0.5
            }
        }

        response = client.put(
            f"/api/runtime-configs/{config_id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "max_chunk_size must be greater than min_chunk_size" in response.json()["detail"]
```

### **8. Migration Scripts**

#### **8.1 Data Migration for Existing Configurations**

**File**: `backend/scripts/migrate_to_runtime_config.py` (NEW)

```python
#!/usr/bin/env python3
"""
Migration script to move existing configurations to runtime_configs table.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from core.database import get_db
from core.config import get_settings
from rag_solution.services.runtime_config_service import RuntimeConfigService
from rag_solution.schemas.runtime_config_schema import ConfigType


def migrate_llm_parameters(db: Session, runtime_service: RuntimeConfigService):
    """Migrate existing llm_parameters to runtime_configs."""
    print("Migrating LLM parameters...")

    # Query existing llm_parameters
    from rag_solution.models.llm_parameters import LLMParameters

    params_list = db.query(LLMParameters).filter(LLMParameters.is_active == True).all()

    for params in params_list:
        config_data = {
            "max_new_tokens": params.max_new_tokens,
            "temperature": params.temperature,
            "top_k": params.top_k,
            "top_p": params.top_p,
            "repetition_penalty": params.repetition_penalty,
            "timeout": 30,
            "max_retries": 3
        }

        # Create runtime config
        runtime_service.repository.create(
            user_id=params.user_id,
            config_input={
                "name": params.name or "Migrated LLM Config",
                "config_type": ConfigType.LLM,
                "config_data": config_data,
                "is_default": params.is_default
            }
        )

    print(f"Migrated {len(params_list)} LLM parameter configurations")


def migrate_prompt_templates(db: Session, runtime_service: RuntimeConfigService):
    """Migrate existing prompt_templates to runtime_configs."""
    print("Migrating prompt templates...")

    from rag_solution.models.prompt_template import PromptTemplate

    templates = db.query(PromptTemplate).filter(PromptTemplate.is_active == True).all()

    for template in templates:
        config_data = {
            "template_type": template.template_type,
            "system_prompt": template.system_prompt,
            "template_format": template.template_format,
            "input_variables": template.input_variables,
            "max_context_length": template.max_context_length,
            "context_strategy": template.context_strategy
        }

        runtime_service.repository.create(
            user_id=template.user_id,
            config_input={
                "name": template.name,
                "config_type": ConfigType.TEMPLATE,
                "config_data": config_data,
                "is_default": template.is_default
            }
        )

    print(f"Migrated {len(templates)} prompt templates")


def main():
    """Run migration."""
    settings = get_settings()
    db = next(get_db())

    try:
        runtime_service = RuntimeConfigService(db, settings)

        # Sync defaults from environment
        runtime_service.sync_defaults_from_env()

        # Migrate existing data
        migrate_llm_parameters(db, runtime_service)
        migrate_prompt_templates(db, runtime_service)

        print("Migration completed successfully")

    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

### **9. Performance Testing**

#### **9.1 Performance Benchmarks**

**File**: `backend/tests/performance/test_runtime_config_performance.py` (NEW)

```python
import pytest
import time
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestRuntimeConfigPerformance:

    @pytest.mark.performance
    def test_config_resolution_time(self, db_session, settings):
        """Test that config resolution meets < 10ms requirement."""
        service = RuntimeConfigService(db_session, settings)
        user_id = uuid4()
        collection_id = uuid4()

        # Warm up cache
        service.get_effective_config(user_id, collection_id)

        # Measure resolution time
        times = []
        for _ in range(100):
            start = time.perf_counter()
            config = service.get_effective_config(user_id, collection_id)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms

        avg_time = sum(times) / len(times)
        max_time = max(times)

        assert avg_time < 10, f"Average resolution time {avg_time}ms exceeds 10ms"
        assert max_time < 50, f"Max resolution time {max_time}ms exceeds 50ms"

    @pytest.mark.performance
    def test_concurrent_config_access(self, db_session, settings):
        """Test concurrent configuration access."""
        service = RuntimeConfigService(db_session, settings)
        user_ids = [uuid4() for _ in range(10)]

        def get_config(user_id):
            start = time.perf_counter()
            config = service.get_effective_config(user_id)
            end = time.perf_counter()
            return (end - start) * 1000

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_config, uid) for uid in user_ids * 10]

            times = []
            for future in as_completed(futures):
                times.append(future.result())

        avg_time = sum(times) / len(times)
        assert avg_time < 20, f"Concurrent access avg time {avg_time}ms exceeds 20ms"

    @pytest.mark.performance
    def test_cache_effectiveness(self, db_session, settings):
        """Test cache hit rate and effectiveness."""
        service = RuntimeConfigService(db_session, settings)
        user_id = uuid4()

        # First call - cache miss
        start = time.perf_counter()
        config1 = service.get_effective_config(user_id)
        miss_time = (time.perf_counter() - start) * 1000

        # Second call - cache hit
        start = time.perf_counter()
        config2 = service.get_effective_config(user_id)
        hit_time = (time.perf_counter() - start) * 1000

        assert hit_time < miss_time * 0.1, "Cache not providing expected speedup"
        assert config1 == config2, "Cached result doesn't match"
```

### **10. Success Criteria**

#### **10.1 Functional Requirements**
- ✅ Runtime configuration changes without container restart
- ✅ Hierarchical precedence (Collection > User > Global > Environment)
- ✅ Full backward compatibility with existing services
- ✅ Configuration validation with helpful error messages
- ✅ Configuration versioning and history tracking
- ✅ API endpoints for CRUD operations
- ✅ Configuration testing/preview capability

#### **10.2 Performance Requirements**
- ✅ Configuration resolution < 10ms average response time
- ✅ Document processing time increase < 5%
- ✅ Memory footprint increase < 100MB
- ✅ Cache hit rate > 90% for repeated requests
- ✅ Concurrent access support for 100+ simultaneous requests

#### **10.3 Quality Requirements**
- ✅ Unit test coverage > 90%
- ✅ Integration test coverage > 80%
- ✅ Zero breaking changes to existing APIs
- ✅ Comprehensive error handling and logging
- ✅ Database migration scripts for existing data
- ✅ Performance benchmarks passing

### **11. Implementation Phases**

#### **Phase 1: Foundation (Week 1-2)**
1. Create database schema and migrations
2. Implement SQLAlchemy models
3. Create Pydantic schemas
4. Implement RuntimeConfigService
5. Implement RuntimeConfigRepository
6. Add unit tests

#### **Phase 2: Integration (Week 3-4)**
1. Create API router and endpoints
2. Integrate with SystemInitializationService
3. Update DataIngestionService for chunking
4. Update SearchService for retrieval
5. Add integration tests
6. Add performance tests

#### **Phase 3: Migration (Month 2, Week 1-2)**
1. Create migration scripts for existing configs
2. Update PipelineService integration
3. Add backward compatibility layer
4. Update LLMProviderService integration
5. Add configuration UI components
6. Deploy to staging environment

#### **Phase 4: Rollout (Month 2, Week 3-4)**
1. Production deployment with feature flag
2. Gradual rollout to users
3. Monitor performance metrics
4. Collect user feedback
5. Bug fixes and optimizations

#### **Phase 5: Deprecation (Month 3+)**
1. Mark old services as deprecated
2. Migrate remaining configurations
3. Update documentation
4. Remove deprecated code (v2.0)

### **12. Rollback Plan**

If issues arise during deployment:

1. **Feature Flag**: Disable runtime config service via environment variable
2. **Database Rollback**: Revert migrations while preserving data
3. **Service Fallback**: Existing services continue to work
4. **Cache Clear**: Clear all configuration caches
5. **Monitoring**: Alert on configuration resolution failures

### **13. Documentation Updates**

Required documentation:

1. **API Documentation**: OpenAPI specs for new endpoints
2. **Migration Guide**: Step-by-step for existing users
3. **Configuration Guide**: How to use runtime configurations
4. **Developer Guide**: Integration patterns for new services
5. **Operations Guide**: Monitoring and troubleshooting

## **Conclusion**

This comprehensive implementation transforms RAG Modulo from a rigid, restart-required configuration system to a flexible, runtime-configurable platform that enables per-collection optimization, A/B testing, and real-time parameter tuning while maintaining full backward compatibility.
