# Token Tracking Implementation Plan
## RAG Modulo - Issue #229 Extension

**Document Version:** 1.0
**Created:** 2024-12-19
**Author:** Claude Code Assistant
**Related Issue:** [GitHub Issue #229](https://github.com/manavgup/rag_modulo/issues/229)

---

## Executive Summary

This document outlines a comprehensive token tracking implementation for the RAG Modulo conversation system. Instead of predicting token usage, we will track **actual token consumption** from LLM API responses to provide accurate usage monitoring and proactive limit warnings.

### Key Benefits
- ✅ **100% Accurate** - Uses real token counts from LLM APIs
- ✅ **No Token Estimation** - Eliminates complex tokenizer management
- ✅ **Real-time Warnings** - Alerts users when approaching context limits
- ✅ **Provider Agnostic** - Works with OpenAI, Anthropic, IBM WatsonX, etc.
- ✅ **Cost Tracking** - Monitor actual API costs and usage patterns
- ✅ **Simple Implementation** - Leverages existing API response data

---

## Architecture Overview

### Core Components

1. **LLMUsage Data Structure** - Standardized token usage tracking
2. **Enhanced LLM Providers** - Return usage data with responses
3. **Token Warning System** - Real-time limit notifications
4. **Service Integration** - Search, Conversation, and CoT services
5. **Database Tracking** - Optional persistent usage analytics

### Data Flow
```
LLM API Call → Usage Extraction → Service Processing → Warning Check → Response + Metadata
```

---

## Implementation Details

### 1. Core Data Structures

#### 1.1 LLMUsage Data Class
**File:** `rag_solution/schemas/llm_usage_schema.py` *(NEW)*

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ServiceType(str, Enum):
    """Type of service that used LLM tokens."""
    SEARCH = "search"
    CONVERSATION = "conversation"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    QUESTION_GENERATION = "question_generation"


class TokenWarningType(str, Enum):
    """Type of token warning."""
    APPROACHING_LIMIT = "approaching_limit"
    CONTEXT_TRUNCATED = "context_truncated"
    AT_LIMIT = "at_limit"
    CONVERSATION_TOO_LONG = "conversation_too_long"


@dataclass
class LLMUsage:
    """Actual token usage from LLM API response."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model_name: str
    service_type: ServiceType
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class TokenWarning(BaseModel):
    """Warning about token usage approaching limits."""
    warning_type: TokenWarningType
    current_tokens: int
    limit_tokens: int
    percentage_used: float = Field(..., ge=0, le=100)
    message: str
    severity: str = Field(..., regex="^(info|warning|critical)$")
    suggested_action: Optional[str] = None


class TokenUsageStats(BaseModel):
    """Aggregated token usage statistics."""
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_calls: int = 0
    average_tokens_per_call: float = 0
    by_service: dict[ServiceType, int] = Field(default_factory=dict)
    by_model: dict[str, int] = Field(default_factory=dict)
```

### 2. Enhanced LLM Provider Base Class

#### 2.1 Update Base Provider
**File:** `rag_solution/generation/providers/base.py` *(MODIFIED)*

```python
from abc import ABC, abstractmethod
from collections.abc import Generator, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple

# ... existing imports ...
from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType


class LLMBase(ABC):
    """Base class for language model integrations with token tracking."""

    def __init__(
        self,
        llm_provider_service: LLMProviderService,
        llm_parameters_service: LLMParametersService,
        prompt_template_service: PromptTemplateService,
        llm_model_service: LLMModelService,
    ) -> None:
        """Initialize provider with required services."""
        # ... existing initialization ...

        # Token tracking
        self._usage_history: List[LLMUsage] = []
        self._max_history_size = 100  # Keep last 100 calls

    @abstractmethod
    async def generate_text_with_usage(
        self,
        prompt: str,
        service_type: ServiceType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, LLMUsage]:
        """Generate text and return response with actual token usage.

        Args:
            prompt: Input text prompt
            service_type: Type of service making the request
            user_id: Optional user identifier
            session_id: Optional session identifier
            **kwargs: Additional model parameters

        Returns:
            Tuple of (generated_text, usage_data)
        """
        pass

    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Legacy method for backward compatibility."""
        text, _ = await self.generate_text_with_usage(
            prompt, ServiceType.SEARCH, **kwargs
        )
        return text

    def track_usage(self, usage: LLMUsage) -> None:
        """Track token usage in provider history."""
        self._usage_history.append(usage)

        # Maintain history size limit
        if len(self._usage_history) > self._max_history_size:
            self._usage_history = self._usage_history[-self._max_history_size:]

    def get_recent_usage(self, limit: int = 10) -> List[LLMUsage]:
        """Get recent token usage history."""
        return self._usage_history[-limit:]

    def get_total_usage(self, since: Optional[datetime] = None) -> TokenUsageStats:
        """Get cumulative usage statistics."""
        relevant_usage = self._usage_history
        if since:
            relevant_usage = [u for u in self._usage_history if u.timestamp >= since]

        if not relevant_usage:
            return TokenUsageStats()

        total_prompt = sum(u.prompt_tokens for u in relevant_usage)
        total_completion = sum(u.completion_tokens for u in relevant_usage)
        total_calls = len(relevant_usage)

        # Group by service type
        by_service = {}
        for usage in relevant_usage:
            by_service[usage.service_type] = by_service.get(usage.service_type, 0) + usage.total_tokens

        # Group by model
        by_model = {}
        for usage in relevant_usage:
            by_model[usage.model_name] = by_model.get(usage.model_name, 0) + usage.total_tokens

        return TokenUsageStats(
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_tokens=total_prompt + total_completion,
            total_calls=total_calls,
            average_tokens_per_call=round((total_prompt + total_completion) / total_calls, 1),
            by_service=by_service,
            by_model=by_model
        )
```

### 3. Provider-Specific Implementations

#### 3.1 OpenAI Provider
**File:** `rag_solution/generation/providers/openai.py` *(MODIFIED)*

```python
# Add to imports
from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType

class OpenAIProvider(LLMBase):
    # ... existing code ...

    async def generate_text_with_usage(
        self,
        prompt: str,
        service_type: ServiceType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, LLMUsage]:
        """Generate text with OpenAI and track token usage."""

        try:
            # Get parameters and prepare request
            params = self._get_parameters()

            response = await self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=params.max_new_tokens if params else 150,
                temperature=params.temperature if params else 0.7,
                **kwargs
            )

            # Extract actual usage from OpenAI response
            api_usage = response.usage
            usage = LLMUsage(
                prompt_tokens=api_usage.prompt_tokens,
                completion_tokens=api_usage.completion_tokens,
                total_tokens=api_usage.total_tokens,
                model_name=self.model_id,
                service_type=service_type,
                timestamp=datetime.utcnow(),
                user_id=user_id,
                session_id=session_id
            )

            # Track usage in provider history
            self.track_usage(usage)

            generated_text = response.choices[0].message.content
            return generated_text, usage

        except Exception as e:
            self.logger.error(f"OpenAI generation error: {e}")
            raise LLMProviderError(f"OpenAI API error: {e}") from e

    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Legacy method for backward compatibility."""
        text, _ = await self.generate_text_with_usage(
            prompt, ServiceType.SEARCH, **kwargs
        )
        return text
```

#### 3.2 Anthropic Provider
**File:** `rag_solution/generation/providers/anthropic.py` *(MODIFIED)*

```python
# Add to imports
from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType

class AnthropicProvider(LLMBase):
    # ... existing code ...

    async def generate_text_with_usage(
        self,
        prompt: str,
        service_type: ServiceType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, LLMUsage]:
        """Generate text with Anthropic and track token usage."""

        try:
            # Get parameters
            params = self._get_parameters()

            response = await self.client.messages.create(
                model=self.model_id,
                max_tokens=params.max_new_tokens if params else 150,
                temperature=params.temperature if params else 0.7,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )

            # Extract actual usage from Anthropic response
            usage = LLMUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                model_name=self.model_id,
                service_type=service_type,
                timestamp=datetime.utcnow(),
                user_id=user_id,
                session_id=session_id
            )

            # Track usage
            self.track_usage(usage)

            generated_text = response.content[0].text
            return generated_text, usage

        except Exception as e:
            self.logger.error(f"Anthropic generation error: {e}")
            raise LLMProviderError(f"Anthropic API error: {e}") from e
```

#### 3.3 IBM WatsonX Provider
**File:** `rag_solution/generation/providers/watsonx.py` *(MODIFIED)*

```python
# Add to imports
from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType

class WatsonXProvider(LLMBase):
    # ... existing code ...

    async def generate_text_with_usage(
        self,
        prompt: str,
        service_type: ServiceType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, LLMUsage]:
        """Generate text with IBM WatsonX and track token usage."""

        try:
            # Get parameters
            params = self._get_parameters()

            # Prepare generation parameters
            generation_params = {
                "max_new_tokens": params.max_new_tokens if params else 150,
                "temperature": params.temperature if params else 0.7,
                **kwargs
            }

            response = await self.client.generate(
                prompt=prompt,
                model_id=self.model_id,
                parameters=generation_params
            )

            # Extract usage from IBM response
            result = response.results[0]
            usage = LLMUsage(
                prompt_tokens=result.input_token_count,
                completion_tokens=result.generated_token_count,
                total_tokens=result.input_token_count + result.generated_token_count,
                model_name=self.model_id,
                service_type=service_type,
                timestamp=datetime.utcnow(),
                user_id=user_id,
                session_id=session_id
            )

            # Track usage
            self.track_usage(usage)

            generated_text = result.generated_text
            return generated_text, usage

        except Exception as e:
            self.logger.error(f"WatsonX generation error: {e}")
            raise LLMProviderError(f"WatsonX API error: {e}") from e
```

### 4. Token Warning Service

#### 4.1 Create Token Warning Service
**File:** `rag_solution/services/token_warning_service.py` *(NEW)*

```python
"""Service for managing token usage warnings and limits."""

from typing import Optional

from rag_solution.schemas.llm_usage_schema import LLMUsage, TokenWarning, TokenWarningType
from rag_solution.services.llm_model_service import LLMModelService


class TokenWarningService:
    """Service for checking token limits and generating warnings."""

    def __init__(self, llm_model_service: LLMModelService):
        self.llm_model_service = llm_model_service

    async def check_usage_warning(
        self,
        current_usage: LLMUsage,
        context_tokens: Optional[int] = None
    ) -> Optional[TokenWarning]:
        """Check if current usage warrants a warning."""

        # Get model configuration
        model = await self.llm_model_service.get_model_by_name(current_usage.model_name)
        if not model:
            return None

        context_limit = getattr(model, 'context_window', 4096)  # Default fallback

        # Determine tokens to check against limit
        check_tokens = context_tokens or current_usage.prompt_tokens
        percentage = (check_tokens / context_limit) * 100

        # Generate appropriate warning
        if percentage >= 95:
            return TokenWarning(
                warning_type=TokenWarningType.AT_LIMIT,
                current_tokens=check_tokens,
                limit_tokens=context_limit,
                percentage_used=percentage,
                message=f"Context window is {percentage:.0f}% full. Consider starting a new conversation.",
                severity="critical",
                suggested_action="start_new_session"
            )
        elif percentage >= 85:
            return TokenWarning(
                warning_type=TokenWarningType.APPROACHING_LIMIT,
                current_tokens=check_tokens,
                limit_tokens=context_limit,
                percentage_used=percentage,
                message=f"Context window is {percentage:.0f}% full. Approaching limit.",
                severity="warning",
                suggested_action="consider_new_session"
            )
        elif percentage >= 70:
            return TokenWarning(
                warning_type=TokenWarningType.APPROACHING_LIMIT,
                current_tokens=check_tokens,
                limit_tokens=context_limit,
                percentage_used=percentage,
                message=f"Context window is {percentage:.0f}% full.",
                severity="info"
            )

        return None

    async def check_conversation_warning(
        self,
        session_usage_history: list[LLMUsage],
        model_name: str
    ) -> Optional[TokenWarning]:
        """Check if conversation length warrants a warning."""

        if not session_usage_history:
            return None

        # Calculate cumulative prompt tokens for recent messages
        recent_prompt_tokens = sum(u.prompt_tokens for u in session_usage_history[-5:])

        # Get model limits
        model = await self.llm_model_service.get_model_by_name(model_name)
        if not model:
            return None

        context_limit = getattr(model, 'context_window', 4096)

        # Check if conversation is getting too long
        if recent_prompt_tokens > context_limit * 0.8:
            return TokenWarning(
                warning_type=TokenWarningType.CONVERSATION_TOO_LONG,
                current_tokens=recent_prompt_tokens,
                limit_tokens=context_limit,
                percentage_used=(recent_prompt_tokens / context_limit) * 100,
                message="Conversation context is getting large. Older messages may be excluded from context.",
                severity="warning",
                suggested_action="start_new_session"
            )

        return None
```

### 5. Service Integration Updates

#### 5.1 Search Service Updates
**File:** `rag_solution/services/search_service.py` *(MODIFIED)*

```python
# Add to imports
from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType
from rag_solution.services.token_warning_service import TokenWarningService

class SearchService:
    """Service for handling search operations through the RAG pipeline."""

    def __init__(self, db: Session, settings: Settings):
        # ... existing initialization ...
        self._token_warning_service: Optional[TokenWarningService] = None

    @property
    def token_warning_service(self) -> TokenWarningService:
        """Get token warning service instance."""
        if self._token_warning_service is None:
            from rag_solution.services.llm_model_service import LLMModelService
            llm_model_service = LLMModelService(self.db)
            self._token_warning_service = TokenWarningService(llm_model_service)
        return self._token_warning_service

    async def search(self, search_input: SearchInput) -> SearchOutput:
        """Process a search query through the RAG pipeline with token tracking."""
        start_time = time.time()
        logger.info("Starting search operation with token tracking")

        # Validate inputs
        self._validate_search_input(search_input)
        self._validate_collection_access(search_input.collection_id, search_input.user_id)

        # Check if Chain of Thought should be used
        if self._should_use_chain_of_thought(search_input):
            logger.info("Using Chain of Thought for enhanced reasoning")
            try:
                # Use CoT with token tracking
                return await self._search_with_chain_of_thought(search_input, start_time)
            except Exception as e:
                logger.warning(f"Chain of Thought failed: {e}, falling back to regular search")

        # Regular search with token tracking
        return await self._search_regular_with_tokens(search_input, start_time)

    async def _search_regular_with_tokens(self, search_input: SearchInput, start_time: float) -> SearchOutput:
        """Perform regular search with token usage tracking."""

        # Get pipeline and perform search
        pipeline_id = self._resolve_user_default_pipeline(search_input.user_id)
        pipeline = self.pipeline_service.get_pipeline(pipeline_id)

        if not pipeline:
            raise NotFoundError(f"Pipeline {pipeline_id} not found")

        # Retrieve documents
        search_results = await self._retrieve_documents(search_input, pipeline)

        # Get LLM provider for generation with token tracking
        llm_provider = self._get_llm_provider(search_input.user_id)

        # Build context and generate response with usage tracking
        context = self._build_context_from_documents(search_results, search_input.question)
        enhanced_prompt = self._build_generation_prompt(search_input.question, context)

        # Generate response with token tracking
        response_text, usage = await llm_provider.generate_text_with_usage(
            prompt=enhanced_prompt,
            service_type=ServiceType.SEARCH,
            user_id=str(search_input.user_id),
            session_id=search_input.config_metadata.get("session_id") if search_input.config_metadata else None
        )

        # Check for token warnings
        token_warning = await self.token_warning_service.check_usage_warning(usage)

        # Calculate execution time
        execution_time = time.time() - start_time

        # Prepare metadata with token information
        metadata = {
            "pipeline_id": str(pipeline_id),
            "search_method": "regular",
            "token_usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "model_name": usage.model_name
            }
        }

        if token_warning:
            metadata["token_warning"] = {
                "type": token_warning.warning_type,
                "message": token_warning.message,
                "percentage_used": token_warning.percentage_used,
                "severity": token_warning.severity,
                "suggested_action": token_warning.suggested_action
            }

        return SearchOutput(
            answer=response_text,
            documents=search_results,
            query_results=[],  # Populated by retrieve documents
            execution_time=execution_time,
            metadata=metadata
        )

    async def _search_with_chain_of_thought(self, search_input: SearchInput, start_time: float) -> SearchOutput:
        """Perform search with Chain of Thought and token tracking."""

        # Get pipeline for document retrieval
        pipeline_id = self._resolve_user_default_pipeline(search_input.user_id)
        pipeline = self.pipeline_service.get_pipeline(pipeline_id)

        if not pipeline:
            raise NotFoundError(f"Pipeline {pipeline_id} not found")

        # Get LLM provider
        llm_provider = self._get_llm_provider(search_input.user_id)

        # Create Chain of Thought service with token tracking
        if not self.chain_of_thought_service:
            from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
            self.chain_of_thought_service = ChainOfThoughtService(
                self.settings,
                llm_provider,
                self,  # Pass search service
                self.db
            )

        # Retrieve documents for context
        search_results = await self._retrieve_documents(search_input, pipeline)
        context = self._build_context_from_documents(search_results, search_input.question)

        # Create CoT input with token awareness
        from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput
        cot_input = ChainOfThoughtInput(
            question=search_input.question,
            context=context,
            config_metadata=search_input.config_metadata or {},
            user_id=search_input.user_id,
            collection_id=search_input.collection_id
        )

        # Process with Chain of Thought (includes token tracking)
        cot_result = await self.chain_of_thought_service.process_chain_of_thought_with_tokens(cot_input)

        execution_time = time.time() - start_time

        # Aggregate token usage from CoT steps
        total_usage = cot_result.aggregate_token_usage()
        token_warning = await self.token_warning_service.check_usage_warning(total_usage)

        # Prepare metadata
        metadata = {
            "pipeline_id": str(pipeline_id),
            "search_method": "chain_of_thought",
            "cot_steps": len(cot_result.reasoning_steps),
            "token_usage": {
                "prompt_tokens": total_usage.prompt_tokens,
                "completion_tokens": total_usage.completion_tokens,
                "total_tokens": total_usage.total_tokens,
                "model_name": total_usage.model_name
            },
            "cot_token_breakdown": [
                {
                    "step": step.step_type,
                    "prompt_tokens": step.token_usage.prompt_tokens if step.token_usage else 0,
                    "completion_tokens": step.token_usage.completion_tokens if step.token_usage else 0,
                    "total_tokens": step.token_usage.total_tokens if step.token_usage else 0
                }
                for step in cot_result.reasoning_steps
            ]
        }

        if token_warning:
            metadata["token_warning"] = {
                "type": token_warning.warning_type,
                "message": token_warning.message,
                "percentage_used": token_warning.percentage_used,
                "severity": token_warning.severity,
                "suggested_action": token_warning.suggested_action
            }

        return SearchOutput(
            answer=cot_result.final_answer,
            documents=search_results,
            query_results=[],
            execution_time=execution_time,
            metadata=metadata
        )
```

#### 5.2 Chain of Thought Service Updates
**File:** `rag_solution/services/chain_of_thought_service.py` *(MODIFIED)*

```python
# Add to imports
from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType
from rag_solution.services.token_warning_service import TokenWarningService

class ChainOfThoughtService:
    """Service for Chain of Thought reasoning in RAG search with token tracking."""

    def __init__(self, settings: Settings, llm_service: LLMBase, search_service: SearchService, db: Session) -> None:
        """Initialize Chain of Thought service."""
        # ... existing initialization ...
        self._token_warning_service: Optional[TokenWarningService] = None

    @property
    def token_warning_service(self) -> TokenWarningService:
        """Get token warning service instance."""
        if self._token_warning_service is None:
            from rag_solution.services.llm_model_service import LLMModelService
            llm_model_service = LLMModelService(self.db)
            self._token_warning_service = TokenWarningService(llm_model_service)
        return self._token_warning_service

    async def process_chain_of_thought_with_tokens(self, cot_input: ChainOfThoughtInput) -> ChainOfThoughtOutput:
        """Process Chain of Thought with comprehensive token tracking."""
        logger.info("Processing Chain of Thought with token tracking")

        try:
            # Step 1: Question Classification with token tracking
            classification_usage = await self._classify_question_with_tokens(cot_input)

            # Step 2: Question Decomposition (if needed) with token tracking
            decomposition_usage = None
            if classification_usage and self._requires_decomposition(classification_usage):
                decomposition_usage = await self._decompose_question_with_tokens(cot_input)

            # Step 3: Answer Generation with token tracking
            generation_usage = await self._generate_answer_with_tokens(cot_input, classification_usage, decomposition_usage)

            # Step 4: Final Synthesis with token tracking
            synthesis_usage = await self._synthesize_final_answer_with_tokens(
                cot_input, classification_usage, decomposition_usage, generation_usage
            )

            # Aggregate all token usage
            all_steps = [usage for usage in [classification_usage, decomposition_usage, generation_usage, synthesis_usage] if usage]
            total_prompt_tokens = sum(step.prompt_tokens for step in all_steps)
            total_completion_tokens = sum(step.completion_tokens for step in all_steps)

            aggregated_usage = LLMUsage(
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens,
                total_tokens=total_prompt_tokens + total_completion_tokens,
                model_name=self.llm_service.model_id,
                service_type=ServiceType.CHAIN_OF_THOUGHT,
                timestamp=datetime.utcnow(),
                user_id=str(cot_input.user_id),
                session_id=cot_input.config_metadata.get("session_id")
            )

            # Check for warnings
            token_warning = await self.token_warning_service.check_usage_warning(aggregated_usage)

            # Build reasoning steps with token information
            reasoning_steps = []

            if classification_usage:
                reasoning_steps.append(ReasoningStep(
                    step_type="classification",
                    description="Classified question complexity and requirements",
                    reasoning="Analyzed question to determine processing approach",
                    conclusion="Question classification completed",
                    token_usage=classification_usage
                ))

            if decomposition_usage:
                reasoning_steps.append(ReasoningStep(
                    step_type="decomposition",
                    description="Decomposed complex question into sub-questions",
                    reasoning="Broke down question for systematic analysis",
                    conclusion="Question decomposition completed",
                    token_usage=decomposition_usage
                ))

            if generation_usage:
                reasoning_steps.append(ReasoningStep(
                    step_type="generation",
                    description="Generated comprehensive answer",
                    reasoning="Processed question with available context",
                    conclusion="Answer generation completed",
                    token_usage=generation_usage
                ))

            if synthesis_usage:
                reasoning_steps.append(ReasoningStep(
                    step_type="synthesis",
                    description="Synthesized final coherent response",
                    reasoning="Combined all analysis into final answer",
                    conclusion="Response synthesis completed",
                    token_usage=synthesis_usage
                ))

            return ChainOfThoughtOutput(
                final_answer=synthesis_usage.generated_text if synthesis_usage else "No answer generated",
                reasoning_steps=reasoning_steps,
                confidence_score=0.85,  # Default confidence
                metadata={
                    "total_steps": len(reasoning_steps),
                    "token_usage": aggregated_usage.__dict__,
                    "token_warning": token_warning.__dict__ if token_warning else None,
                    "processing_time": time.time()
                },
                aggregate_token_usage=lambda: aggregated_usage  # Method to get aggregated usage
            )

        except Exception as e:
            logger.error(f"Chain of Thought processing error: {e}")
            raise

    async def _classify_question_with_tokens(self, cot_input: ChainOfThoughtInput) -> Optional[LLMUsage]:
        """Classify question complexity with token tracking."""
        try:
            classification_prompt = self._build_classification_prompt(cot_input.question)

            response_text, usage = await self.llm_service.generate_text_with_usage(
                prompt=classification_prompt,
                service_type=ServiceType.CHAIN_OF_THOUGHT,
                user_id=str(cot_input.user_id),
                session_id=cot_input.config_metadata.get("session_id")
            )

            # Store the generated classification for use in other steps
            usage.generated_text = response_text
            return usage

        except Exception as e:
            logger.error(f"Question classification error: {e}")
            return None

    async def _decompose_question_with_tokens(self, cot_input: ChainOfThoughtInput) -> Optional[LLMUsage]:
        """Decompose complex question with token tracking."""
        try:
            decomposition_prompt = self._build_decomposition_prompt(cot_input.question, cot_input.context)

            response_text, usage = await self.llm_service.generate_text_with_usage(
                prompt=decomposition_prompt,
                service_type=ServiceType.CHAIN_OF_THOUGHT,
                user_id=str(cot_input.user_id),
                session_id=cot_input.config_metadata.get("session_id")
            )

            usage.generated_text = response_text
            return usage

        except Exception as e:
            logger.error(f"Question decomposition error: {e}")
            return None

    async def _generate_answer_with_tokens(
        self,
        cot_input: ChainOfThoughtInput,
        classification_usage: Optional[LLMUsage],
        decomposition_usage: Optional[LLMUsage]
    ) -> Optional[LLMUsage]:
        """Generate comprehensive answer with token tracking."""
        try:
            # Build enhanced prompt using previous step results
            enhanced_context = cot_input.context
            if classification_usage and hasattr(classification_usage, 'generated_text'):
                enhanced_context += f"\n\nQuestion Analysis: {classification_usage.generated_text}"
            if decomposition_usage and hasattr(decomposition_usage, 'generated_text'):
                enhanced_context += f"\n\nQuestion Breakdown: {decomposition_usage.generated_text}"

            generation_prompt = self._build_generation_prompt(cot_input.question, enhanced_context)

            response_text, usage = await self.llm_service.generate_text_with_usage(
                prompt=generation_prompt,
                service_type=ServiceType.CHAIN_OF_THOUGHT,
                user_id=str(cot_input.user_id),
                session_id=cot_input.config_metadata.get("session_id")
            )

            usage.generated_text = response_text
            return usage

        except Exception as e:
            logger.error(f"Answer generation error: {e}")
            return None

    async def _synthesize_final_answer_with_tokens(
        self,
        cot_input: ChainOfThoughtInput,
        classification_usage: Optional[LLMUsage],
        decomposition_usage: Optional[LLMUsage],
        generation_usage: Optional[LLMUsage]
    ) -> Optional[LLMUsage]:
        """Synthesize final coherent answer with token tracking."""
        try:
            # Build synthesis prompt using all previous results
            synthesis_context = ""
            if classification_usage and hasattr(classification_usage, 'generated_text'):
                synthesis_context += f"Analysis: {classification_usage.generated_text}\n\n"
            if decomposition_usage and hasattr(decomposition_usage, 'generated_text'):
                synthesis_context += f"Breakdown: {decomposition_usage.generated_text}\n\n"
            if generation_usage and hasattr(generation_usage, 'generated_text'):
                synthesis_context += f"Generated Answer: {generation_usage.generated_text}\n\n"

            synthesis_prompt = self._build_synthesis_prompt(
                cot_input.question,
                cot_input.context,
                synthesis_context
            )

            response_text, usage = await self.llm_service.generate_text_with_usage(
                prompt=synthesis_prompt,
                service_type=ServiceType.CHAIN_OF_THOUGHT,
                user_id=str(cot_input.user_id),
                session_id=cot_input.config_metadata.get("session_id")
            )

            usage.generated_text = response_text
            return usage

        except Exception as e:
            logger.error(f"Answer synthesis error: {e}")
            return None

    def _build_classification_prompt(self, question: str) -> str:
        """Build prompt for question classification."""
        return f"""Analyze this question and classify its complexity:

Question: {question}

Classify as:
1. Simple - Direct factual question requiring single lookup
2. Complex - Multi-part question requiring analysis and synthesis
3. Analytical - Requires reasoning and interpretation

Provide classification and brief reasoning (max 100 words)."""

    def _build_decomposition_prompt(self, question: str, context: str) -> str:
        """Build prompt for question decomposition."""
        return f"""Break down this complex question into manageable sub-questions:

Question: {question}
Context: {context}

Decompose into 2-4 specific sub-questions that can be answered individually.
List each sub-question clearly (max 150 words total)."""

    def _build_generation_prompt(self, question: str, context: str) -> str:
        """Build prompt for answer generation."""
        return f"""Answer this question comprehensively using the provided context:

Question: {question}
Context: {context}

Provide a detailed, accurate answer based on the context. If the context doesn't contain sufficient information, state what's missing."""

    def _build_synthesis_prompt(self, question: str, original_context: str, reasoning_context: str) -> str:
        """Build prompt for final synthesis."""
        return f"""Synthesize a final, coherent answer using all the analysis provided:

Original Question: {question}
Original Context: {original_context}
Analysis and Reasoning: {reasoning_context}

Provide a clear, comprehensive final answer that incorporates the reasoning and analysis."""

    def _requires_decomposition(self, classification_usage: LLMUsage) -> bool:
        """Determine if question requires decomposition based on classification."""
        if not hasattr(classification_usage, 'generated_text'):
            return False

        classification_text = classification_usage.generated_text.lower()
        return 'complex' in classification_text or 'analytical' in classification_text
```

#### 5.3 Conversation Service Updates
**File:** `rag_solution/services/conversation_service.py` *(MODIFIED)*

```python
# Add to imports
from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType, TokenUsageStats
from rag_solution.services.token_warning_service import TokenWarningService

class ConversationService:
    """Service for managing conversation sessions and messages with token tracking."""

    def __init__(self, db: Session, settings: Settings):
        """Initialize the conversation service."""
        # ... existing initialization ...
        self._token_warning_service: Optional[TokenWarningService] = None

    @property
    def token_warning_service(self) -> TokenWarningService:
        """Get token warning service instance."""
        if self._token_warning_service is None:
            from rag_solution.services.llm_model_service import LLMModelService
            llm_model_service = LLMModelService(self.db)
            self._token_warning_service = TokenWarningService(llm_model_service)
        return self._token_warning_service

    async def process_user_message(self, message_input: ConversationMessageInput) -> Tuple[ConversationMessageOutput, Optional[TokenWarning]]:
        """Process a user message and generate a response with token tracking."""
        # First get the session to get the user_id
        session = self.db.query(ConversationSession).filter(ConversationSession.id == message_input.session_id).first()
        if not session:
            raise ValueError("Session not found")

        # Add the user message to the session
        await self.add_message(message_input)

        # Get conversation context and message history
        messages = await self.get_messages(message_input.session_id, session.user_id)
        context = await self.build_context_from_messages(message_input.session_id, messages)

        # Enhance question with conversation context
        enhanced_question = await self.enhance_question_with_context(
            message_input.content,
            context.context_window,
            [msg.content for msg in messages[-5:]],  # Last 5 messages
        )

        # Create search input with conversation context
        search_input = SearchInput(
            question=enhanced_question,
            collection_id=session.collection_id,
            user_id=session.user_id,
            config_metadata={
                "conversation_context": context.context_window,
                "session_id": str(message_input.session_id),
                "message_history": [msg.content for msg in messages[-10:]],
                "conversation_entities": context.context_metadata.get("extracted_entities", []),
                "cot_enabled": True,
                "show_cot_steps": False,
                "conversation_aware": True,
            },
        )

        # Execute search with token tracking
        search_result = await self.search_service.search(search_input)

        # Extract token usage from search result
        token_usage_data = search_result.metadata.get("token_usage", {})
        token_warning_data = search_result.metadata.get("token_warning")

        # Check for conversation-level token warnings
        conversation_warning = None
        if token_usage_data:
            # Get recent usage for this session to check conversation limits
            recent_messages = messages[-10:]  # Check last 10 messages
            session_usage_history = self._extract_usage_from_messages(recent_messages)

            conversation_warning = await self.token_warning_service.check_conversation_warning(
                session_usage_history,
                token_usage_data.get("model_name", "unknown")
            )

        # Determine which warning to prioritize
        final_warning = None
        if token_warning_data:
            final_warning = TokenWarning(**token_warning_data)
        elif conversation_warning:
            final_warning = conversation_warning

        # Extract CoT information if it was used
        cot_used = search_result.metadata.get("search_method") == "chain_of_thought"
        cot_steps = search_result.metadata.get("cot_token_breakdown", [])

        # Convert DocumentMetadata objects to dictionaries for JSON serialization
        serialized_documents = self._serialize_documents(search_result.documents)

        # Create assistant response with comprehensive token metadata
        assistant_message_input = ConversationMessageInput(
            session_id=message_input.session_id,
            content=search_result.answer,
            role=MessageRole.ASSISTANT,
            message_type=MessageType.ANSWER,
            metadata=MessageMetadata(
                source_documents=[doc.get("document_id", "") for doc in serialized_documents]
                if serialized_documents
                else None,
                search_metadata={
                    "enhanced_question": enhanced_question,
                    "cot_steps": cot_steps,
                    "integration_seamless": True,
                    "conversation_ui_used": True,
                    "search_rag_used": True,
                    "cot_reasoning_used": cot_used,
                    "no_duplication": True,
                    "service_boundaries_respected": True,
                    "token_usage": token_usage_data,
                    "token_warning": token_warning_data,
                    "conversation_warning": conversation_warning.__dict__ if conversation_warning else None
                },
                cot_used=cot_used,
                conversation_aware=True,
                execution_time=search_result.execution_time,
                context_length=len(context.context_window) if context else None,
                token_count=token_usage_data.get("total_tokens") if token_usage_data else None,
            ),
        )

        assistant_message = await self.add_message(assistant_message_input)
        return assistant_message, final_warning

    def _extract_usage_from_messages(self, messages: List[ConversationMessageOutput]) -> List[LLMUsage]:
        """Extract token usage information from message metadata."""
        usage_history = []

        for msg in messages:
            if msg.metadata and msg.metadata.search_metadata:
                token_usage = msg.metadata.search_metadata.get("token_usage")
                if token_usage:
                    usage = LLMUsage(
                        prompt_tokens=token_usage.get("prompt_tokens", 0),
                        completion_tokens=token_usage.get("completion_tokens", 0),
                        total_tokens=token_usage.get("total_tokens", 0),
                        model_name=token_usage.get("model_name", "unknown"),
                        service_type=ServiceType.CONVERSATION,
                        timestamp=msg.created_at,
                        session_id=str(msg.session_id)
                    )
                    usage_history.append(usage)

        return usage_history

    async def get_session_token_statistics(self, session_id: UUID, user_id: UUID) -> TokenUsageStats:
        """Get comprehensive token usage statistics for a session."""
        messages = await self.get_messages(session_id, user_id)
        usage_history = self._extract_usage_from_messages(messages)

        if not usage_history:
            return TokenUsageStats()

        total_prompt = sum(u.prompt_tokens for u in usage_history)
        total_completion = sum(u.completion_tokens for u in usage_history)
        total_calls = len(usage_history)

        # Group by service type
        by_service = {}
        for usage in usage_history:
            service = usage.service_type
            by_service[service] = by_service.get(service, 0) + usage.total_tokens

        # Group by model
        by_model = {}
        for usage in usage_history:
            model = usage.model_name
            by_model[model] = by_model.get(model, 0) + usage.total_tokens

        return TokenUsageStats(
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_tokens=total_prompt + total_completion,
            total_calls=total_calls,
            average_tokens_per_call=round((total_prompt + total_completion) / total_calls, 1) if total_calls > 0 else 0,
            by_service=by_service,
            by_model=by_model
        )

    # ... rest of existing methods remain the same ...
```

### 6. Database Schema Updates

#### 6.1 Add Context Window to LLM Models
**File:** Database Migration *(NEW)*

```sql
-- Migration: Add token limits to llm_models table
-- File: alembic/versions/xxx_add_token_limits_to_llm_models.py

"""Add token limits to llm_models

Revision ID: add_token_limits
Revises: previous_revision
Create Date: 2024-12-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_token_limits'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns for token limits
    op.add_column('llm_models', sa.Column('context_window', sa.Integer(), nullable=False, server_default='4096'))
    op.add_column('llm_models', sa.Column('max_output_tokens', sa.Integer(), nullable=False, server_default='2048'))
    op.add_column('llm_models', sa.Column('tokenizer_model', sa.String(100), nullable=True))

    # Update existing models with known context windows
    connection = op.get_bind()

    # OpenAI models
    connection.execute(sa.text("""
        UPDATE llm_models
        SET context_window = 4096, max_output_tokens = 4096
        WHERE model_id LIKE 'gpt-3.5-turbo%' AND model_id NOT LIKE '%-16k%'
    """))

    connection.execute(sa.text("""
        UPDATE llm_models
        SET context_window = 16384, max_output_tokens = 4096
        WHERE model_id LIKE 'gpt-3.5-turbo-16k%'
    """))

    connection.execute(sa.text("""
        UPDATE llm_models
        SET context_window = 8192, max_output_tokens = 4096
        WHERE model_id LIKE 'gpt-4%' AND model_id NOT LIKE '%-turbo%'
    """))

    connection.execute(sa.text("""
        UPDATE llm_models
        SET context_window = 128000, max_output_tokens = 4096
        WHERE model_id LIKE 'gpt-4-turbo%'
    """))

    # Anthropic models
    connection.execute(sa.text("""
        UPDATE llm_models
        SET context_window = 200000, max_output_tokens = 4096
        WHERE model_id LIKE 'claude-3%'
    """))

    # IBM Granite models (conservative estimates)
    connection.execute(sa.text("""
        UPDATE llm_models
        SET context_window = 8192, max_output_tokens = 2048
        WHERE model_id LIKE 'granite%'
    """))


def downgrade():
    op.drop_column('llm_models', 'tokenizer_model')
    op.drop_column('llm_models', 'max_output_tokens')
    op.drop_column('llm_models', 'context_window')
```

#### 6.2 Optional Token Usage Tracking Table
**File:** Database Migration *(NEW - OPTIONAL)*

```sql
-- Migration: Create token_usage tracking table
-- File: alembic/versions/xxx_create_token_usage_table.py

"""Create token usage tracking table

Revision ID: create_token_usage_table
Revises: add_token_limits
Create Date: 2024-12-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers
revision = 'create_token_usage_table'
down_revision = 'add_token_limits'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'token_usage',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('session_id', UUID(as_uuid=True), sa.ForeignKey('conversation_sessions.id'), nullable=True),
        sa.Column('model_id', sa.String(255), nullable=False),
        sa.Column('service_type', sa.String(50), nullable=False),  # search, conversation, cot
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('completion_tokens', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Indexes for common queries
        sa.Index('idx_token_usage_user_date', 'user_id', 'created_at'),
        sa.Index('idx_token_usage_session', 'session_id'),
        sa.Index('idx_token_usage_service_type', 'service_type'),
    )


def downgrade():
    op.drop_table('token_usage')
```

### 7. API Router Updates

#### 7.1 Chat Router Updates
**File:** `rag_solution/router/chat_router.py` *(MODIFIED)*

```python
# Add to imports
from rag_solution.schemas.llm_usage_schema import TokenWarning

# Update the process_user_message endpoint
@router.post("/sessions/{session_id}/process", response_model=dict)
async def process_user_message(
    session_id: UUID,
    message_data: ConversationMessageInput,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> dict:
    """Process a user message and generate a response with token tracking."""
    try:
        # Ensure session_id matches
        message_data.session_id = session_id
        response, warning = await conversation_service.process_user_message(message_data)

        result = {
            "message": response.model_dump(),
            "status": "success"
        }

        # Include token warning if present
        if warning:
            result["token_warning"] = {
                "type": warning.warning_type,
                "message": warning.message,
                "percentage_used": warning.percentage_used,
                "severity": warning.severity,
                "current_tokens": warning.current_tokens,
                "limit_tokens": warning.limit_tokens,
                "suggested_action": warning.suggested_action
            }

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# Add new endpoint for token statistics
@router.get("/sessions/{session_id}/token-stats")
async def get_session_token_statistics(
    session_id: UUID,
    user_id: UUID = Query(..., description="User ID"),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> dict:
    """Get token usage statistics for a conversation session."""
    try:
        stats = await conversation_service.get_session_token_statistics(session_id, user_id)
        return {
            "session_id": str(session_id),
            "statistics": stats.model_dump()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
```

### 8. Schema Updates

#### 8.1 Update LLM Model Schema
**File:** `rag_solution/schemas/llm_model_schema.py` *(MODIFIED)*

```python
# Add to existing LLMModelInput
class LLMModelInput(BaseModel):
    # ... existing fields ...

    # New token-related fields
    context_window: int = Field(4096, ge=1024, le=200000, description="Model's context window in tokens")
    max_output_tokens: int = Field(2048, ge=128, le=100000, description="Maximum output tokens")
    tokenizer_model: Optional[str] = Field(None, description="Tokenizer model identifier")

# Add to existing LLMModelOutput
class LLMModelOutput(BaseModel):
    # ... existing fields ...

    # New token-related fields
    context_window: int
    max_output_tokens: int
    tokenizer_model: Optional[str]
```

#### 8.2 Update Chain of Thought Schema
**File:** `rag_solution/schemas/chain_of_thought_schema.py` *(MODIFIED)*

```python
# Add to imports
from rag_solution.schemas.llm_usage_schema import LLMUsage

# Update ReasoningStep
class ReasoningStep(BaseModel):
    # ... existing fields ...
    token_usage: Optional[LLMUsage] = Field(None, description="Token usage for this step")

# Update ChainOfThoughtOutput
class ChainOfThoughtOutput(BaseModel):
    # ... existing fields ...
    aggregate_token_usage: Optional[callable] = Field(None, description="Method to get aggregated token usage")

    def get_total_token_usage(self) -> LLMUsage:
        """Get aggregated token usage across all steps."""
        if self.aggregate_token_usage:
            return self.aggregate_token_usage()

        # Fallback: sum from reasoning steps
        total_prompt = sum(step.token_usage.prompt_tokens for step in self.reasoning_steps if step.token_usage)
        total_completion = sum(step.token_usage.completion_tokens for step in self.reasoning_steps if step.token_usage)

        return LLMUsage(
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            total_tokens=total_prompt + total_completion,
            model_name="aggregated",
            service_type=ServiceType.CHAIN_OF_THOUGHT,
            timestamp=datetime.utcnow()
        )
```

### 9. Testing Strategy

#### 9.1 Unit Tests
**File:** `tests/unit/test_token_tracking.py` *(NEW)*

```python
"""Unit tests for token tracking functionality."""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType, TokenWarning, TokenWarningType
from rag_solution.services.token_warning_service import TokenWarningService


class TestTokenWarningService:
    """Test token warning service functionality."""

    @pytest.fixture
    def mock_llm_model_service(self):
        """Create mock LLM model service."""
        mock_service = Mock()
        mock_model = Mock()
        mock_model.context_window = 4096
        mock_model.max_output_tokens = 2048
        mock_service.get_model_by_name = AsyncMock(return_value=mock_model)
        return mock_service

    @pytest.fixture
    def token_warning_service(self, mock_llm_model_service):
        """Create token warning service with mocked dependencies."""
        return TokenWarningService(mock_llm_model_service)

    @pytest.mark.asyncio
    async def test_no_warning_under_70_percent(self, token_warning_service):
        """Test no warning generated when under 70% usage."""
        usage = LLMUsage(
            prompt_tokens=2000,  # ~49% of 4096
            completion_tokens=500,
            total_tokens=2500,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow()
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is None

    @pytest.mark.asyncio
    async def test_info_warning_70_to_85_percent(self, token_warning_service):
        """Test info warning between 70-85% usage."""
        usage = LLMUsage(
            prompt_tokens=3200,  # ~78% of 4096
            completion_tokens=500,
            total_tokens=3700,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow()
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is not None
        assert warning.warning_type == TokenWarningType.APPROACHING_LIMIT
        assert warning.severity == "info"
        assert 70 <= warning.percentage_used < 85

    @pytest.mark.asyncio
    async def test_warning_85_to_95_percent(self, token_warning_service):
        """Test warning severity between 85-95% usage."""
        usage = LLMUsage(
            prompt_tokens=3700,  # ~90% of 4096
            completion_tokens=500,
            total_tokens=4200,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow()
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is not None
        assert warning.warning_type == TokenWarningType.APPROACHING_LIMIT
        assert warning.severity == "warning"
        assert 85 <= warning.percentage_used < 95

    @pytest.mark.asyncio
    async def test_critical_warning_over_95_percent(self, token_warning_service):
        """Test critical warning over 95% usage."""
        usage = LLMUsage(
            prompt_tokens=3900,  # ~95% of 4096
            completion_tokens=500,
            total_tokens=4400,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow()
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is not None
        assert warning.warning_type == TokenWarningType.AT_LIMIT
        assert warning.severity == "critical"
        assert warning.percentage_used >= 95
        assert "start_new_session" in warning.suggested_action


class TestLLMUsageTracking:
    """Test LLM usage data structure and calculations."""

    def test_llm_usage_creation(self):
        """Test LLMUsage object creation."""
        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.CONVERSATION,
            timestamp=datetime.utcnow(),
            user_id="user123",
            session_id="session456"
        )

        assert usage.prompt_tokens == 1000
        assert usage.completion_tokens == 500
        assert usage.total_tokens == 1500
        assert usage.model_name == "gpt-3.5-turbo"
        assert usage.service_type == ServiceType.CONVERSATION
        assert usage.user_id == "user123"
        assert usage.session_id == "session456"

    def test_token_usage_stats_aggregation(self):
        """Test token usage statistics aggregation."""
        from rag_solution.schemas.llm_usage_schema import TokenUsageStats

        stats = TokenUsageStats(
            total_prompt_tokens=5000,
            total_completion_tokens=2000,
            total_tokens=7000,
            total_calls=10,
            average_tokens_per_call=700.0,
            by_service={
                ServiceType.SEARCH: 3000,
                ServiceType.CONVERSATION: 4000
            },
            by_model={
                "gpt-3.5-turbo": 5000,
                "gpt-4": 2000
            }
        )

        assert stats.total_tokens == 7000
        assert stats.average_tokens_per_call == 700.0
        assert stats.by_service[ServiceType.SEARCH] == 3000
        assert stats.by_model["gpt-3.5-turbo"] == 5000
```

#### 9.2 Integration Tests
**File:** `tests/integration/test_token_integration.py` *(NEW)*

```python
"""Integration tests for token tracking across services."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.search_service import SearchService


class TestTokenTrackingIntegration:
    """Test token tracking integration across services."""

    @pytest.mark.asyncio
    async def test_search_service_token_tracking(self):
        """Test that search service properly tracks tokens."""
        # Mock dependencies
        mock_db = Mock()
        mock_settings = Mock()

        # Create search service
        search_service = SearchService(mock_db, mock_settings)

        # Mock LLM provider with token tracking
        mock_provider = Mock()
        mock_usage = LLMUsage(
            prompt_tokens=1200,
            completion_tokens=300,
            total_tokens=1500,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow()
        )

        mock_provider.generate_text_with_usage = AsyncMock(
            return_value=("This is a test response", mock_usage)
        )

        # Mock other dependencies
        with patch.object(search_service, '_get_llm_provider', return_value=mock_provider), \
             patch.object(search_service, '_validate_search_input'), \
             patch.object(search_service, '_validate_collection_access'), \
             patch.object(search_service, '_resolve_user_default_pipeline', return_value="pipeline_123"), \
             patch.object(search_service, 'pipeline_service') as mock_pipeline_service, \
             patch.object(search_service, '_retrieve_documents', return_value=[]), \
             patch.object(search_service, '_build_context_from_documents', return_value="test context"), \
             patch.object(search_service, '_build_generation_prompt', return_value="test prompt"):

            # Mock pipeline
            mock_pipeline = Mock()
            mock_pipeline_service.get_pipeline.return_value = mock_pipeline

            # Create search input
            search_input = SearchInput(
                question="What is AI?",
                collection_id="collection_123",
                user_id="user_456"
            )

            # Execute search
            result = await search_service._search_regular_with_tokens(search_input, 0.0)

            # Verify token usage is included in metadata
            assert "token_usage" in result.metadata
            token_usage = result.metadata["token_usage"]
            assert token_usage["prompt_tokens"] == 1200
            assert token_usage["completion_tokens"] == 300
            assert token_usage["total_tokens"] == 1500
            assert token_usage["model_name"] == "gpt-3.5-turbo"

    @pytest.mark.asyncio
    async def test_conversation_service_token_warning_propagation(self):
        """Test that conversation service properly propagates token warnings."""
        # This test would verify that token warnings from search
        # are properly included in conversation responses
        pass

    @pytest.mark.asyncio
    async def test_chain_of_thought_token_aggregation(self):
        """Test that CoT service properly aggregates token usage across steps."""
        # This test would verify that multi-step CoT processes
        # correctly sum token usage from all steps
        pass
```

#### 9.3 End-to-End Tests
**File:** `tests/e2e/test_token_e2e.py` *(NEW)*

```python
"""End-to-end tests for complete token tracking workflow."""

import pytest
from fastapi.testclient import TestClient

from main import app


class TestTokenTrackingE2E:
    """End-to-end tests for token tracking through API."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.e2e
    def test_complete_conversation_with_token_tracking(self, client):
        """Test complete conversation workflow with token tracking."""
        # This test would:
        # 1. Create a session
        # 2. Send multiple messages
        # 3. Verify token usage is tracked in responses
        # 4. Verify warnings appear when approaching limits
        # 5. Verify conversation statistics include token data
        pass

    @pytest.mark.e2e
    def test_token_warning_in_api_response(self, client):
        """Test that token warnings appear in API responses."""
        # This test would send a message that triggers a token warning
        # and verify the warning is included in the response
        pass

    @pytest.mark.e2e
    def test_token_statistics_endpoint(self, client):
        """Test token statistics API endpoint."""
        # This test would:
        # 1. Have a conversation with multiple messages
        # 2. Call the token statistics endpoint
        # 3. Verify statistics are accurate and complete
        pass
```

### 10. Implementation Timeline

#### Phase 1: Foundation (Week 1)
- [ ] Create LLMUsage and TokenWarning schemas
- [ ] Update LLM provider base class with token tracking
- [ ] Implement provider-specific token extraction (OpenAI, Anthropic, IBM)
- [ ] Create TokenWarningService
- [ ] Database migration for model context windows

#### Phase 2: Service Integration (Week 2)
- [ ] Update SearchService with token tracking
- [ ] Update ConversationService with token warnings
- [ ] Update ChainOfThoughtService with multi-step tracking
- [ ] Implement conversation-level token monitoring

#### Phase 3: API and Testing (Week 3)
- [ ] Update API endpoints to include token data
- [ ] Add token statistics endpoint
- [ ] Comprehensive unit test suite
- [ ] Integration tests across services

#### Phase 4: Polish and Deploy (Week 4)
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Documentation updates
- [ ] Production deployment

### 11. Benefits Summary

This implementation provides:

1. **Accurate Token Tracking** - Uses actual API response data instead of estimates
2. **Real-time Warnings** - Proactive notifications before hitting limits
3. **Provider Agnostic** - Works with any LLM provider (OpenAI, Anthropic, IBM)
4. **Service Integration** - Consistent tracking across Search, Conversation, and CoT
5. **Cost Monitoring** - Track actual API usage and costs
6. **User Experience** - Clear warnings and suggestions for users
7. **Analytics** - Comprehensive usage statistics and patterns
8. **Scalability** - Efficient tracking without performance impact

This comprehensive plan addresses the token limit handling requirements for Issue #229 while providing a robust foundation for future LLM integrations and usage monitoring.

---

**End of Document**