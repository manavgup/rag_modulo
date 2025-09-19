# CoT Examples and Usage Patterns

This document provides practical examples and usage patterns for implementing Chain of Thought reasoning in different scenarios.

## Basic Usage Examples

### Simple CoT Execution

```python
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput

# Initialize service
cot_service = ChainOfThoughtService(settings=app_settings)

# Create input
cot_input = ChainOfThoughtInput(
    question="Compare machine learning and deep learning approaches",
    collection_id=collection_uuid,
    user_id=user_uuid
)

# Execute reasoning
result = await cot_service.execute_chain_of_thought(cot_input)

# Access results
print(f"Final Answer: {result.final_answer}")
print(f"Reasoning Steps: {len(result.reasoning_steps)}")
for i, step in enumerate(result.reasoning_steps, 1):
    print(f"Step {i}: {step.question}")
    print(f"Answer: {step.intermediate_answer}")
    print(f"Confidence: {step.confidence_score:.2f}")
```

### Question Classification Example

```python
# Classify question before processing
question = "Why does increasing the learning rate sometimes cause training instability in neural networks?"

classification = await cot_service.classify_question(question)
print(f"Question Type: {classification.question_type}")  # "causal"
print(f"Complexity: {classification.complexity_level}")  # "high"
print(f"Requires CoT: {classification.requires_cot}")    # True
print(f"Estimated Steps: {classification.estimated_steps}")  # 3-4

if classification.requires_cot:
    # Proceed with CoT reasoning
    result = await cot_service.execute_chain_of_thought(cot_input)
else:
    # Use regular search
    result = await regular_search(question)
```

## Question Type Examples

### Multi-part Questions

**Question**: "What are supervised and unsupervised learning, and how do they differ in their approach to image recognition?"

**Expected Decomposition**:
```python
[
    "What is supervised learning?",
    "What is unsupervised learning?",
    "How do supervised and unsupervised learning differ for image recognition?"
]
```

**Implementation**:
```python
cot_input = ChainOfThoughtInput(
    question="What are supervised and unsupervised learning, and how do they differ in their approach to image recognition?",
    collection_id=collection_uuid,
    user_id=user_uuid,
    cot_config={
        "reasoning_strategy": "decomposition",
        "max_reasoning_depth": 3
    }
)

result = await cot_service.execute_chain_of_thought(cot_input)

# Typical output structure:
# Step 1: Definition of supervised learning
# Step 2: Definition of unsupervised learning
# Step 3: Comparison for image recognition
```

### Comparison Questions

**Question**: "Which is better for natural language processing: transformer models or RNN models?"

**Expected Decomposition**:
```python
[
    "What are transformer models and their strengths for NLP?",
    "What are RNN models and their strengths for NLP?",
    "How do transformer and RNN models compare for NLP tasks?"
]
```

**Implementation**:
```python
cot_input = ChainOfThoughtInput(
    question="Which is better for natural language processing: transformer models or RNN models?",
    collection_id=collection_uuid,
    user_id=user_uuid,
    cot_config={
        "reasoning_strategy": "comparison",
        "max_reasoning_depth": 3,
        "evaluation_threshold": 0.7
    }
)

result = await cot_service.execute_chain_of_thought(cot_input)
```

### Causal Questions

**Question**: "Why do deep neural networks sometimes suffer from vanishing gradients?"

**Expected Decomposition**:
```python
[
    "What are gradients in neural networks?",
    "How do gradients propagate through deep networks?",
    "What causes gradients to vanish and what are the consequences?"
]
```

**Implementation**:
```python
cot_input = ChainOfThoughtInput(
    question="Why do deep neural networks sometimes suffer from vanishing gradients?",
    collection_id=collection_uuid,
    user_id=user_uuid,
    cot_config={
        "reasoning_strategy": "causal",
        "max_reasoning_depth": 4
    }
)

result = await cot_service.execute_chain_of_thought(cot_input)
```

### Complex Analytical Questions

**Question**: "Analyze the trade-offs between accuracy, interpretability, and computational efficiency in different machine learning model types."

**Expected Decomposition**:
```python
[
    "What are the different types of machine learning models?",
    "How do these models compare in terms of accuracy?",
    "How do these models compare in terms of interpretability?",
    "How do these models compare in terms of computational efficiency?",
    "What are the key trade-offs between these three factors?"
]
```

**Implementation**:
```python
cot_input = ChainOfThoughtInput(
    question="Analyze the trade-offs between accuracy, interpretability, and computational efficiency in different machine learning model types.",
    collection_id=collection_uuid,
    user_id=user_uuid,
    cot_config={
        "reasoning_strategy": "hierarchical",
        "max_reasoning_depth": 5,
        "token_budget_multiplier": 2.5
    }
)

result = await cot_service.execute_chain_of_thought(cot_input)
```

## Integration Patterns

### With Search Service

```python
class EnhancedSearchService:
    def __init__(self, search_service: SearchService, cot_service: ChainOfThoughtService):
        self.search_service = search_service
        self.cot_service = cot_service

    async def intelligent_search(self, search_input: SearchInput) -> SearchOutput:
        # Classify question
        classification = await self.cot_service.classify_question(search_input.question)

        if classification.requires_cot and classification.complexity_level in ["high", "very_high"]:
            return await self._cot_search(search_input, classification)
        else:
            return await self._regular_search(search_input)

    async def _cot_search(self, search_input: SearchInput, classification: QuestionClassification) -> SearchOutput:
        # Retrieve context documents first
        initial_results = await self.search_service.retrieve_context(
            query=search_input.question,
            collection_id=search_input.collection_id,
            top_k=10
        )

        # Execute CoT with context
        cot_input = ChainOfThoughtInput(
            question=search_input.question,
            collection_id=search_input.collection_id,
            user_id=search_input.user_id,
            cot_config=self._get_strategy_config(classification)
        )

        cot_result = await self.cot_service.execute_chain_of_thought(
            cot_input=cot_input,
            context_documents=[doc.content for doc in initial_results]
        )

        # Return enhanced search output
        return SearchOutput(
            answer=cot_result.final_answer,
            sources=cot_result.source_summary.primary_sources,
            confidence=cot_result.total_confidence,
            reasoning_trace=cot_result.reasoning_steps,
            metadata={
                "cot_enabled": True,
                "reasoning_strategy": cot_result.reasoning_strategy,
                "steps_taken": len(cot_result.reasoning_steps),
                "token_usage": cot_result.token_usage
            }
        )

    def _get_strategy_config(self, classification: QuestionClassification) -> dict:
        strategy_configs = {
            "comparison": {
                "reasoning_strategy": "decomposition",
                "max_reasoning_depth": 3,
                "evaluation_threshold": 0.7
            },
            "causal": {
                "reasoning_strategy": "causal",
                "max_reasoning_depth": 4,
                "evaluation_threshold": 0.6
            },
            "multi_part": {
                "reasoning_strategy": "decomposition",
                "max_reasoning_depth": 3,
                "evaluation_threshold": 0.6
            },
            "complex_analytical": {
                "reasoning_strategy": "hierarchical",
                "max_reasoning_depth": 5,
                "evaluation_threshold": 0.8,
                "token_budget_multiplier": 2.5
            }
        }
        return strategy_configs.get(classification.question_type, {})
```

### With FastAPI Endpoints

```python
from fastapi import FastAPI, HTTPException, Depends
from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput, ChainOfThoughtOutput

app = FastAPI()

@app.post("/search/cot", response_model=SearchOutput)
async def search_with_cot(
    search_input: SearchInput,
    cot_service: ChainOfThoughtService = Depends(get_cot_service)
):
    """Enhanced search with Chain of Thought reasoning."""
    try:
        # Check if CoT should be applied
        classification = await cot_service.classify_question(search_input.question)

        if not classification.requires_cot:
            # Fallback to regular search
            return await regular_search(search_input)

        # Execute CoT reasoning
        cot_input = ChainOfThoughtInput(
            question=search_input.question,
            collection_id=search_input.collection_id,
            user_id=search_input.user_id,
            cot_config=search_input.config_metadata.get("cot_config")
        )

        result = await cot_service.execute_chain_of_thought(cot_input)

        return SearchOutput(
            answer=result.final_answer,
            sources=result.source_summary.primary_sources if result.source_summary else [],
            confidence=result.total_confidence,
            reasoning_steps=result.reasoning_steps,
            metadata={
                "cot_classification": classification.model_dump(),
                "execution_time": result.total_execution_time,
                "token_usage": result.token_usage
            }
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {e}")
    except LLMProviderError as e:
        raise HTTPException(status_code=502, detail=f"LLM service error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")

@app.get("/cot/classify")
async def classify_question(
    question: str,
    cot_service: ChainOfThoughtService = Depends(get_cot_service)
):
    """Classify a question for CoT applicability."""
    classification = await cot_service.classify_question(question)
    return classification.model_dump()
```

### CLI Integration Examples

```python
# Enhanced CLI with CoT support
import click
from rag_solution.cli.client import RAGCLIClient

@click.command()
@click.argument("question")
@click.option("--collection-id", required=True)
@click.option("--cot/--no-cot", default=None, help="Enable/disable CoT reasoning")
@click.option("--cot-strategy", type=click.Choice(["decomposition", "iterative", "hierarchical", "causal"]), help="CoT reasoning strategy")
@click.option("--cot-depth", type=int, help="Maximum reasoning depth")
@click.option("--show-steps", is_flag=True, help="Show individual reasoning steps")
def search_with_cot(question, collection_id, cot, cot_strategy, cot_depth, show_steps):
    """Search with optional Chain of Thought reasoning."""
    client = RAGCLIClient()

    # Build CoT configuration
    cot_config = {}
    if cot is not None:
        cot_config["enabled"] = cot
    if cot_strategy:
        cot_config["reasoning_strategy"] = cot_strategy
    if cot_depth:
        cot_config["max_reasoning_depth"] = cot_depth

    # Execute search
    search_input = {
        "question": question,
        "collection_id": collection_id,
        "user_id": client.get_current_user_id(),
        "config_metadata": {
            "cot_config": cot_config
        } if cot_config else None
    }

    try:
        result = client.search(search_input)

        # Display results
        click.echo(f"\n🤖 Answer: {result['answer']}")

        if result.get('confidence'):
            click.echo(f"📊 Confidence: {result['confidence']:.1%}")

        if show_steps and result.get('reasoning_steps'):
            click.echo("\n🔍 Reasoning Steps:")
            for i, step in enumerate(result['reasoning_steps'], 1):
                click.echo(f"\n  Step {i}: {step['question']}")
                click.echo(f"  Answer: {step['intermediate_answer']}")
                click.echo(f"  Confidence: {step['confidence_score']:.2f}")

        # Show sources
        if result.get('sources'):
            click.echo(f"\n📚 Sources ({len(result['sources'])}):")
            for source in result['sources'][:3]:  # Show top 3
                title = source.get('document_title', source['document_id'])
                relevance = source.get('relevance_score', 0)
                click.echo(f"  • {title} (relevance: {relevance:.1%})")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()

# Usage examples:
# ./cli search-cot "Compare A and B" --collection-id abc123 --cot --show-steps
# ./cli search-cot "Why does X happen?" --collection-id abc123 --cot-strategy causal --cot-depth 4
```

## Source Attribution Examples

### Accessing Source Information

```python
# Execute CoT and access source attribution
result = await cot_service.execute_chain_of_thought(cot_input)

# Access overall source summary
if result.source_summary:
    print(f"Total sources used: {len(result.source_summary.all_sources)}")
    print(f"Primary sources: {len(result.source_summary.primary_sources)}")

    # Show primary sources
    for source in result.source_summary.primary_sources:
        print(f"📄 {source.document_title or source.document_id}")
        print(f"   Relevance: {source.relevance_score:.1%}")
        if source.excerpt:
            print(f"   Excerpt: {source.excerpt[:100]}...")

    # Show step-by-step source usage
    print("\n📋 Step-by-step source usage:")
    for step_num, doc_ids in result.source_summary.source_usage_by_step.items():
        print(f"  Step {step_num}: {len(doc_ids)} sources used")
        for doc_id in doc_ids:
            print(f"    - {doc_id}")

# Access step-level source attribution
for step in result.reasoning_steps:
    print(f"\nStep {step.step_number}: {step.question}")
    print(f"Sources for this step ({len(step.source_attributions)}):")
    for attribution in step.source_attributions:
        print(f"  - {attribution.document_id} (relevance: {attribution.relevance_score:.2f})")
```

### UI-Friendly Source Display

```python
def format_cot_result_for_ui(result: ChainOfThoughtOutput) -> dict:
    """Format CoT result for frontend display."""

    # Format main answer
    formatted_result = {
        "answer": result.final_answer,
        "confidence": result.total_confidence,
        "execution_time": result.total_execution_time,
        "reasoning_strategy": result.reasoning_strategy
    }

    # Format reasoning steps
    formatted_result["reasoning_steps"] = []
    for step in result.reasoning_steps:
        formatted_step = {
            "step_number": step.step_number,
            "question": step.question,
            "answer": step.intermediate_answer,
            "confidence": step.confidence_score,
            "sources": [
                {
                    "id": attr.document_id,
                    "title": attr.document_title or attr.document_id,
                    "relevance": f"{attr.relevance_score:.1%}",
                    "excerpt": attr.excerpt[:150] + "..." if attr.excerpt and len(attr.excerpt) > 150 else attr.excerpt
                }
                for attr in step.source_attributions
            ]
        }
        formatted_result["reasoning_steps"].append(formatted_step)

    # Format source summary
    if result.source_summary:
        source_service = SourceAttributionService()
        formatted_result["source_summary"] = source_service.format_sources_for_display(
            result.source_summary,
            include_excerpts=True
        )

    return formatted_result

# Usage in web API
@app.get("/cot/result/{result_id}")
async def get_formatted_result(result_id: str):
    result = await get_cot_result(result_id)
    return format_cot_result_for_ui(result)
```

## Advanced Configuration Examples

### Domain-Specific Configurations

```python
class DomainSpecificCotService:
    def __init__(self, base_service: ChainOfThoughtService):
        self.base_service = base_service
        self.domain_configs = {
            "medical": ChainOfThoughtConfig(
                max_reasoning_depth=4,
                reasoning_strategy="hierarchical",
                evaluation_threshold=0.8,  # Higher threshold for medical accuracy
                token_budget_multiplier=2.5
            ),
            "legal": ChainOfThoughtConfig(
                max_reasoning_depth=5,
                reasoning_strategy="causal",
                evaluation_threshold=0.75,
                context_preservation=True,
                token_budget_multiplier=3.0  # More thorough for legal analysis
            ),
            "technical": ChainOfThoughtConfig(
                max_reasoning_depth=3,
                reasoning_strategy="decomposition",
                evaluation_threshold=0.6,
                token_budget_multiplier=2.0
            )
        }

    async def domain_aware_cot(self, question: str, domain: str, collection_id: UUID, user_id: UUID):
        config = self.domain_configs.get(domain, ChainOfThoughtConfig())

        cot_input = ChainOfThoughtInput(
            question=question,
            collection_id=collection_id,
            user_id=user_id,
            cot_config=config.model_dump()
        )

        return await self.base_service.execute_chain_of_thought(cot_input)

# Usage
domain_service = DomainSpecificCotService(cot_service)

# Medical question with high accuracy requirements
medical_result = await domain_service.domain_aware_cot(
    question="What are the contraindications for prescribing ACE inhibitors?",
    domain="medical",
    collection_id=medical_collection_id,
    user_id=doctor_user_id
)

# Legal analysis with thorough reasoning
legal_result = await domain_service.domain_aware_cot(
    question="What are the legal implications of data breach under GDPR?",
    domain="legal",
    collection_id=legal_collection_id,
    user_id=lawyer_user_id
)
```

### Adaptive Configuration Based on Results

```python
class AdaptiveCotService:
    def __init__(self, base_service: ChainOfThoughtService):
        self.base_service = base_service

    async def adaptive_cot(self, question: str, collection_id: UUID, user_id: UUID):
        """Execute CoT with adaptive configuration based on intermediate results."""

        # Start with conservative configuration
        current_config = ChainOfThoughtConfig(
            max_reasoning_depth=2,
            evaluation_threshold=0.6,
            token_budget_multiplier=1.5
        )

        max_attempts = 3
        for attempt in range(max_attempts):
            cot_input = ChainOfThoughtInput(
                question=question,
                collection_id=collection_id,
                user_id=user_id,
                cot_config=current_config.model_dump()
            )

            result = await self.base_service.execute_chain_of_thought(cot_input)

            # Check if result quality is acceptable
            if self._is_result_satisfactory(result):
                return result

            # Adapt configuration for next attempt
            if attempt < max_attempts - 1:
                current_config = self._enhance_config(current_config, result)

        return result  # Return best attempt

    def _is_result_satisfactory(self, result: ChainOfThoughtOutput) -> bool:
        """Check if CoT result meets quality thresholds."""
        return (
            result.total_confidence >= 0.7 and
            len(result.reasoning_steps) >= 2 and
            result.final_answer and
            len(result.final_answer.split()) >= 20  # Minimum answer length
        )

    def _enhance_config(self, config: ChainOfThoughtConfig, result: ChainOfThoughtOutput) -> ChainOfThoughtConfig:
        """Enhance configuration based on previous result."""
        new_config = config.model_copy()

        # Increase depth if confidence is low
        if result.total_confidence < 0.6:
            new_config.max_reasoning_depth = min(5, config.max_reasoning_depth + 1)
            new_config.token_budget_multiplier *= 1.2

        # Change strategy if not enough reasoning steps
        if len(result.reasoning_steps) < 2:
            strategies = ["decomposition", "iterative", "hierarchical", "causal"]
            current_idx = strategies.index(config.reasoning_strategy)
            new_config.reasoning_strategy = strategies[(current_idx + 1) % len(strategies)]

        return new_config

# Usage
adaptive_service = AdaptiveCotService(cot_service)
result = await adaptive_service.adaptive_cot(question, collection_id, user_id)
```

## Testing Examples

### Unit Testing CoT Components

```python
import pytest
from unittest.mock import Mock, AsyncMock
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput

@pytest.fixture
def mock_cot_service():
    mock_llm = AsyncMock()
    mock_search = Mock()
    mock_settings = Mock()

    return ChainOfThoughtService(
        settings=mock_settings,
        llm_service=mock_llm,
        search_service=mock_search
    )

@pytest.mark.asyncio
async def test_question_classification():
    """Test question classification functionality."""
    service = ChainOfThoughtService()

    # Test simple question
    simple_result = await service.classify_question("What is AI?")
    assert simple_result.question_type == "simple"
    assert not simple_result.requires_cot

    # Test comparison question
    comparison_result = await service.classify_question("Compare A and B")
    assert comparison_result.question_type == "comparison"
    assert comparison_result.requires_cot
    assert comparison_result.estimated_steps >= 3

@pytest.mark.asyncio
async def test_cot_execution_with_mocking(mock_cot_service):
    """Test complete CoT execution with mocked dependencies."""
    # Setup mock LLM responses
    mock_cot_service.llm_service.generate_response.return_value = "Mock LLM response"

    # Create test input
    cot_input = ChainOfThoughtInput(
        question="Compare supervised and unsupervised learning",
        collection_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        user_id=UUID("987fcdeb-51d2-43a1-b123-456789abcdef"),
        cot_config={"max_reasoning_depth": 3}
    )

    # Execute CoT
    result = await mock_cot_service.execute_chain_of_thought(cot_input)

    # Assertions
    assert result.original_question == cot_input.question
    assert result.final_answer is not None
    assert len(result.reasoning_steps) > 0
    assert result.total_confidence > 0
    assert result.source_summary is not None

@pytest.mark.asyncio
async def test_source_attribution():
    """Test source attribution functionality."""
    from rag_solution.services.source_attribution_service import SourceAttributionService

    service = SourceAttributionService()

    # Test source extraction from context
    context_docs = [
        "id:doc_1 Machine learning is a subset of artificial intelligence...",
        "Deep learning uses neural networks with multiple layers..."
    ]

    attributions = service.extract_sources_from_context(context_docs)

    assert len(attributions) == 2
    assert attributions[0].document_id == "doc_1"
    assert attributions[0].relevance_score > 0
    assert attributions[1].document_id == "context_doc_1"  # Auto-generated ID

# Integration test with real components
@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_cot_workflow():
    """Test complete CoT workflow with real components."""
    # This would use actual services in a test environment
    service = ChainOfThoughtService(settings=test_settings)

    cot_input = ChainOfThoughtInput(
        question="Why is regularization important in machine learning?",
        collection_id=test_collection_id,
        user_id=test_user_id
    )

    result = await service.execute_chain_of_thought(cot_input)

    # Verify complete workflow
    assert result.final_answer
    assert len(result.reasoning_steps) >= 2
    assert result.total_confidence > 0.5
    assert result.total_execution_time > 0
```

These examples demonstrate the flexibility and power of the Chain of Thought system, showing how it can be integrated into various application architectures and adapted for different use cases while maintaining transparency through comprehensive source attribution.