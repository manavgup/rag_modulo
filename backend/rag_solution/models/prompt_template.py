from datetime import datetime
from typing import Optional, Dict
from sqlalchemy import Column, String, Boolean, DateTime, Text, UniqueConstraint
from sqlalchemy.sql import func

from rag_solution.file_management.database import Base

class PromptTemplate(Base):
    """SQLAlchemy model for prompt templates.
    
    Stores provider-specific prompt templates with system prompts and prefixes
    for context, query and answers.
    """
    
    __tablename__ = "prompt_templates"
    
    # Example templates for different LLM providers
    EXAMPLE_TEMPLATES: Dict[str, Dict[str, str]] = {
        "watsonx": {
            "name": "watsonx_granite_default",
            "provider": "watsonx",
            "description": "Default template for IBM Watsonx Granite models",
            "system_prompt": "You are a helpful AI assistant powered by IBM Watsonx. Answer questions accurately based on the provided context.",
            "context_prefix": "Context information:\n",
            "query_prefix": "Question:\n",
            "answer_prefix": "Answer:\n"
        },
        "llama2": {
            "name": "llama2_default",
            "provider": "llama2",
            "description": "Default template for Meta's LLaMA 2 models",
            "system_prompt": "[INST] <<SYS>> You are a helpful AI assistant. Always provide accurate and relevant answers based on the given context. <</SYS>>",
            "context_prefix": "Reference information:\n",
            "query_prefix": "User question:\n",
            "answer_prefix": "[/INST]\n"
        },
        "claude": {
            "name": "claude_default", 
            "provider": "anthropic",
            "description": "Default template for Anthropic's Claude models",
            "system_prompt": "Human: You are Claude, an AI assistant created by Anthropic. Please help answer questions based on the provided context information. Keep your responses accurate and focused on the given context.\n\nAssistant: I understand. I'll help answer questions by carefully analyzing the provided context and giving accurate, relevant responses.",
            "context_prefix": "Here is the relevant context:\n",
            "query_prefix": "\nHuman: ",
            "answer_prefix": "\nAssistant: "
        },
        "openai": {
            "name": "gpt4_default",
            "provider": "openai",
            "description": "Default template for OpenAI's GPT-4 model",
            "system_prompt": "You are a knowledgeable AI assistant. Your task is to provide accurate and helpful answers based on the given context. Focus on relevant information and avoid speculation.",
            "context_prefix": "Reference material:\n",
            "query_prefix": "User query:\n", 
            "answer_prefix": "Response:\n"
        },
        "falcon": {
            "name": "falcon_default",
            "provider": "tii",
            "description": "Default template for TII's Falcon models",
            "system_prompt": "You are an AI assistant based on the Falcon model. Answer questions accurately using the provided context.",
            "context_prefix": "Context:\n",
            "query_prefix": "Question:\n",
            "answer_prefix": "Answer:\n"
        }
    }
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)  # watsonx, openai, anthropic etc
    description = Column(Text, nullable=True)
    
    # Template components
    system_prompt = Column(Text, nullable=False)
    context_prefix = Column(String(255), nullable=False)
    query_prefix = Column(String(255), nullable=False) 
    answer_prefix = Column(String(255), nullable=False)
    
    # Metadata
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Ensure name+provider combination is unique
    __table_args__ = (
        UniqueConstraint('name', 'provider', name='uq_prompt_template_name_provider'),
    )
    
    def __init__(
        self,
        id: str,
        name: str,
        provider: str,
        system_prompt: str,
        context_prefix: str,
        query_prefix: str,
        answer_prefix: str,
        description: Optional[str] = None,
        is_default: bool = False
    ) -> None:
        """Initialize a new prompt template.
        
        Args:
            id: Unique identifier
            name: Template name
            provider: LLM provider (watsonx, openai, etc)
            system_prompt: System prompt for the LLM
            context_prefix: Prefix for context section
            query_prefix: Prefix for query section
            answer_prefix: Prefix for answer section
            description: Optional template description
            is_default: Whether this is the default template for the provider
        """
        self.id = id
        self.name = name
        self.provider = provider
        self.system_prompt = system_prompt
        self.context_prefix = context_prefix
        self.query_prefix = query_prefix
        self.answer_prefix = answer_prefix
        self.description = description
        self.is_default = is_default
    
    def to_dict(self) -> dict:
        """Convert prompt template to dictionary representation.
        
        Returns:
            Dictionary containing template data
        """
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "context_prefix": self.context_prefix,
            "query_prefix": self.query_prefix,
            "answer_prefix": self.answer_prefix,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_example_template(cls, provider: str) -> Optional[Dict[str, str]]:
        """Get example template for a specific provider.
        
        Args:
            provider: LLM provider name
            
        Returns:
            Example template dictionary if found, None otherwise
        """
        return cls.EXAMPLE_TEMPLATES.get(provider)
