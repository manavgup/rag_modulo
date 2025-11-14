# Issue: Implement Structured Output with JSON Schema Validation

**Labels:** `enhancement`, `high-priority`, `llm-providers`
**Milestone:** Production RAG Enhancements
**Estimated Effort:** 6-10 days

---

## Problem Statement

Current RAG system relies entirely on **prompt engineering + regex post-processing** for output formatting. We have no provider-level guarantees about output structure.

### Current State
- `SearchOutput.answer` is unstructured text (`backend/rag_solution/schemas/search_schema.py:49`)
- Post-processing with regex cleanup in `_clean_answer()` (`backend/rag_solution/services/pipeline/stages/generation_stage.py:130-153`)
- No JSON schema validation
- Cannot reliably parse structured data (citations, confidence scores, reasoning steps)

### Impact
- ❌ Cannot parse answers programmatically for downstream processing
- ❌ No guaranteed citation format
- ❌ Cannot validate answer quality automatically
- ❌ UI must handle unpredictable response formats

---

## WatsonX API Capabilities

From https://ibm.github.io/watsonx-ai-python-sdk/v1.4.4/fm_model.html:

✅ **WatsonX.ai Foundation Models SUPPORT:**
1. `GenTextReturnOptMetaNames` - Control response components (tokens, logprobs, etc.)
2. Stop sequences - Controlled termination
3. **Function calling** - `chat()` with `tools` parameter + `tool_choice`
4. **Streaming** - `chat_stream()` and `generate_text_stream()`
5. Multi-turn conversations - Native message list support

---

## Proposed Solution

### Phase 1: Output Schemas (1-2 days)

Create typed output schemas in `backend/rag_solution/schemas/`:

```python
# backend/rag_solution/schemas/structured_output_schema.py

from pydantic import BaseModel, Field
from typing import Literal

class Citation(BaseModel):
    """Citation linking answer to source document."""
    document_id: str = Field(..., description="Source document UUID")
    document_title: str | None = Field(None, description="Document title")
    excerpt: str = Field(..., description="Relevant excerpt from document")
    page_number: int | None = Field(None, description="Page number")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    chunk_id: str | None = Field(None, description="Chunk identifier")

class ReasoningStep(BaseModel):
    """Single reasoning step in structured answer."""
    step_number: int = Field(..., description="Step sequence number")
    thought: str = Field(..., description="Reasoning thought")
    conclusion: str = Field(..., description="Step conclusion")
    citations: list[Citation] = Field(default_factory=list)

class StructuredAnswer(BaseModel):
    """Structured answer with citations and metadata."""
    answer: str = Field(..., description="Main answer text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Answer confidence score")
    citations: list[Citation] = Field(default_factory=list, description="Source citations")
    reasoning_steps: list[ReasoningStep] | None = Field(None, description="Chain of thought steps")
    format_type: Literal["plain", "markdown", "structured"] = Field(
        default="plain", description="Answer format type"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Machine learning is a subset of AI...",
                "confidence": 0.92,
                "citations": [
                    {
                        "document_id": "doc_123",
                        "excerpt": "ML algorithms learn from data...",
                        "page_number": 5,
                        "relevance_score": 0.95
                    }
                ],
                "format_type": "markdown"
            }
        }
```

### Phase 2: Provider Integration (3-5 days)

#### **2.1 Update Base Provider Interface**

```python
# backend/rag_solution/generation/providers/base.py

@abstractmethod
def generate_structured(
    self,
    user_id: UUID4,
    prompt: str,
    output_schema: type[BaseModel],
    model_parameters: LLMParametersInput | None = None,
) -> BaseModel:
    """Generate structured output matching provided schema."""
    pass
```

#### **2.2 WatsonX Implementation (Function Calling)**

```python
# backend/rag_solution/generation/providers/watsonx.py

def generate_structured(
    self,
    user_id: UUID4,
    prompt: str,
    output_schema: type[BaseModel],
    model_parameters: LLMParametersInput | None = None,
) -> BaseModel:
    """Generate structured output using WatsonX function calling."""

    # Convert Pydantic schema to WatsonX tool format
    tool_definition = {
        "name": "structured_answer",
        "description": "Generate structured answer with citations",
        "input_schema": output_schema.model_json_schema()
    }

    # Use WatsonX chat API with tools
    response = self.client.chat(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        tools=[tool_definition],
        tool_choice={"type": "function", "function": {"name": "structured_answer"}}
    )

    # Parse tool call response
    tool_call = response["choices"][0]["message"]["tool_calls"][0]
    structured_data = json.loads(tool_call["function"]["arguments"])

    # Validate and return
    return output_schema.model_validate(structured_data)
```

#### **2.3 OpenAI Implementation (Native JSON Schema)**

```python
# backend/rag_solution/generation/providers/openai.py

def generate_structured(
    self,
    user_id: UUID4,
    prompt: str,
    output_schema: type[BaseModel],
    model_parameters: LLMParametersInput | None = None,
) -> BaseModel:
    """Generate structured output using OpenAI JSON schema mode."""

    response = self.client.chat.completions.create(
        model=self.model_id,
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "structured_answer",
                "schema": output_schema.model_json_schema(),
                "strict": True
            }
        }
    )

    json_response = json.loads(response.choices[0].message.content)
    return output_schema.model_validate(json_response)
```

#### **2.4 Anthropic Implementation (Tool Use)**

```python
# backend/rag_solution/generation/providers/anthropic.py

def generate_structured(
    self,
    user_id: UUID4,
    prompt: str,
    output_schema: type[BaseModel],
    model_parameters: LLMParametersInput | None = None,
) -> BaseModel:
    """Generate structured output using Anthropic tool use."""

    tool_definition = {
        "name": "structured_answer",
        "description": "Generate structured answer",
        "input_schema": output_schema.model_json_schema()
    }

    response = self.client.messages.create(
        model=self.model_id,
        messages=[{"role": "user", "content": prompt}],
        tools=[tool_definition],
        tool_choice={"type": "tool", "name": "structured_answer"}
    )

    tool_use = next(block for block in response.content if block.type == "tool_use")
    return output_schema.model_validate(tool_use.input)
```

### Phase 3: Validation Pipeline (2-3 days)

#### **3.1 Output Validator Service**

```python
# backend/rag_solution/services/output_validator_service.py

class OutputValidatorService:
    """Validates and retries structured output generation."""

    def validate_structured_output(
        self,
        output: StructuredAnswer,
        query_results: list[QueryResult],
        quality_threshold: float = 0.6
    ) -> tuple[bool, float, dict[str, Any]]:
        """
        Validate structured output quality.

        Returns:
            (is_valid, quality_score, validation_details)
        """
        issues = []

        # 1. Check citation validity
        cited_doc_ids = {c.document_id for c in output.citations}
        available_doc_ids = {qr.document_id for qr in query_results if qr.document_id}
        invalid_citations = cited_doc_ids - available_doc_ids

        if invalid_citations:
            issues.append(f"Invalid citations: {invalid_citations}")

        # 2. Check answer completeness
        if len(output.answer) < 10:
            issues.append("Answer too short")

        # 3. Check confidence calibration
        if output.confidence > 0.95 and len(output.citations) == 0:
            issues.append("High confidence without citations suspicious")

        # 4. Calculate quality score
        quality_score = self._calculate_quality_score(output, query_results)

        is_valid = len(issues) == 0 and quality_score >= quality_threshold

        return is_valid, quality_score, {
            "issues": issues,
            "cited_docs": len(output.citations),
            "answer_length": len(output.answer)
        }

    async def generate_with_retry(
        self,
        provider: LLMBase,
        user_id: UUID4,
        prompt: str,
        output_schema: type[BaseModel],
        query_results: list[QueryResult],
        max_retries: int = 3,
        quality_threshold: float = 0.6
    ) -> StructuredAnswer:
        """Generate with validation and retry logic."""

        for attempt in range(max_retries):
            try:
                # Generate structured output
                output = provider.generate_structured(user_id, prompt, output_schema)

                # Validate
                is_valid, quality_score, details = self.validate_structured_output(
                    output, query_results, quality_threshold
                )

                if is_valid:
                    logger.info(f"Valid output on attempt {attempt + 1}, quality={quality_score:.3f}")
                    return output

                logger.warning(
                    f"Attempt {attempt + 1} failed validation: quality={quality_score:.3f}, "
                    f"issues={details['issues']}"
                )

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed with error: {e}")

        # Fallback: return unstructured answer
        logger.error("All retries exhausted, falling back to unstructured")
        raise ValidationError("Failed to generate valid structured output after retries")
```

#### **3.2 Integration with Generation Stage**

```python
# backend/rag_solution/services/pipeline/stages/generation_stage.py

async def _generate_answer_from_documents(self, context: SearchContext) -> str:
    """Generate answer using LLM from documents."""

    # Check if structured output requested
    config_metadata = context.search_input.config_metadata or {}
    use_structured = config_metadata.get("structured_output", False)

    if use_structured:
        # Use structured output pipeline
        validator = OutputValidatorService()
        structured_answer = await validator.generate_with_retry(
            provider=provider,
            user_id=context.user_id,
            prompt=query,
            output_schema=StructuredAnswer,
            query_results=context.query_results,
            max_retries=3,
            quality_threshold=0.6
        )

        # Store structured output in context
        context.structured_answer = structured_answer

        # Return answer text
        return structured_answer.answer
    else:
        # Existing unstructured path
        answer = self.pipeline_service._generate_answer(...)
        return answer
```

---

## Updated SearchOutput Schema

```python
# backend/rag_solution/schemas/search_schema.py

class SearchOutput(BaseModel):
    """Output schema for search responses."""

    answer: str  # Keep for backward compatibility
    documents: list[DocumentMetadata]
    query_results: list[QueryResult]
    rewritten_query: str | None = None
    evaluation: dict[str, Any] | None = None
    execution_time: float | None = None
    cot_output: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    token_warning: TokenWarning | None = None

    # NEW: Structured output
    structured_answer: StructuredAnswer | None = Field(
        None,
        description="Structured answer with citations (when requested)"
    )
```

---

## API Usage Example

```python
# Enable structured output via config_metadata
search_input = SearchInput(
    question="What are the benefits of machine learning?",
    collection_id=collection_uuid,
    user_id=user_uuid,
    config_metadata={
        "structured_output": True,  # Request structured format
        "format_type": "markdown",  # Optional format preference
        "include_citations": True   # Require citations
    }
)

# Response will include structured_answer
response: SearchOutput = await search_service.search(search_input)

if response.structured_answer:
    print(f"Answer: {response.structured_answer.answer}")
    print(f"Confidence: {response.structured_answer.confidence}")
    print(f"Citations: {len(response.structured_answer.citations)}")

    for citation in response.structured_answer.citations:
        print(f"  - {citation.document_title} (p.{citation.page_number})")
        print(f"    Relevance: {citation.relevance_score:.2f}")
```

---

## Files to Modify

1. **Schemas**
   - `backend/rag_solution/schemas/structured_output_schema.py` - NEW
   - `backend/rag_solution/schemas/search_schema.py` - Add `structured_answer` field

2. **Providers**
   - `backend/rag_solution/generation/providers/base.py` - Add `generate_structured()` abstract method
   - `backend/rag_solution/generation/providers/watsonx.py` - Implement function calling
   - `backend/rag_solution/generation/providers/openai.py` - Implement JSON schema mode
   - `backend/rag_solution/generation/providers/anthropic.py` - Implement tool use

3. **Services**
   - `backend/rag_solution/services/output_validator_service.py` - NEW
   - `backend/rag_solution/services/pipeline/stages/generation_stage.py` - Integrate validation

4. **Tests**
   - `tests/unit/services/test_output_validator.py` - NEW
   - `tests/unit/generation/test_structured_output.py` - NEW
   - `tests/integration/test_structured_search.py` - NEW

5. **Documentation**
   - `docs/api/structured_output.md` - NEW
   - `docs/features/structured-output-guide.md` - NEW
   - Update `docs/api/search_api.md`

---

## Acceptance Criteria

- [ ] `StructuredAnswer`, `Citation`, `ReasoningStep` schemas defined
- [ ] WatsonX provider implements function calling for structured output
- [ ] OpenAI provider uses native JSON schema mode
- [ ] Anthropic provider uses tool use for structured output
- [ ] `OutputValidatorService` with validation and retry logic
- [ ] Integration with `GenerationStage`
- [ ] `SearchOutput` includes optional `structured_answer` field
- [ ] API parameter `config_metadata.structured_output: true` enables feature
- [ ] Unit tests for all providers (100% coverage)
- [ ] Integration tests with quality validation
- [ ] Documentation with usage examples
- [ ] Backward compatibility maintained (default is unstructured)

---

## Testing Strategy

### Unit Tests
```python
def test_watsonx_structured_output():
    """Test WatsonX function calling for structured output."""
    provider = WatsonXProvider(...)
    output = provider.generate_structured(
        user_id=test_user,
        prompt="What is machine learning?",
        output_schema=StructuredAnswer
    )
    assert isinstance(output, StructuredAnswer)
    assert output.answer
    assert 0.0 <= output.confidence <= 1.0
    assert len(output.citations) > 0

def test_output_validator_invalid_citations():
    """Test validator catches invalid citations."""
    validator = OutputValidatorService()
    output = StructuredAnswer(
        answer="Test",
        confidence=0.9,
        citations=[Citation(document_id="fake_id", excerpt="test", relevance_score=0.8)]
    )
    query_results = [QueryResult(document_id="real_id", ...)]

    is_valid, score, details = validator.validate_structured_output(output, query_results)
    assert not is_valid
    assert "Invalid citations" in str(details["issues"])
```

### Integration Tests
```python
@pytest.mark.integration
async def test_search_with_structured_output():
    """Test end-to-end structured output pipeline."""
    search_input = SearchInput(
        question="What is machine learning?",
        collection_id=collection_id,
        user_id=user_id,
        config_metadata={"structured_output": True}
    )

    response = await search_service.search(search_input)

    assert response.structured_answer is not None
    assert isinstance(response.structured_answer, StructuredAnswer)
    assert response.structured_answer.confidence >= 0.6
    assert len(response.structured_answer.citations) > 0

    # Verify citations reference actual retrieved documents
    cited_ids = {c.document_id for c in response.structured_answer.citations}
    retrieved_ids = {qr.document_id for qr in response.query_results if qr.document_id}
    assert cited_ids.issubset(retrieved_ids)
```

---

## References

- WatsonX Foundation Models API: https://ibm.github.io/watsonx-ai-python-sdk/v1.4.4/fm_model.html
- OpenAI Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- Anthropic Tool Use: https://docs.anthropic.com/en/docs/tool-use
- Related Issue #461: Chain of Thought hardening with quality scoring

---

## Priority

**HIGH** - Blocks reliable downstream processing, UI integration, and programmatic answer parsing

---

## Estimated Effort

**6-10 days** (1 developer)

- Phase 1: 1-2 days
- Phase 2: 3-5 days
- Phase 3: 2-3 days
