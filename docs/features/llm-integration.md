# LLM Integration

This document describes how RAG Modulo integrates with multiple LLM providers, including configuration, provider management, prompt templates, and token tracking.

## Overview

RAG Modulo supports multiple LLM providers through a unified interface:

- **WatsonX** (IBM): Enterprise-grade AI platform
- **OpenAI**: GPT-3.5, GPT-4 models
- **Anthropic**: Claude models
- **Extensible Architecture**: Easy to add new providers

Key features:
- **Provider Factory Pattern**: Single interface for all providers
- **Singleton Caching**: Reuse provider instances for performance
- **Per-User Configuration**: Customize LLM settings per user
- **Prompt Templates**: Reusable prompt management
- **Token Tracking**: Monitor usage and enforce limits
- **Structured Output**: Parse LLM responses reliably

## Provider Architecture

### Factory Pattern

**Centralized provider management**:

```python
# backend/rag_solution/generation/providers/factory.py
from threading import Lock
from typing import ClassVar

class LLMProviderFactory:
    """Factory for creating and caching LLM provider instances"""

    _providers: ClassVar[dict[str, type[LLMBase]]] = {}
    _instances: ClassVar[dict[str, LLMBase]] = {}
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def register_provider(
        cls,
        name: str,
        provider_class: type[LLMBase]
    ):
        """Register a new provider type"""
        cls._providers[name] = provider_class

    def get_provider(
        self,
        provider_name: str,
        model_id: str | None = None
    ) -> LLMBase:
        """Get cached provider instance"""
        cache_key = f"{provider_name}:{model_id}"

        # Check cache first
        if cache_key in self._instances:
            provider = self._instances[cache_key]
            self._validate_provider_instance(provider, provider_name)
            return provider

        # Double-checked locking for thread safety
        with self._lock:
            if cache_key not in self._instances:
                provider = self._create_provider(provider_name, model_id)
                self._instances[cache_key] = provider

        return self._instances[cache_key]

    def _create_provider(
        self,
        provider_name: str,
        model_id: str | None
    ) -> LLMBase:
        """Create new provider instance"""
        if provider_name not in self._providers:
            raise ValueError(f"Unknown provider: {provider_name}")

        provider_class = self._providers[provider_name]

        # Inject dependencies
        provider = provider_class(
            self._llm_provider_service,
            self._llm_parameters_service,
            self._prompt_template_service,
            self._llm_model_service,
        )

        # Initialize with model
        if model_id:
            provider.set_model(model_id)

        return provider
```

### Base Provider Interface

**Common interface** for all providers:

```python
# backend/rag_solution/generation/providers/base.py
from abc import ABC, abstractmethod

class LLMBase(ABC):
    """Base class for all LLM providers"""

    def __init__(
        self,
        llm_provider_service,
        parameters_service,
        prompt_template_service,
        llm_model_service
    ):
        self.llm_provider_service = llm_provider_service
        self.parameters_service = parameters_service
        self.prompt_template_service = prompt_template_service
        self.llm_model_service = llm_model_service

    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """Generate text response from prompt"""
        pass

    @abstractmethod
    def validate_client(self) -> None:
        """Validate client is properly configured"""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response tokens as they're generated"""
        pass

    def get_model_info(self) -> dict[str, Any]:
        """Get model information"""
        return {
            "provider": self.provider_name,
            "model_id": self.model_id,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
```

## Provider Implementations

### WatsonX Provider

**IBM WatsonX integration**:

```python
# backend/rag_solution/generation/providers/watsonx.py
from ibm_watsonx_ai.foundation_models import Model

class WatsonxProvider(LLMBase):
    """IBM WatsonX LLM provider"""

    provider_name = "watsonx"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = get_settings()

        # Initialize WatsonX client
        self.client = Model(
            model_id=self.model_id,
            credentials={
                "url": self.settings.watsonx_url,
                "apikey": self.settings.watsonx_apikey
            },
            project_id=self.settings.watsonx_instance_id,
            params={
                "max_new_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": 0.9,
                "top_k": 50
            }
        )

    async def generate_response(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """Generate response using WatsonX"""
        # Override default parameters if provided
        params = {
            "max_new_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", 0.9),
        }

        # Generate response
        response = self.client.generate(
            prompt=prompt,
            params=params
        )

        # Extract text from response
        return response["results"][0]["generated_text"]

    def validate_client(self) -> None:
        """Validate WatsonX configuration"""
        if not self.settings.watsonx_apikey:
            raise ValueError("WatsonX API key not configured")

        if not self.settings.watsonx_instance_id:
            raise ValueError("WatsonX project ID not configured")

    async def generate_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream WatsonX response"""
        params = {
            "max_new_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
        }

        async for chunk in self.client.generate_stream(
            prompt=prompt,
            params=params
        ):
            yield chunk["results"][0]["generated_text"]
```

**Configuration**:

```bash
# .env
WATSONX_APIKEY=your_api_key
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_INSTANCE_ID=your_project_id

# Available models
WATSONX_MODEL=ibm/granite-13b-chat-v2
# or: meta-llama/llama-2-70b-chat
# or: mistralai/mixtral-8x7b-instruct-v01
```

### OpenAI Provider

**OpenAI GPT integration**:

```python
# backend/rag_solution/generation/providers/openai.py
import openai

class OpenAIProvider(LLMBase):
    """OpenAI GPT provider"""

    provider_name = "openai"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = get_settings()

        # Initialize OpenAI client
        openai.api_key = self.settings.openai_api_key
        self.client = openai

    async def generate_response(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """Generate response using OpenAI"""
        response = await self.client.ChatCompletion.acreate(
            model=self.model_id,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            temperature=kwargs.get("temperature", self.temperature),
            top_p=kwargs.get("top_p", 1.0),
        )

        return response.choices[0].message.content

    def validate_client(self) -> None:
        """Validate OpenAI configuration"""
        if not self.settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")

    async def generate_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream OpenAI response"""
        response = await self.client.ChatCompletion.acreate(
            model=self.model_id,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            temperature=kwargs.get("temperature", self.temperature),
            stream=True
        )

        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

**Configuration**:

```bash
# .env
OPENAI_API_KEY=sk-your_api_key

# Available models
OPENAI_MODEL=gpt-4
# or: gpt-3.5-turbo
# or: gpt-4-turbo
```

### Anthropic Provider

**Claude integration**:

```python
# backend/rag_solution/generation/providers/anthropic.py
import anthropic

class AnthropicProvider(LLMBase):
    """Anthropic Claude provider"""

    provider_name = "anthropic"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = get_settings()

        # Initialize Anthropic client
        self.client = anthropic.Anthropic(
            api_key=self.settings.anthropic_api_key
        )

    async def generate_response(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """Generate response using Claude"""
        message = await self.client.messages.create(
            model=self.model_id,
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            temperature=kwargs.get("temperature", self.temperature),
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text

    def validate_client(self) -> None:
        """Validate Anthropic configuration"""
        if not self.settings.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")

    async def generate_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream Claude response"""
        async with self.client.messages.stream(
            model=self.model_id,
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            temperature=kwargs.get("temperature", self.temperature),
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            async for text in stream.text_stream:
                yield text
```

**Configuration**:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-your_api_key

# Available models
ANTHROPIC_MODEL=claude-3-opus-20240229
# or: claude-3-sonnet-20240229
# or: claude-3-haiku-20240307
```

## Provider Management

### User Provider Configuration

**Per-user LLM settings**:

```python
# backend/rag_solution/services/llm_provider_service.py
class LLMProviderService:
    def __init__(self, db: Session):
        self.db = db

    async def get_user_provider(
        self,
        user_id: UUID4
    ) -> LLMProvider:
        """Get user's LLM provider configuration"""
        provider = (
            self.db.query(LLMProvider)
            .filter(LLMProvider.user_id == user_id)
            .first()
        )

        if not provider:
            # Create default provider
            provider = await self.create_default_provider(user_id)

        return provider

    async def create_default_provider(
        self,
        user_id: UUID4
    ) -> LLMProvider:
        """Create default provider for user"""
        provider = LLMProvider(
            user_id=user_id,
            provider_name="watsonx",
            model_id="ibm/granite-13b-chat-v2",
            max_tokens=1024,
            temperature=0.7
        )

        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)

        return provider

    async def update_provider(
        self,
        user_id: UUID4,
        provider_name: str,
        model_id: str,
        parameters: dict[str, Any]
    ) -> LLMProvider:
        """Update user's provider configuration"""
        provider = await self.get_user_provider(user_id)

        provider.provider_name = provider_name
        provider.model_id = model_id
        provider.max_tokens = parameters.get("max_tokens", 1024)
        provider.temperature = parameters.get("temperature", 0.7)

        self.db.commit()
        self.db.refresh(provider)

        return provider
```

### API Endpoints

**Manage provider configuration**:

```python
# backend/rag_solution/router/llm_provider_router.py
@router.get("/providers", response_model=list[LLMProviderOutput])
async def list_providers(
    current_user: dict = Depends(get_current_user)
):
    """List available LLM providers"""
    return [
        {"name": "watsonx", "models": ["ibm/granite-13b-chat-v2"]},
        {"name": "openai", "models": ["gpt-4", "gpt-3.5-turbo"]},
        {"name": "anthropic", "models": ["claude-3-opus-20240229"]}
    ]

@router.get("/providers/user", response_model=LLMProviderOutput)
async def get_user_provider(
    current_user: dict = Depends(get_current_user),
    provider_service: LLMProviderService = Depends(get_llm_provider_service)
):
    """Get user's current provider configuration"""
    user_id = UUID(current_user["uuid"])
    provider = await provider_service.get_user_provider(user_id)
    return provider

@router.put("/providers/user", response_model=LLMProviderOutput)
async def update_user_provider(
    provider_input: LLMProviderInput,
    current_user: dict = Depends(get_current_user),
    provider_service: LLMProviderService = Depends(get_llm_provider_service)
):
    """Update user's provider configuration"""
    user_id = UUID(current_user["uuid"])

    provider = await provider_service.update_provider(
        user_id=user_id,
        provider_name=provider_input.provider_name,
        model_id=provider_input.model_id,
        parameters={
            "max_tokens": provider_input.max_tokens,
            "temperature": provider_input.temperature
        }
    )

    return provider
```

## Prompt Templates

### Template Management

**Reusable prompt templates**:

```python
# backend/rag_solution/services/prompt_template_service.py
class PromptTemplateService:
    def __init__(self, db: Session):
        self.db = db

    async def get_template(
        self,
        name: str,
        user_id: UUID4 | None = None
    ) -> PromptTemplate:
        """Get prompt template by name"""
        # Try user-specific template first
        if user_id:
            template = (
                self.db.query(PromptTemplate)
                .filter(
                    PromptTemplate.name == name,
                    PromptTemplate.user_id == user_id
                )
                .first()
            )
            if template:
                return template

        # Fallback to system template
        template = (
            self.db.query(PromptTemplate)
            .filter(
                PromptTemplate.name == name,
                PromptTemplate.user_id.is_(None)
            )
            .first()
        )

        if not template:
            raise NotFoundError(
                resource_type="PromptTemplate",
                resource_id=name
            )

        return template

    async def create_template(
        self,
        name: str,
        template: str,
        user_id: UUID4 | None = None,
        description: str | None = None
    ) -> PromptTemplate:
        """Create new prompt template"""
        template_obj = PromptTemplate(
            name=name,
            template=template,
            user_id=user_id,
            description=description
        )

        self.db.add(template_obj)
        self.db.commit()
        self.db.refresh(template_obj)

        return template_obj
```

### Built-in Templates

**System prompt templates**:

```python
# RAG Generation Template
RAG_GENERATION_TEMPLATE = """You are a helpful AI assistant. Answer the user's question based on the provided context.

Context:
{context}

Question: {question}

Instructions:
- Provide a clear, concise answer
- Cite sources using [1], [2], etc.
- If the context doesn't contain enough information, say so
- Structure your response with <thinking> and <answer> tags

Response:"""

# Chain of Thought Template
COT_REASONING_TEMPLATE = """You are reasoning through a complex question step by step.

Original Question: {original_question}
Current Sub-Question: {sub_question}

Context from previous steps:
{accumulated_context}

Retrieved Documents:
{documents}

Provide your reasoning in the following format:
<thinking>
[Your step-by-step reasoning process]
</thinking>

<answer>
[Your answer to the sub-question]
</answer>"""

# Query Rewriting Template
QUERY_REWRITE_TEMPLATE = """Rewrite the following query to improve retrieval results.

Original Query: {query}

Conversation History:
{conversation_history}

Rewritten Query (return only the rewritten query):"""
```

### Template Usage

**Format templates** with variables:

```python
async def format_prompt(
    template_name: str,
    user_id: UUID4,
    **variables
) -> str:
    """Format prompt template with variables"""
    # Get template
    template = await prompt_service.get_template(template_name, user_id)

    # Format with variables
    try:
        formatted = template.template.format(**variables)
        return formatted
    except KeyError as e:
        raise ValueError(f"Missing template variable: {e}")

# Usage
prompt = await format_prompt(
    template_name="rag_generation",
    user_id=user_id,
    context=context_text,
    question=question
)
```

## Token Tracking

### Usage Monitoring

**Track LLM token usage**:

```python
# backend/rag_solution/services/token_tracking_service.py
class TokenTrackingService:
    def __init__(self, db: Session):
        self.db = db

    async def track_usage(
        self,
        user_id: UUID4,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ):
        """Track token usage"""
        total_tokens = prompt_tokens + completion_tokens

        # Record usage
        usage = TokenUsage(
            user_id=user_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            timestamp=datetime.utcnow()
        )

        self.db.add(usage)
        self.db.commit()

        # Check if user exceeds limits
        await self._check_limits(user_id)

    async def _check_limits(self, user_id: UUID4):
        """Check if user exceeds token limits"""
        # Get usage for today
        today = datetime.utcnow().date()
        usage = (
            self.db.query(func.sum(TokenUsage.total_tokens))
            .filter(
                TokenUsage.user_id == user_id,
                TokenUsage.timestamp >= today
            )
            .scalar()
        )

        # User limit: 100,000 tokens per day
        daily_limit = 100000

        if usage >= daily_limit:
            # Create warning
            warning = TokenWarning(
                user_id=user_id,
                current_usage=usage,
                limit=daily_limit,
                message="Daily token limit reached"
            )
            self.db.add(warning)
            self.db.commit()

    async def get_usage_stats(
        self,
        user_id: UUID4,
        days: int = 7
    ) -> dict[str, Any]:
        """Get usage statistics"""
        start_date = datetime.utcnow() - timedelta(days=days)

        usage = (
            self.db.query(
                func.sum(TokenUsage.total_tokens).label("total"),
                func.sum(TokenUsage.prompt_tokens).label("prompt"),
                func.sum(TokenUsage.completion_tokens).label("completion")
            )
            .filter(
                TokenUsage.user_id == user_id,
                TokenUsage.timestamp >= start_date
            )
            .first()
        )

        return {
            "total_tokens": usage.total or 0,
            "prompt_tokens": usage.prompt or 0,
            "completion_tokens": usage.completion or 0,
            "period_days": days
        }
```

### Token Estimation

**Estimate tokens** before API calls:

```python
import tiktoken

def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """Estimate number of tokens in text"""
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return len(tokens)

# Usage
prompt_tokens = estimate_tokens(prompt, model="gpt-4")
if prompt_tokens > 8000:
    raise ValueError("Prompt exceeds token limit")
```

## Structured Output Parsing

### XML-Based Parsing

**Parse structured LLM responses**:

```python
import xml.etree.ElementTree as ET
import re

def parse_llm_response(response: str) -> dict[str, Any]:
    """Parse structured LLM response with XML tags"""
    # Strategy 1: XML parsing
    try:
        # Wrap in root element for parsing
        xml_text = f"<root>{response}</root>"
        root = ET.fromstring(xml_text)

        thinking = root.find("thinking")
        answer = root.find("answer")

        if thinking is not None and answer is not None:
            return {
                "thinking": thinking.text.strip(),
                "answer": answer.text.strip(),
                "quality_score": 1.0,
                "parse_strategy": "xml"
            }
    except ET.ParseError:
        pass

    # Strategy 2: Regex extraction
    thinking_match = re.search(
        r"<thinking>(.*?)</thinking>",
        response,
        re.DOTALL
    )
    answer_match = re.search(
        r"<answer>(.*?)</answer>",
        response,
        re.DOTALL
    )

    if thinking_match and answer_match:
        return {
            "thinking": thinking_match.group(1).strip(),
            "answer": answer_match.group(1).strip(),
            "quality_score": 0.9,
            "parse_strategy": "regex"
        }

    # Strategy 3: Fallback - use full response
    return {
        "thinking": "",
        "answer": response,
        "quality_score": 0.5,
        "parse_strategy": "fallback"
    }
```

### Quality Scoring

**Assess response quality**:

```python
def calculate_quality_score(parsed: dict[str, Any]) -> float:
    """Calculate quality score for parsed response"""
    score = parsed.get("quality_score", 0.5)

    # Deduct for missing components
    if not parsed.get("thinking"):
        score -= 0.2

    if not parsed.get("answer"):
        score -= 0.3

    # Deduct for artifacts
    if "<thinking>" in parsed.get("answer", ""):
        score -= 0.3  # Answer contains thinking tags

    if "</answer>" in parsed.get("answer", ""):
        score -= 0.2  # Answer contains closing tags

    return max(0.0, min(1.0, score))
```

## Configuration

### Environment Variables

```bash
# WatsonX
WATSONX_APIKEY=your_api_key
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_INSTANCE_ID=your_project_id
WATSONX_MODEL=ibm/granite-13b-chat-v2

# OpenAI
OPENAI_API_KEY=sk-your_api_key
OPENAI_MODEL=gpt-4

# Anthropic
ANTHROPIC_API_KEY=sk-ant-your_api_key
ANTHROPIC_MODEL=claude-3-opus-20240229

# Token Limits
TOKEN_LIMIT_PER_DAY=100000
TOKEN_LIMIT_PER_REQUEST=8000

# Generation Settings
DEFAULT_MAX_TOKENS=1024
DEFAULT_TEMPERATURE=0.7
DEFAULT_TOP_P=0.9
```

## Best Practices

### Provider Selection

1. **WatsonX**: Enterprise use cases, on-premise deployment
2. **OpenAI**: General-purpose, high-quality responses
3. **Anthropic**: Long context, complex reasoning

### Performance

1. **Cache provider instances** - Use factory pattern
2. **Batch requests** - Process multiple prompts together
3. **Stream responses** - Improve perceived latency
4. **Monitor token usage** - Track costs and limits

### Quality

1. **Use structured output** - Parse responses reliably
2. **Implement retry logic** - Handle API failures
3. **Validate responses** - Check quality scores
4. **Template prompts** - Reuse proven patterns

## Related Documentation

- [Search and Retrieval](search-retrieval.md) - Using LLMs for RAG
- [Chain of Thought](chain-of-thought/index.md) - Advanced reasoning
- [Architecture - Components](../architecture/components.md) - System design
- [Troubleshooting](../troubleshooting/debugging.md) - Debug LLM issues
