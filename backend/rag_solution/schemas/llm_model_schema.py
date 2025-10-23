from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, ConfigDict, Field


class ModelType(str, Enum):
    GENERATION = "generation"
    EMBEDDING = "embedding"


class LLMModelInput(BaseModel):
    provider_id: UUID4
    model_id: str
    default_model_id: str
    model_type: ModelType
    timeout: int = Field(30)
    max_retries: int = Field(3)
    batch_size: int = Field(10)
    retry_delay: float = Field(1.0)
    concurrency_limit: int = Field(10)
    stream: bool = Field(False)
    rate_limit: int = Field(10)
    is_default: bool = Field(False)
    is_active: bool = Field(True)

    model_config = ConfigDict(protected_namespaces=())


class LLMModelUpdate(BaseModel):
    """Schema for partial updates to LLM models.

    All fields are optional to support partial updates from API.
    Use exclude_unset=True when converting to dict to only update provided fields.
    """

    model_id: str | None = None
    default_model_id: str | None = None
    model_type: ModelType | None = None
    timeout: int | None = None
    max_retries: int | None = None
    batch_size: int | None = None
    retry_delay: float | None = None
    concurrency_limit: int | None = None
    stream: bool | None = None
    rate_limit: int | None = None
    is_default: bool | None = None
    is_active: bool | None = None

    model_config = ConfigDict(protected_namespaces=())


class LLMModelOutput(BaseModel):
    id: UUID4
    provider_id: UUID4
    model_id: str
    default_model_id: str
    model_type: ModelType
    timeout: int
    max_retries: int
    batch_size: int
    retry_delay: float
    concurrency_limit: int
    stream: bool
    rate_limit: int
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
