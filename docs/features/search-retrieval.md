# Search and Retrieval

This document describes the search and retrieval capabilities of RAG Modulo, including the 6-stage pipeline architecture, Chain of Thought reasoning, and advanced retrieval techniques.

## Overview

RAG Modulo implements a sophisticated search and retrieval system with the following features:

- **6-Stage Pipeline Architecture**: Modern, composable pipeline design
- **Automatic Pipeline Resolution**: No manual pipeline management required
- **Chain of Thought Reasoning**: Advanced reasoning for complex questions
- **Hybrid Search**: Vector + keyword search capabilities
- **Reranking**: Improved result relevance with cross-encoders
- **Conversation-Aware**: Context from chat history
- **Source Attribution**: Track document sources across reasoning steps

## Search Pipeline Architecture

### 6-Stage Pipeline

RAG Modulo uses a **modern 6-stage pipeline** for processing search queries:

```
┌────────────────────┐
│ 1. Pipeline        │ ← Resolve user's default pipeline
│    Resolution      │
└─────────┬──────────┘
          ↓
┌────────────────────┐
│ 2. Query           │ ← Enhance query for better retrieval
│    Enhancement     │
└─────────┬──────────┘
          ↓
┌────────────────────┐
│ 3. Retrieval       │ ← Search vector database
└─────────┬──────────┘
          ↓
┌────────────────────┐
│ 4. Reranking       │ ← Reorder results by relevance
└─────────┬──────────┘
          ↓
┌────────────────────┐
│ 5. Reasoning       │ ← Apply Chain of Thought (if needed)
└─────────┬──────────┘
          ↓
┌────────────────────┐
│ 6. Generation      │ ← Generate final answer
└────────────────────┘
```

### Stage 1: Pipeline Resolution

**Automatic pipeline selection** based on user configuration:

```python
# backend/rag_solution/services/search_service.py
async def _resolve_user_default_pipeline(
    self,
    user_id: UUID4
) -> Pipeline:
    """Resolve user's default pipeline automatically"""
    # Get user's LLM provider configuration
    provider = await self.llm_provider_service.get_user_provider(user_id)

    # Get or create default pipeline
    pipeline = await self.pipeline_service.get_user_default_pipeline(
        user_id=user_id,
        provider=provider
    )

    # Create default pipeline if none exists
    if not pipeline:
        pipeline = await self.pipeline_service.create_default_pipeline(
            user_id=user_id,
            provider=provider
        )

    return pipeline
```

**Key Benefits**:
- No client-side pipeline management
- Automatic pipeline creation for new users
- Intelligent error handling for configuration issues
- Simplified API and CLI interfaces

### Stage 2: Query Enhancement

**Improve queries** for better retrieval:

```python
async def _enhance_query(
    self,
    query: str,
    context: SearchContext
) -> str:
    """Enhance query with rewriting and context"""
    # Skip enhancement for short queries
    if len(query.split()) < 5:
        return query

    # Get query rewriter
    rewriter = await self.pipeline_service.get_query_rewriter(
        context.user_id
    )

    # Load conversation history for context
    conversation_history = await self._get_conversation_history(
        context.conversation_id
    )

    # Enhance query
    enhanced = await rewriter.rewrite(
        query=query,
        conversation_history=conversation_history,
        strategy="decomposition"
    )

    return enhanced
```

**Enhancement Techniques**:
- **Query Expansion**: Add synonyms and related terms
- **Query Rewriting**: Rephrase for better semantic match
- **Context Addition**: Include conversation history
- **Entity Recognition**: Extract and emphasize entities

### Stage 3: Retrieval

**Search vector database** for relevant documents:

```python
async def _retrieve_documents(
    self,
    query: str,
    collection_id: UUID4,
    top_k: int = 10
) -> list[QueryResult]:
    """Retrieve documents from vector database"""
    # Generate embeddings for query
    embeddings = await self.embedding_service.embed_text(query)

    # Search vector database
    results = await self.vector_store.search(
        collection_name=str(collection_id),
        query_vector=embeddings,
        top_k=top_k,
        filters={"collection_id": str(collection_id)}
    )

    return results
```

**Vector Search Configuration**:

```python
search_params = {
    "metric_type": "L2",  # Euclidean distance
    "params": {
        "ef": 64,         # Search accuracy parameter
        "top_k": 10,      # Number of results
    }
}
```

**Supported Distance Metrics**:
- **L2**: Euclidean distance (default)
- **IP**: Inner product (cosine similarity)
- **COSINE**: Cosine similarity

### Stage 4: Reranking

**Improve result relevance** with cross-encoder reranking:

```python
async def _rerank_results(
    self,
    query: str,
    documents: list[Document],
    context: SearchContext
) -> list[Document]:
    """Rerank documents using cross-encoder"""
    # Get reranker configuration
    reranker = await self.pipeline_service.get_reranker(
        context.user_id
    )

    if not reranker:
        return documents  # Skip if reranking disabled

    # Rerank with cross-encoder
    reranked = await reranker.rerank(
        query=query,
        documents=documents,
        top_k=context.config.get("top_k", 10)
    )

    return reranked
```

**Reranking Strategies**:
- **Cross-Encoder**: Deep neural network for query-document matching
- **LLM-based**: Use LLM to score relevance
- **Hybrid**: Combine multiple reranking signals

**Configuration**:

```python
# .env
ENABLE_RERANKING=true
RERANKER_TYPE=cross-encoder  # or "llm" or "hybrid"
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
```

### Stage 5: Reasoning (Chain of Thought)

**Apply advanced reasoning** for complex questions:

```python
async def _apply_chain_of_thought(
    self,
    question: str,
    documents: list[Document],
    context: SearchContext
) -> ChainOfThoughtOutput | None:
    """Apply Chain of Thought reasoning if needed"""
    # 1. Classify question complexity
    classification = await self.cot_service.classify_question(question)

    if not classification.requires_cot:
        return None  # Skip CoT for simple questions

    # 2. Decompose into sub-questions
    decomposition = await self.cot_service.decompose_question(
        question=question,
        max_depth=context.config.get("max_reasoning_depth", 3)
    )

    # 3. Execute reasoning steps
    reasoning_steps = []
    accumulated_context = []

    for sub_question in decomposition.sub_questions:
        # Search for each sub-question
        sub_result = await self._retrieve_documents(
            query=sub_question,
            collection_id=context.collection_id
        )

        # Build reasoning with context
        reasoning = await self._build_reasoning_step(
            sub_question=sub_question,
            documents=sub_result,
            accumulated_context=accumulated_context
        )

        # Quality check with retry logic
        if reasoning.quality_score < 0.6:
            reasoning = await self._retry_reasoning(
                sub_question,
                sub_result,
                max_retries=3
            )

        reasoning_steps.append(reasoning)
        accumulated_context.append(reasoning.reasoning)

    # 4. Synthesize final answer
    final_answer = await self.cot_service.synthesize(
        original_question=question,
        reasoning_steps=reasoning_steps
    )

    return ChainOfThoughtOutput(
        reasoning_steps=reasoning_steps,
        final_answer=final_answer,
        quality_score=final_answer.quality_score
    )
```

**Chain of Thought Features**:
- **Automatic Detection**: Detects when CoT is beneficial
- **Question Decomposition**: Breaks complex questions into steps
- **Iterative Reasoning**: Each step builds on previous context
- **Quality Scoring**: 0.0-1.0 confidence assessment
- **Retry Logic**: Up to 3 attempts with quality threshold
- **Structured Output**: XML tags for clean parsing

**See Also**: [Chain of Thought](chain-of-thought/index.md) for detailed documentation

### Stage 6: Generation

**Generate final answer** using LLM:

```python
async def _generate_answer(
    self,
    question: str,
    documents: list[Document],
    cot_output: ChainOfThoughtOutput | None,
    context: SearchContext
) -> str:
    """Generate answer using LLM"""
    # Build context from documents
    context_text = self._build_context(documents)

    # Add CoT reasoning if available
    if cot_output:
        context_text += f"\n\nReasoning:\n{cot_output.final_answer}"

    # Load prompt template
    template = await self.prompt_service.get_template(
        name="rag_generation",
        user_id=context.user_id
    )

    # Format prompt
    prompt = template.format(
        question=question,
        context=context_text
    )

    # Get LLM provider
    provider = await self.llm_provider_factory.get_provider(
        provider_name=context.provider_name,
        model_id=context.model_id
    )

    # Generate with structured output
    response = await provider.generate_response(
        prompt=prompt,
        max_tokens=1024,
        temperature=0.7
    )

    # Parse structured output (XML tags: <thinking>, <answer>)
    parsed = self._parse_llm_response(response)

    # Track token usage
    await self.token_service.track_usage(
        user_id=context.user_id,
        tokens=parsed.token_count
    )

    return parsed.answer
```

## Search API

### Simple Search

**Basic search request** without Chain of Thought:

```python
from rag_solution.schemas.search_schema import SearchInput

search_input = SearchInput(
    question="What is machine learning?",
    collection_id="550e8400-e29b-41d4-a716-446655440000",
    user_id="660e8400-e29b-41d4-a716-446655440001"
)

result = await search_service.search(search_input)

print(result.answer)
print(f"Found {len(result.documents)} source documents")
```

### Complex Search with CoT

**Enable Chain of Thought** for complex questions:

```python
search_input = SearchInput(
    question="How does machine learning work and what are the key components?",
    collection_id=collection_id,
    user_id=user_id,
    config_metadata={
        "cot_enabled": True,          # Explicitly enable CoT
        "show_cot_steps": True,       # Include reasoning steps
        "max_reasoning_depth": 3,     # Maximum sub-question depth
        "reasoning_strategy": "decomposition"
    }
)

result = await search_service.search(search_input)

# Access reasoning steps
if result.cot_output:
    for step in result.cot_output["reasoning_steps"]:
        print(f"Sub-question: {step['question']}")
        print(f"Reasoning: {step['reasoning']}")
        print(f"Quality: {step['quality_score']}")
```

### Conversation-Aware Search

**Include conversation history** for context:

```python
search_input = SearchInput(
    question="Tell me more about that",  # Refers to previous context
    collection_id=collection_id,
    user_id=user_id,
    config_metadata={
        "conversation_id": "770e8400-e29b-41d4-a716-446655440002",
        "include_history": True
    }
)

result = await search_service.search(search_input)
```

## Retrieval Techniques

### Hierarchical Chunking

**Maintain context** across document chunks:

```python
# backend/data_ingestion/chunking/hierarchical_chunker.py
class HierarchicalChunker:
    def chunk_document(
        self,
        document: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> list[Chunk]:
        """Create hierarchical chunks with context"""
        chunks = []

        # 1. Split into sections (headers, paragraphs)
        sections = self._split_into_sections(document)

        # 2. Create chunks within sections
        for section in sections:
            section_chunks = self._chunk_section(
                section,
                chunk_size=chunk_size,
                overlap=overlap
            )

            # Add section context to each chunk
            for chunk in section_chunks:
                chunk.metadata["section"] = section.title
                chunk.metadata["parent"] = section.id
                chunks.append(chunk)

        return chunks
```

### Hybrid Search

**Combine vector and keyword search**:

```python
async def hybrid_search(
    query: str,
    collection_id: UUID4,
    alpha: float = 0.7  # Weight for vector search (0-1)
) -> list[Document]:
    """Hybrid search combining vector + keyword"""
    # Vector search
    vector_results = await vector_store.search(
        query=query,
        collection_id=collection_id,
        top_k=20
    )

    # Keyword search (BM25)
    keyword_results = await keyword_store.search(
        query=query,
        collection_id=collection_id,
        top_k=20
    )

    # Combine results with weighted scores
    combined = self._combine_results(
        vector_results,
        keyword_results,
        alpha=alpha
    )

    return combined[:10]  # Return top 10
```

### Metadata Filtering

**Filter results** by metadata:

```python
search_input = SearchInput(
    question="What is machine learning?",
    collection_id=collection_id,
    user_id=user_id,
    config_metadata={
        "filters": {
            "document_type": "pdf",
            "created_after": "2024-01-01",
            "author": "John Doe"
        }
    }
)

result = await search_service.search(search_input)
```

## Source Attribution

### Document Sources

**Track sources** across all reasoning steps:

```python
# Result includes source attribution
result = await search_service.search(search_input)

for doc in result.documents:
    print(f"Source: {doc.metadata['filename']}")
    print(f"Page: {doc.metadata.get('page', 'N/A')}")
    print(f"Score: {doc.score}")
    print(f"Content: {doc.content[:200]}...")
```

### Citation Format

**Formatted citations** in responses:

```python
# Answer with citations
answer_with_citations = """
Machine learning is a subset of artificial intelligence [1].
It uses algorithms to learn from data [2][3].

Sources:
[1] Introduction to ML (page 5)
[2] Deep Learning Fundamentals (page 12)
[3] AI Handbook (page 87)
"""
```

## Performance Optimization

### Caching

**Cache search results** for identical queries:

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def search_cached(
    query_hash: str,
    collection_id: str
) -> SearchOutput:
    """Cache search results"""
    return search_service.search(query_hash, collection_id)

# Usage
query_hash = hashlib.md5(query.encode()).hexdigest()
result = search_cached(query_hash, str(collection_id))
```

### Batch Search

**Search multiple queries** in one batch:

```python
async def batch_search(
    queries: list[str],
    collection_id: UUID4,
    user_id: UUID4
) -> list[SearchOutput]:
    """Batch multiple search queries"""
    tasks = [
        search_service.search(
            SearchInput(
                question=query,
                collection_id=collection_id,
                user_id=user_id
            )
        )
        for query in queries
    ]

    results = await asyncio.gather(*tasks)
    return results
```

## Configuration

### Environment Variables

```bash
# Vector Database
VECTOR_DB=milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Retrieval Settings
MAX_TOP_K=100
DEFAULT_TOP_K=10
VECTOR_BATCH_SIZE=1000

# Reranking
ENABLE_RERANKING=true
RERANKER_TYPE=cross-encoder
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# Chain of Thought
COT_ENABLED=true
COT_MAX_DEPTH=3
COT_QUALITY_THRESHOLD=0.6
COT_MAX_RETRIES=3
```

### Per-User Configuration

**Customize per user or organization**:

```python
# User pipeline configuration
user_config = {
    "top_k": 20,
    "reranking_enabled": True,
    "cot_enabled": True,
    "cot_max_depth": 3,
    "temperature": 0.7,
    "max_tokens": 1024
}

# Apply to search
search_input.config_metadata = user_config
```

## CLI Usage

### Simple Search

```bash
# Basic search
./rag-cli search query \
  --collection-id "col_123abc" \
  --query "What is machine learning?"

# Complex questions automatically use Chain of Thought
./rag-cli search query \
  --collection-id "col_123abc" \
  --query "How does ML work and what are the key components?"
```

### Advanced Options

```bash
# Enable explicit CoT
./rag-cli search query \
  --collection-id "col_123abc" \
  --query "Explain neural networks" \
  --enable-cot \
  --show-cot-steps

# Conversation-aware search
./rag-cli search conversation \
  --session-id "session_789xyz" \
  --query "Tell me more about that"
```

## Best Practices

### Query Formulation

1. **Be specific**: Provide detailed questions
2. **Use context**: Reference previous conversation
3. **Break down complex questions**: Let CoT handle decomposition
4. **Include constraints**: Add metadata filters when needed

### Performance

1. **Enable caching**: Cache frequent queries
2. **Use batch search**: Process multiple queries together
3. **Optimize top_k**: Balance accuracy vs speed
4. **Monitor token usage**: Track LLM costs

### Quality

1. **Enable reranking**: Improve result relevance
2. **Use CoT for complexity**: Let system detect when needed
3. **Validate sources**: Check document attribution
4. **Monitor quality scores**: Track CoT confidence

## Related Documentation

- [Chain of Thought](chain-of-thought/index.md) - Advanced reasoning system
- [LLM Integration](llm-integration.md) - Provider configuration
- [Document Processing](document-processing.md) - Ingestion pipeline
- [Architecture - Data Flow](../architecture/data-flow.md) - Complete request flow
