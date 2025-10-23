# Leveraging Existing Infrastructure

## Overview

The RAG Technique System is designed to **wrap and extend** the existing RAG Modulo infrastructure, not replace it. This document explains how the technique system leverages existing components.

## Adapter Pattern Implementation

### Philosophy

Rather than reimplementing retrieval logic, the technique system uses the **Adapter Pattern** to wrap existing, battle-tested components:

```
┌─────────────────────────────────────────┐
│   Technique System (New)                │
│   - BaseTechnique interface             │
│   - TechniquePipeline orchestration     │
│   - Dynamic configuration               │
└──────────────┬──────────────────────────┘
               │ adapts
               ▼
┌─────────────────────────────────────────┐
│   Existing Infrastructure (Reused)      │
│   - VectorRetriever                     │
│   - HybridRetriever                     │
│   - LLMReranker                         │
│   - LLM Provider abstraction            │
│   - Vector DB support                   │
└─────────────────────────────────────────┘
```

## Leveraging Existing Components

### ✅ 1. Service-Based Architecture

**What Exists**: Clean service layer with dependency injection
- `SearchService`, `LLMProviderService`, `CollectionService`, etc.
- Well-defined service interfaces
- Lazy initialization pattern

**How We Leverage It**:
```python
class TechniqueContext:
    """Context uses dependency injection like existing services."""
    llm_provider: LLMBase | None = None  # Injected from LLMProviderService
    vector_store: Any | None = None       # Injected from existing vector store
    db_session: Session | None = None     # Injected from existing DB session
```

**Benefits**:
- Reuses existing service initialization
- No duplicate service creation
- Same dependency injection pattern

### ✅ 2. Existing LLM Provider Abstraction

**What Exists**: `LLMBase` interface with multiple providers
- WatsonX, OpenAI, Anthropic providers
- Unified `generate()` interface
- Token tracking and cost management

**How We Leverage It**:
```python
@register_technique()
class LLMRerankingTechnique(BaseTechnique):
    """Wraps existing LLMReranker which uses LLM provider abstraction."""

    async def execute(self, context: TechniqueContext):
        # Reuse existing LLMReranker (which uses LLMBase providers)
        self._reranker = LLMReranker(
            llm_provider=context.llm_provider,  # ← Existing provider
            user_id=context.user_id,
            prompt_template=prompt_template,
        )

        # LLMReranker handles all LLM calls internally
        reranked = self._reranker.rerank(query, documents, top_k)
        return TechniqueResult(success=True, output=reranked, ...)
```

**Benefits**:
- No LLM provider duplication
- Automatic token tracking
- Consistent error handling
- Works with all existing providers (WatsonX, OpenAI, Anthropic)

### ✅ 3. Flexible Vector DB Support

**What Exists**: Abstracted vector store interface
- Milvus, Elasticsearch, Pinecone, Weaviate, ChromaDB support
- Common `retrieve_documents()` interface
- Connection pooling and error handling

**How We Leverage It**:
```python
@register_technique()
class VectorRetrievalTechnique(BaseTechnique):
    """Wraps existing VectorRetriever which supports all vector DBs."""

    async def execute(self, context: TechniqueContext):
        # Reuse existing VectorRetriever (works with any vector DB)
        from rag_solution.data_ingestion.ingestion import DocumentStore
        document_store = DocumentStore(
            context.vector_store,  # ← Existing vector store (any type)
            collection_name
        )
        self._retriever = VectorRetriever(document_store)

        # VectorRetriever handles DB-specific logic
        results = self._retriever.retrieve(collection_name, query)
        return TechniqueResult(success=True, output=results, ...)
```

**Benefits**:
- Works with all supported vector DBs automatically
- No DB-specific code in techniques
- Reuses connection pooling
- Consistent error handling across DBs

### ✅ 4. Hierarchical Chunking

**What Exists**: Sophisticated chunking strategies
- Sentence-based chunking
- Recursive chunking
- Hierarchical parent-child relationships
- Metadata preservation

**How We Leverage It**:
```python
@register_technique()
class SemanticChunkingTechnique(BaseTechnique):
    """Extends existing chunking infrastructure."""

    async def execute(self, context: TechniqueContext):
        from rag_solution.data_ingestion.chunking import (
            chunk_text_by_sentences,
            cosine_similarity  # ← Reuse existing utilities
        )

        # Build on existing chunking, add semantic boundary detection
        sentence_chunks = chunk_text_by_sentences(text)
        semantic_chunks = self._merge_by_similarity(
            sentence_chunks,
            cosine_similarity  # ← Reuse existing similarity function
        )
        return TechniqueResult(success=True, output=semantic_chunks, ...)
```

**Benefits**:
- Extends proven chunking logic
- Preserves metadata and relationships
- Compatible with existing chunk formats

### ✅ 5. Reranking Infrastructure

**What Exists**: `LLMReranker` with sophisticated scoring
- Batch processing for efficiency
- Score extraction with multiple patterns
- Fallback on errors
- Prompt template system

**How We Leverage It**:
```python
@register_technique()
class LLMRerankingTechnique(BaseTechnique):
    """100% wraps existing LLMReranker - zero reimplementation."""

    def __init__(self):
        self._reranker: LLMReranker | None = None

    async def execute(self, context: TechniqueContext):
        # Create LLMReranker instance (reuses ALL existing logic)
        if self._reranker is None:
            self._reranker = LLMReranker(
                llm_provider=context.llm_provider,
                user_id=context.user_id,
                prompt_template=context.config.get("prompt_template"),
                batch_size=context.config.get("batch_size", 10),
                score_scale=context.config.get("score_scale", 10),
            )

        # Delegate to existing implementation
        reranked = self._reranker.rerank(
            context.current_query,
            context.retrieved_documents,
            top_k=context.config.get("top_k", 10)
        )

        # Just wrap the result in our TechniqueResult format
        return TechniqueResult(success=True, output=reranked, ...)
```

**Benefits**:
- **Zero code duplication** - 100% reuse
- Inherits all improvements to LLMReranker
- Consistent behavior with existing code
- Maintains existing prompt templates

### ✅ 6. Chain of Thought Reasoning

**What Exists**: `ChainOfThoughtService` with sophisticated reasoning
- Question classification
- Question decomposition
- Iterative reasoning
- Source attribution

**How We Leverage It**:
```python
@register_technique()
class ChainOfThoughtTechnique(BaseTechnique):
    """Wraps existing ChainOfThoughtService."""

    async def execute(self, context: TechniqueContext):
        from rag_solution.services.chain_of_thought_service import (
            ChainOfThoughtService
        )

        # Reuse existing CoT service
        cot_service = ChainOfThoughtService(
            llm_provider=context.llm_provider,
            # ... other dependencies
        )

        # Execute using existing CoT logic
        cot_result = await cot_service.execute_chain_of_thought(
            question=context.current_query,
            collection_id=context.collection_id,
            user_id=context.user_id
        )

        # Update context with CoT results
        context.current_query = cot_result.synthesized_answer
        context.intermediate_results["cot_steps"] = cot_result.reasoning_steps

        return TechniqueResult(success=True, output=cot_result, ...)
```

**Benefits**:
- Reuses sophisticated reasoning logic
- Compatible with existing CoT features
- No duplication of question decomposition logic

## What's New vs. What's Reused

### 🆕 New (Technique System Additions)

1. **BaseTechnique Interface**: Common abstraction for all techniques
2. **TechniqueRegistry**: Discovery and instantiation system
3. **TechniquePipeline**: Orchestration and execution flow
4. **TechniqueContext**: Shared state container
5. **Dynamic Configuration**: Runtime technique selection via API
6. **Presets**: Pre-configured technique combinations
7. **Observability**: Execution traces and metrics

### ♻️ Reused (Existing Infrastructure)

1. **VectorRetriever**: Vector search implementation
2. **HybridRetriever**: Hybrid vector + keyword search
3. **LLMReranker**: LLM-based reranking logic
4. **LLMBase Providers**: All LLM provider implementations
5. **Vector Stores**: All vector DB implementations
6. **Chunking Logic**: Sentence and recursive chunking
7. **ChainOfThoughtService**: CoT reasoning engine
8. **DocumentStore**: Document ingestion and storage
9. **Service Layer**: All existing services

## Code Comparison: Old vs. Adapter

### ❌ What We DON'T Do (Reimplementation)

```python
# BAD: Reimplementing vector retrieval from scratch
class VectorRetrievalTechnique(BaseTechnique):
    async def execute(self, context):
        # ❌ Reimplementing vector search logic
        embeddings = await self._embed_query(context.current_query)
        results = await context.vector_store.search(embeddings, top_k=10)
        # ❌ Reimplementing score normalization
        normalized = self._normalize_scores(results)
        return TechniqueResult(success=True, output=normalized, ...)
```

### ✅ What We DO (Adapter Pattern)

```python
# GOOD: Wrapping existing VectorRetriever
class VectorRetrievalTechnique(BaseTechnique):
    async def execute(self, context):
        # ✅ Reuse existing VectorRetriever (battle-tested)
        document_store = DocumentStore(context.vector_store, collection_name)
        retriever = VectorRetriever(document_store)

        # ✅ Delegate to existing implementation
        results = retriever.retrieve(collection_name, query)

        # ✅ Just wrap in our result format
        return TechniqueResult(success=True, output=results, ...)
```

## Integration Points

### How Techniques Access Existing Infrastructure

```python
# TechniqueContext is the integration bridge
context = TechniqueContext(
    user_id=user_id,
    collection_id=collection_id,
    original_query=query,

    # Dependency injection from existing services
    llm_provider=llm_provider_service.get_provider(user_id),
    vector_store=collection_service.get_vector_store(collection_id),
    db_session=db_session,
)

# Techniques access existing infrastructure through context
technique.execute(context)
```

### SearchService Integration (Planned)

```python
class SearchService:
    """Enhanced to use technique pipeline while maintaining existing logic."""

    async def search(self, search_input: SearchInput):
        # Build technique pipeline (new)
        pipeline = self._build_pipeline(search_input)

        # Create context with existing services (integration)
        context = TechniqueContext(
            user_id=search_input.user_id,
            collection_id=search_input.collection_id,
            original_query=search_input.question,
            llm_provider=self.llm_provider_service.get_provider(user_id),
            vector_store=self.collection_service.get_vector_store(collection_id),
            db_session=self.db,
        )

        # Execute pipeline (delegates to existing retrievers/rerankers)
        context = await pipeline.execute(context)

        # Generate answer using existing generation logic
        answer = await self._generate_answer(
            context.current_query,
            context.retrieved_documents,
            context.llm_provider
        )

        # Return with technique metrics
        return SearchOutput(
            answer=answer,
            documents=[r.chunk.metadata for r in context.retrieved_documents],
            query_results=context.retrieved_documents,
            techniques_applied=context.execution_trace,
            technique_metrics=context.metrics["pipeline_metrics"],
        )
```

## Architecture Validation Checklist

When adding new techniques, ensure they leverage existing infrastructure:

- [ ] **LLM Calls**: Use `context.llm_provider` (LLMBase abstraction)
- [ ] **Vector Search**: Wrap `VectorRetriever` or `HybridRetriever`
- [ ] **Reranking**: Wrap `LLMReranker`
- [ ] **Chunking**: Extend existing chunking utilities
- [ ] **CoT Reasoning**: Wrap `ChainOfThoughtService`
- [ ] **Database**: Use `context.db_session`
- [ ] **Services**: Access via dependency injection in context

## Benefits of This Approach

### 1. **Code Reuse**
- No duplication of complex logic
- Single source of truth for retrieval/reranking
- Bug fixes in existing code benefit techniques automatically

### 2. **Consistency**
- Same LLM providers everywhere
- Same vector DB support everywhere
- Same error handling patterns

### 3. **Maintainability**
- Techniques focus on composition, not implementation
- Existing code improvements propagate automatically
- Smaller surface area for bugs

### 4. **Compatibility**
- Works with all existing LLM providers
- Works with all existing vector DBs
- Works with all existing services

### 5. **Performance**
- Reuses optimized implementations
- No unnecessary object creation
- Singleton pattern where appropriate

### 6. **Testing**
- Existing components already tested
- Techniques only test composition logic
- Reduced test burden

## Anti-Patterns to Avoid

### ❌ Don't: Reimplement Existing Logic

```python
# BAD: Reimplementing vector search
class VectorTechnique(BaseTechnique):
    async def execute(self, context):
        # ❌ Don't do this - reimplementing VectorRetriever
        embeddings = await self._create_embeddings(context.query)
        results = await self._search_vector_db(embeddings)
        return results
```

### ✅ Do: Wrap Existing Components

```python
# GOOD: Wrapping VectorRetriever
class VectorTechnique(BaseTechnique):
    async def execute(self, context):
        # ✅ Reuse existing VectorRetriever
        retriever = VectorRetriever(document_store)
        results = retriever.retrieve(collection, query)
        return TechniqueResult(success=True, output=results, ...)
```

### ❌ Don't: Create Parallel Services

```python
# BAD: Creating new LLM service
class MyLLMService:
    def __init__(self):
        self.openai_client = OpenAI()  # ❌ Duplicate
        self.anthropic_client = Anthropic()  # ❌ Duplicate
```

### ✅ Do: Use Existing Services via Context

```python
# GOOD: Use existing LLM provider
class MyTechnique(BaseTechnique):
    async def execute(self, context):
        # ✅ Use injected LLM provider
        response = await context.llm_provider.generate(prompt)
        return response
```

## Conclusion

The technique system is a **thin orchestration layer** that composes existing, battle-tested components. It adds:

- **Dynamic configuration** (runtime technique selection)
- **Composability** (technique pipelines)
- **Observability** (execution traces and metrics)
- **Extensibility** (easy to add new techniques)

While reusing 100% of existing:

- **Retrieval logic** (VectorRetriever, HybridRetriever)
- **Reranking logic** (LLMReranker)
- **LLM providers** (WatsonX, OpenAI, Anthropic)
- **Vector stores** (Milvus, Elasticsearch, etc.)
- **Services** (all existing services)
- **Chunking** (existing chunking strategies)
- **CoT reasoning** (ChainOfThoughtService)

This approach maximizes code reuse, maintains consistency, and ensures that improvements to existing infrastructure automatically benefit the technique system.

---

**Document Version**: 1.0
**Last Updated**: 2025-10-23
**Status**: Architecture Validated ✅
