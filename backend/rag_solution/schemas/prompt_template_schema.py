import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator, model_validator


class PromptTemplateType(str, Enum):
    """Enum for prompt template types."""

    RAG_QUERY = "RAG_QUERY"
    QUESTION_GENERATION = "QUESTION_GENERATION"
    RESPONSE_EVALUATION = "RESPONSE_EVALUATION"
    COT_REASONING = "COT_REASONING"
    CUSTOM = "CUSTOM"


class PromptTemplateBase(BaseModel):
    """Base schema for prompt templates."""

    name: str = Field(..., min_length=1, max_length=255)
    user_id: UUID4
    template_type: PromptTemplateType = PromptTemplateType.CUSTOM
    system_prompt: str | None = None
    template_format: str = Field(..., min_length=1)
    input_variables: dict[str, str] = Field(default={})
    example_inputs: dict[str, Any] | None = Field(default=None)
    context_strategy: dict[str, Any] | None = None
    max_context_length: int | None = Field(None, gt=0)
    stop_sequences: list[str] | None = None
    is_default: bool = False
    validation_schema: dict[str, Any] | None = None
    id: UUID4 | None = None
    context_prefix: str | None = None
    query_prefix: str | None = None
    answer_prefix: str | None = None

    model_config = ConfigDict(strict=True, extra="forbid", validate_assignment=True, populate_by_name=True)

    @field_validator("user_id", mode="before")
    @classmethod
    def parse_user_id(cls, v: str | UUID4) -> UUID4:
        """Ensure user_id is a valid UUID, converting from string if needed."""
        if isinstance(v, str):
            return UUID4(v)
        return v

    @model_validator(mode="after")
    def validate_template_variables(self) -> "PromptTemplateBase":
        """Validate that all template variables are defined in input_variables."""
        variables = set(re.findall(r"\{(\w+)\}", self.template_format))
        defined_vars = set(self.input_variables.keys())
        missing = variables - defined_vars

        if missing:
            raise ValueError(f"Template variables missing in input_variables: {missing}")

        return self

    @field_validator("template_format")
    @classmethod
    def validate_template_format(cls, v: str) -> str:
        """Validate template format syntax."""
        if not re.search(r"\{(\w+)\}", v):
            raise ValueError("Template format must contain at least one variable in {varname} format")
        return v

    @field_validator("input_variables")
    @classmethod
    def validate_variables(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate input variables."""
        if not v:
            raise ValueError("At least one input variable must be defined")
        return v

    @field_validator("system_prompt")
    @classmethod
    def validate_system_prompt(cls, v: str | None) -> str | None:
        """Validate system prompt exists."""
        if not v:
            return "You are a helpful AI assistant."  # Default prompt
        return v

    def format_prompt(self, **kwargs: Any) -> str:
        """Format the prompt template with the given variables."""
        try:
            return self.template_format.format(**kwargs)
        except KeyError as e:
            missing_var = str(e).strip("'")
            raise ValueError(f"Missing required variable: {missing_var}") from e
        except Exception as e:
            raise ValueError(f"Error formatting prompt: {e}") from e


class PromptTemplateInput(PromptTemplateBase):
    """Input schema for creating/updating prompt templates."""

    model_config = ConfigDict(strict=True, extra="forbid", validate_assignment=True, populate_by_name=True)

    @field_validator("template_type", mode="before")
    @classmethod
    def enforce_enum(cls, v: str | PromptTemplateType) -> PromptTemplateType:
        """Convert string to Enum if needed."""
        if isinstance(v, str):
            return PromptTemplateType(v)  # Convert string to Enum
        return v  # type: ignore[unreachable]


class PromptTemplateOutput(PromptTemplateBase):
    """Output schema for prompt templates."""

    id: UUID4
    user_id: UUID4
    created_at: datetime
    updated_at: datetime
    template_type: PromptTemplateType

    model_config = ConfigDict(from_attributes=True)

    @field_validator("template_type", mode="before")
    @classmethod
    def validate_template_type(cls, v: str | PromptTemplateType) -> PromptTemplateType:
        """Ensure template_type is an instance of the Enum."""
        if isinstance(v, str):
            return PromptTemplateType(v)  # Convert string to Enum
        return v  # type: ignore[unreachable]


class PromptTemplateInDB(PromptTemplateOutput):
    """Database schema for prompt templates."""
