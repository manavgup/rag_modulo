"""Base provider interface for LLM interactions using established schemas."""

from abc import ABC, abstractmethod
from typing import Generator, List, Optional, Union, Dict, Any
from pathlib import Path
from pydantic import BaseModel

from core.logging_utils import setup_logging, get_logger
from core.custom_exceptions import LLMProviderError
from rag_solution.schemas.model_parameters_schema import ModelParametersInput
from rag_solution.schemas.prompt_template_schema import BasePromptTemplate, PromptTemplateInput
from vectordbs.data_types import EmbeddingsList

# Setup logging
setup_logging(Path("logs"))
logger = get_logger("llm.providers")

class ProviderConfig(BaseModel):
    """Provider-specific configuration not covered by model parameters."""
    concurrency_limit: int = 10
    timeout: int = 30
    batch_size: int = 10
    stream: bool = False

class LLMProvider(ABC):
    """Abstract base class for language model providers."""

    def __init__(self) -> None:
        """Initialize provider with logging."""
        self.logger = get_logger(f"llm.providers.{self.__class__.__name__}")
        self.logger.info(f"Initializing {self.__class__.__name__}")
        self.client = None
        self.initialize_client()
    
    @abstractmethod
    def initialize_client(self) -> None:
        """Initialize the provider client. Must be implemented by subclasses."""
        pass

    def _ensure_client(self) -> None:
        """Ensure client is initialized."""
        if self.client is None:
            self.logger.warning("Client not initialized, attempting to initialize")
            self.initialize_client()
            if self.client is None:
                raise LLMProviderError("Failed to initialize client")

    def format_prompt(self, template: BasePromptTemplate, variables: Dict[str, Any]) -> str:
        """Format prompt template with variables.

        Args:
            template: The prompt template to format
            variables: The variables to substitute in the template

        Returns:
            str: The formatted prompt string

        Raises:
            LLMProviderError: If template formatting fails
        """
        try:
            # Build prompt parts
            formatted_parts: List[str] = []

            # Add system prompt
            if template.system_prompt:
                formatted_parts.append(template.system_prompt)

            # Add context if present
            if template.context_prefix and 'context' in variables:
                formatted_parts.append(f"{template.context_prefix}{variables['context']}")

            # Add query/question if present
            if template.query_prefix and 'question' in variables:
                formatted_parts.append(f"{template.query_prefix}{variables['question']}")

            # Add output prefix with specific template handling
            if template.output_prefix:
                if 'num_questions' in variables:
                    formatted_parts.append(f"{template.output_prefix}Generate {variables['num_questions']} questions.")
                else:
                    formatted_parts.append(template.output_prefix)

            return "\n\n".join(part.strip() for part in formatted_parts if part)

        except Exception as e:
            raise LLMProviderError(f"Failed to format prompt template: {str(e)}")

    def _prepare_prompts(
        self,
        prompt: Union[str, List[str]],
        template: Optional[BasePromptTemplate] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Union[str, List[str]]:
        """Prepare prompts using template if provided.

        Args:
            prompt: The input prompt or list of prompts
            template: Optional template to format the prompt
            variables: Optional variables to substitute in the template

        Returns:
            The prepared prompt or list of prompts

        Raises:
            LLMProviderError: If prompt preparation fails
        """
        if template is None:
            return prompt

        if isinstance(prompt, str):
            vars_dict = variables or {"input": prompt}
            return self.format_prompt(template, vars_dict)

        if isinstance(prompt, list):
            vars_list = variables or [{"input": p} for p in prompt]
            return [
                self.format_prompt(template, vars)
                for vars in vars_list
            ]

        raise LLMProviderError(f"Unsupported prompt type: {type(prompt)}")

    @abstractmethod
    def generate_text(
        self,
        prompt: Union[str, List[str]],
        model_parameters: ModelParametersInput,
        template: Optional[BasePromptTemplate] = None,
        provider_config: Optional[ProviderConfig] = None
    ) -> Union[str, List[str]]:
        """Generate text using the model.

        Args:
            prompt (Union[str, List[str]]): Input text prompt or list of prompts.
            model_parameters (ModelParametersInput): Generation parameters from model config.
            template (Optional[PromptTemplateInput]): Optional prompt template.
            provider_config (Optional[ProviderConfig]): Optional provider-specific settings.

        Returns:
            Union[str, List[str]]: Generated text response or list of responses.
        """
        pass

    @abstractmethod
    def generate_text_stream(
        self,
        prompt: str,
        model_parameters: ModelParametersInput,
        template: Optional[BasePromptTemplate] = None,
        provider_config: Optional[ProviderConfig] = None
    ) -> Generator[str, None, None]:
        """Generate text in streaming mode.

        Args:
            prompt (str): Input text prompt.
            model_parameters (ModelParametersInput): Generation parameters from model config.
            template (Optional[PromptTemplateInput]): Optional prompt template.
            provider_config (Optional[ProviderConfig]): Optional provider-specific settings.

        Yields:
            Generator[str, None, None]: Generated text chunks.
        """
        pass

    @abstractmethod
    def get_embeddings(
        self,
        texts: Union[str, List[str]],
        provider_config: Optional[ProviderConfig] = None
    ) -> EmbeddingsList:
        """Generate embeddings for texts.

        Args:
            texts (Union[str, List[str]]): Text or list of texts to embed.
            provider_config (Optional[ProviderConfig]): Optional provider-specific settings.

        Returns:
            EmbeddingsList: List of embedding vectors.
        """
        pass

    def close(self) -> None:
        """Clean up provider resources."""
        pass