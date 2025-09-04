from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, UUID4


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

    model_config = {
        "protected_namespaces": ()  # This removes the model_ namespace warnings
    }


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

    class Config:
        from_attributes = True
