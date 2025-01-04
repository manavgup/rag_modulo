from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from string import Formatter
from uuid import UUID, uuid4

from rag_solution.models.prompt_template import PromptTemplate
from core.logging_utils import get_logger

logger = get_logger("schemas.prompt_template_schema")

class PromptTemplateBase(BaseModel):
    """Base schema for prompt templates with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    provider: str = Field(..., min_length=1, max_length=50, description="LLM provider")
    description: Optional[str] = Field(None, description="Template description")
    system_prompt: str = Field(..., min_length=1, description="System prompt for the LLM")
    context_prefix: str = Field(..., min_length=1, max_length=255, description="Prefix for context section")
    query_prefix: str = Field(..., min_length=1, max_length=255, description="Prefix for query section")
    answer_prefix: str = Field(..., min_length=1, max_length=255, description="Prefix for answer section")
    is_default: bool = Field(False, description="Whether this is the default template for the provider")
    input_variables: Optional[List[str]] = Field(None, description="List of variable names that can be used in the template")
    template_format: Optional[str] = Field(None, description="Format string containing variables to be replaced")
    
    def format_prompt(self, **kwargs) -> str:
        """Format the complete prompt using provided variables.
        
        Args:
            **kwargs: Key-value pairs corresponding to placeholders in the template.
            
        Returns:
            str: The complete formatted prompt string.
            
        Raises:
            ValueError: If required variables are missing or template format is invalid.
        """
        # Validate variables if input_variables is defined
        if self.input_variables:
            missing_vars = [var for var in self.input_variables if var not in kwargs]
            if missing_vars:
                raise ValueError(f"Missing required variables: {', '.join(missing_vars)}")

        # Format the template if provided, otherwise use question directly
        try:
            if self.template_format:
                formatted_query = self.template_format.format(**kwargs)
            else:
                # Default to using the question directly if no template format
                formatted_query = kwargs.get('question', '')
                if not formatted_query:
                    raise ValueError("No question provided and no template format defined")
        except KeyError as e:
            raise ValueError(f"Missing placeholder in template: {e}")

        # Assemble complete prompt with all components
        complete_prompt = [self.system_prompt]
        
        # Add context if provided
        if 'context' in kwargs:
            complete_prompt.append(f"{self.context_prefix}{kwargs['context']}")
        
        # Add formatted query
        complete_prompt.append(f"{self.query_prefix}{formatted_query}")
        
        # Add answer prefix
        complete_prompt.append(self.answer_prefix)
        logger.info(f"Complete prompt: {complete_prompt}")
        return "\n\n".join(complete_prompt)

    @model_validator(mode='after')
    def validate_template_format(self) -> 'PromptTemplateBase':
        """Validate that template format only uses declared variables."""
        if self.template_format and self.input_variables:
            # Extract variables from template
            formatter = Formatter()
            template_vars = {v[1] for v in formatter.parse(self.template_format) if v[1]}
            
            # Check if all template variables are declared
            undeclared_vars = template_vars - set(self.input_variables)
            if undeclared_vars:
                raise ValueError(f"Template contains undeclared variables: {undeclared_vars}")
                
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": PromptTemplate.EXAMPLE_TEMPLATES["watsonx"]
        }
    )

class PromptTemplateCreate(PromptTemplateBase):
    """Schema for creating a new prompt template.
    
    Example:
        {
            "name": "custom_template",
            "provider": "watsonx",
            "description": "Template with variables",
            "system_prompt": "You are a helpful AI assistant.",
            "context_prefix": "Context:\n",
            "query_prefix": "Question:\n",
            "answer_prefix": "Answer:\n",
            "input_variables": ["topic", "aspect"],
            "template_format": "Explain {topic}, focusing on {aspect}."
        }
    """
    
    @field_validator("provider")
    def validate_provider(cls, v: str) -> str:
        """Validate provider name."""
        valid_providers = {"watsonx", "openai", "anthropic", "llama2", "tii"}
        if v.lower() not in valid_providers:
            raise ValueError(f"Invalid provider. Must be one of: {', '.join(valid_providers)}")
        return v.lower()

class PromptTemplateUpdate(BaseModel):
    """Schema for updating an existing prompt template.
    
    Example:
        {
            "name": "updated_template",
            "description": "Updated description",
            "input_variables": ["subject"],
            "template_format": "What is {subject} and how does it work?"
        }
    """
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=1)
    context_prefix: Optional[str] = Field(None, min_length=1, max_length=255)
    query_prefix: Optional[str] = Field(None, min_length=1, max_length=255)
    answer_prefix: Optional[str] = Field(None, min_length=1, max_length=255)
    is_default: Optional[bool] = None
    input_variables: Optional[List[str]] = None
    template_format: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_template_format(self) -> 'PromptTemplateUpdate':
        """Validate that template format only uses declared variables."""
        if self.template_format and self.input_variables:
            formatter = Formatter()
            template_vars = {v[1] for v in formatter.parse(self.template_format) if v[1]}
            undeclared_vars = template_vars - set(self.input_variables)
            if undeclared_vars:
                raise ValueError(f"Template contains undeclared variables: {undeclared_vars}")
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "custom_watsonx",
                "description": "Updated description",
                "system_prompt": "Updated system prompt",
                "is_default": True,
                "input_variables": ["subject"],
                "template_format": "What is {subject} and how does it work?"
            }
        }
    )

class PromptTemplateResponse(PromptTemplateBase):
    """Schema for prompt template responses including metadata."""
    
    id: UUID = Field(..., description="Template unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                **PromptTemplate.EXAMPLE_TEMPLATES["watsonx"],
                "id": str(uuid4()),
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z"
            }
        }
    )
